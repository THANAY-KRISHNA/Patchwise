"""Deterministic Static AST Rules for JavaScript and TypeScript (JS001 - JS004).

Rules:
- JS001: Potentially unsafe dynamic code execution (eval, new Function, setTimeout/setInterval with string)
- JS002: Potential DOM HTML injection / Cross-Site Scripting (innerHTML, outerHTML, document.write, dangerouslySetInnerHTML)
- JS003: Unsafe shell command construction (child_process.exec, execSync with dynamic string)
- JS004: Potentially unsafe SQL query construction (query, execute, $queryRawUnsafe with dynamic concatenation/template)
"""
import re
from typing import Dict, List, Optional, Set
import esprima

from src.analyzer.base import CandidateFinding
from src.parser.models import ParsedFileDiff
from src.schemas.findings import FindingCategory, FindingProvenance, FindingSeverity

SQL_KEYWORDS_REGEX = re.compile(
    r"\b(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|DROP|ALTER|CREATE|TABLE|TRUNCATE)\b",
    re.IGNORECASE,
)

SHELL_EXEC_NAMES = {"exec", "execSync"}
SQL_QUERY_NAMES = {"query", "execute", "raw", "$queryRawUnsafe", "$executeRawUnsafe"}


def _preprocess_ts_and_jsx(code: str) -> str:
    """
    Preprocess TypeScript and JSX code to allow parsing by standard ESTree parsers
    while strictly preserving exact newline counts and line-number alignments.
    """
    def blank_multiline(m: re.Match) -> str:
        newlines = m.group(0).count("\n")
        return "\n" * newlines if newlines > 0 else " " * len(m.group(0))

    # 1. Blank out interfaces (single-line or multiline, with or without leading whitespace)
    code = re.sub(
        r"(?ms)^[ \t]*(?:export\s+)?interface\s+\w+(?:<[^>]+>)?(?:\s+extends\s+[^{]+)?\s*\{.*?\}",
        blank_multiline,
        code,
    )
    # 2. Blank out type aliases
    code = re.sub(r"(?ms)^[ \t]*(?:export\s+)?type\s+\w+(?:<[^>]+>)?\s*=.*?;", blank_multiline, code)

    # 3. Strip return type annotations: `): ReturnType {` or `): Promise<T> {`
    code = re.sub(r"\)\s*:\s*[A-Za-z0-9_<>\[\],\s|&?{}]+(?=\s*=>|\s*\{)", ")", code)

    # 4. Strip destructuring object type annotations: `: { ... }`
    code = re.sub(r":\s*\{[^}]*\}", "", code)

    # 5. Strip parameter type annotations: `param: Type` or `param?: Type`
    code = re.sub(r"(?<=[\w\]\}])\?:\s*[A-Za-z0-9_<>\[\],\s|&]+(?=[,\)])", "", code)
    code = re.sub(r"(?<=[\w\]\}]):\s*[A-Za-z0-9_<>\[\],\s|&]+(?=[,\)])", "", code)

    # 6. Strip variable type annotations: `const x: Type =`
    code = re.sub(r"(?<=[\w\]\}]):\s*[A-Za-z0-9_<>\[\],\s|&]+(?=\s*=)", "", code)

    # 7. Strip `as Type` casts
    code = re.sub(r"\s+as\s+[A-Za-z0-9_<>\[\],\s|&]+", "", code)

    # 8. Transform JSX tags while preserving dangerouslySetInnerHTML and line numbers
    def transform_jsx(m: re.Match) -> str:
        full = m.group(0)
        newlines = "\n" * full.count("\n")
        match_danger = re.search(r"dangerouslySetInnerHTML=\{(\{[^}]*\}|[^{}]+)\}", full)
        if match_danger:
            val = match_danger.group(1)
            return f"React.createElement('div', {{ dangerouslySetInnerHTML: {val} }}){newlines}"
        return f"React.createElement('div', null){newlines}"

    code = re.sub(r"(?s)<[A-Za-z0-9_.]+(?:\s+[^>]*?)?(?:/>|>)", transform_jsx, code)
    code = re.sub(r"</[A-Za-z0-9_.]+>", "", code)

    return code


def _is_dynamic_string(node) -> bool:
    """Check if node represents a dynamic string (template literal with expressions, concatenation, or identifier)."""
    if not node:
        return False
    node_type = getattr(node, "type", None)
    if node_type == "TemplateLiteral":
        return len(getattr(node, "expressions", [])) > 0
    if node_type == "BinaryExpression" and getattr(node, "operator", None) == "+":
        return True
    if node_type == "Identifier":
        return True
    return False


def _extract_static_strings(node) -> List[str]:
    """Recursively collect static string literals and quasi segments from an AST node."""
    strings: List[str] = []
    if not node:
        return strings
    node_type = getattr(node, "type", None)
    if node_type == "Literal" and isinstance(getattr(node, "value", None), str):
        strings.append(node.value)
    elif node_type == "TemplateLiteral":
        for q in getattr(node, "quasis", []):
            raw = getattr(getattr(q, "value", None), "raw", "")
            if raw:
                strings.append(raw)
    elif node_type == "BinaryExpression" and getattr(node, "operator", None) == "+":
        strings.extend(_extract_static_strings(getattr(node, "left", None)))
        strings.extend(_extract_static_strings(getattr(node, "right", None)))
    return strings


def _contains_sql_keywords(node) -> bool:
    """Check if node contains SQL keywords in its static text."""
    static_parts = _extract_static_strings(node)
    joined = " ".join(static_parts)
    return bool(SQL_KEYWORDS_REGEX.search(joined))


def _get_callee_name(callee) -> Optional[str]:
    """Extract top-level method or function name from call callee."""
    if not callee:
        return None
    node_type = getattr(callee, "type", None)
    if node_type == "Identifier":
        return callee.name
    if node_type in ("MemberExpression", "StaticMemberExpression"):
        prop = getattr(callee, "property", None)
        if prop and hasattr(prop, "name"):
            return prop.name
    return None


def _get_callee_full_name(callee) -> str:
    """Extract full qualified name (e.g. child_process.exec) if available."""
    if not callee:
        return ""
    node_type = getattr(callee, "type", None)
    if node_type == "Identifier":
        return callee.name
    if node_type in ("MemberExpression", "StaticMemberExpression"):
        obj_name = getattr(getattr(callee, "object", None), "name", "")
        prop_name = getattr(getattr(callee, "property", None), "name", "")
        if obj_name and prop_name:
            return f"{obj_name}.{prop_name}"
        return prop_name or ""
    return ""


def _walk_ast(node):
    """Recursive generator traversing all AST nodes in an ESTree tree."""
    if not node:
        return
    yield node
    if hasattr(node, "__dict__"):
        for k, v in node.__dict__.items():
            if k == "loc":
                continue
            if isinstance(v, list):
                for item in v:
                    if hasattr(item, "type"):
                        yield from _walk_ast(item)
            elif hasattr(v, "type"):
                yield from _walk_ast(v)


class JavaScriptAstRuleVisitor:
    """Inspects ESTree AST nodes and emits grounded candidate findings for rules JS001 - JS004."""

    def __init__(
        self,
        file_path: str,
        line_mapping: Dict[int, int],
        added_lines: Set[int],
    ):
        self.file_path = file_path
        self.line_mapping = line_mapping
        self.added_lines = added_lines
        self.findings: List[CandidateFinding] = []
        self._seen_keys: Set[str] = set()

    def _get_mapped_line(self, node) -> Optional[int]:
        if not node or not hasattr(node, "loc") or not node.loc:
            return None
        ast_line = node.loc.start.line
        return self.line_mapping.get(ast_line)

    def _is_in_changed_lines(self, line: Optional[int]) -> bool:
        return line is not None and line in self.added_lines

    def _add_finding(self, finding: CandidateFinding):
        key = f"{finding.rule_id}:{finding.file_path}:{finding.start_line}"
        if key not in self._seen_keys:
            self._seen_keys.add(key)
            self.findings.append(finding)

    def inspect(self, tree):
        """Walk and evaluate all rules on the AST."""
        for node in _walk_ast(tree):
            node_type = getattr(node, "type", None)

            # -----------------------------------------------------------------
            # 1. CallExpression & NewExpression Checks (JS001, JS002, JS003, JS004)
            # -----------------------------------------------------------------
            if node_type == "CallExpression":
                callee = getattr(node, "callee", None)
                callee_name = _get_callee_name(callee)
                full_callee = _get_callee_full_name(callee)
                args = getattr(node, "arguments", [])
                first_arg = args[0] if args else None

                node_line = self._get_mapped_line(node)
                arg_line = self._get_mapped_line(first_arg) if first_arg else None
                target_line = arg_line if (arg_line and self._is_in_changed_lines(arg_line)) else node_line

                # --- JS001: eval(...) ---
                if callee_name == "eval" and self._is_in_changed_lines(target_line):
                    self._add_finding(
                        CandidateFinding(
                            rule_id="JS001",
                            source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                            severity=FindingSeverity.HIGH,
                            category=FindingCategory.SECURITY_PATTERN,
                            file_path=self.file_path,
                            start_line=target_line,
                            end_line=target_line,
                            title="Potentially unsafe dynamic execution with eval()",
                            explanation=(
                                "Using 'eval()' executes arbitrary code strings in the caller's privilege context, "
                                "introducing remote code execution (RCE) vulnerabilities if any part of the string is influenced by external input."
                            ),
                            suggested_fix="Replace 'eval()' with safe parsers like JSON.parse() or structured logic.",
                        )
                    )

                # --- JS001: setTimeout/setInterval with string argument ---
                elif callee_name in ("setTimeout", "setInterval") and first_arg and self._is_in_changed_lines(target_line):
                    first_arg_type = getattr(first_arg, "type", None)
                    is_string_eval = (
                        (first_arg_type == "Literal" and isinstance(getattr(first_arg, "value", None), str))
                        or first_arg_type == "TemplateLiteral"
                        or (first_arg_type == "BinaryExpression" and getattr(first_arg, "operator", None) == "+")
                    )
                    if is_string_eval:
                        self._add_finding(
                            CandidateFinding(
                                rule_id="JS001",
                                source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                                severity=FindingSeverity.HIGH,
                                category=FindingCategory.SECURITY_PATTERN,
                                file_path=self.file_path,
                                start_line=target_line,
                                end_line=target_line,
                                title=f"Potentially unsafe dynamic string evaluation in {callee_name}()",
                                explanation=(
                                    f"Passing a string or dynamically concatenated expression to '{callee_name}()' invokes the internal "
                                    "eval compiler, allowing arbitrary script execution."
                                ),
                                suggested_fix=f"Pass a callback function directly to {callee_name}(() => {{ ... }}, delay) instead of a string.",
                            )
                        )

                # --- JS002: document.write / document.writeln ---
                elif callee_name in ("write", "writeln") and "document" in full_callee and self._is_in_changed_lines(target_line):
                    self._add_finding(
                        CandidateFinding(
                            rule_id="JS002",
                            source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                            severity=FindingSeverity.HIGH,
                            category=FindingCategory.SECURITY_PATTERN,
                            file_path=self.file_path,
                            start_line=target_line,
                            end_line=target_line,
                            title=f"Potential DOM HTML injection via {full_callee}()",
                            explanation=(
                                f"Calling '{full_callee}()' writes unescaped markup directly to the active document stream, "
                                "bypassing entity encoding and enabling Cross-Site Scripting (XSS)."
                            ),
                            suggested_fix="Use DOM manipulation methods like element.textContent or element.setAttribute() instead of document.write().",
                        )
                    )

                # --- JS003: Shell command execution (exec, execSync) ---
                elif (callee_name in SHELL_EXEC_NAMES or full_callee.endswith((".exec", ".execSync"))) and first_arg and self._is_in_changed_lines(target_line):
                    first_arg_type = getattr(first_arg, "type", None)
                    is_static_literal = (first_arg_type == "Literal" and isinstance(getattr(first_arg, "value", None), str)) or (
                        first_arg_type == "TemplateLiteral" and len(getattr(first_arg, "expressions", [])) == 0
                    )
                    if not is_static_literal and _is_dynamic_string(first_arg):
                        self._add_finding(
                            CandidateFinding(
                                rule_id="JS003",
                                source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                                severity=FindingSeverity.HIGH,
                                category=FindingCategory.SECURITY_PATTERN,
                                file_path=self.file_path,
                                start_line=target_line,
                                end_line=target_line,
                                title=f"Unsafe shell command construction in {full_callee or callee_name}()",
                                explanation=(
                                    f"Constructing shell commands using dynamic string interpolation or concatenation in '{full_callee or callee_name}()' "
                                    "exposes the host to command injection attacks if user-controlled data is passed to the shell."
                                ),
                                suggested_fix="Use child_process.execFile() or spawn() with an array of arguments and { shell: false }.",
                            )
                        )

                # --- JS004: Potentially unsafe SQL query construction ---
                elif (callee_name in SQL_QUERY_NAMES or "query" in full_callee.lower()) and first_arg and self._is_in_changed_lines(target_line):
                    is_dynamic_query = _is_dynamic_string(first_arg)
                    has_sql = _contains_sql_keywords(first_arg) or callee_name in ("$queryRawUnsafe", "$executeRawUnsafe")
                    if is_dynamic_query and has_sql:
                        self._add_finding(
                            CandidateFinding(
                                rule_id="JS004",
                                source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                                severity=FindingSeverity.HIGH,
                                category=FindingCategory.SECURITY_PATTERN,
                                file_path=self.file_path,
                                start_line=target_line,
                                end_line=target_line,
                                title="Potentially unsafe SQL query construction",
                                explanation=(
                                    "Interpolating variables or concatenating dynamic strings into database queries bypasses query parameterization "
                                    "and driver escaping, creating SQL injection vulnerabilities."
                                ),
                                suggested_fix="Use parameterized queries with placeholder bindings (e.g., db.query('SELECT * FROM t WHERE id = $1', [id])).",
                            )
                        )

            elif node_type == "NewExpression":
                callee = getattr(node, "callee", None)
                callee_name = _get_callee_name(callee)
                node_line = self._get_mapped_line(node)

                # --- JS001: new Function(...) ---
                if callee_name == "Function" and self._is_in_changed_lines(node_line):
                    self._add_finding(
                        CandidateFinding(
                            rule_id="JS001",
                            source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                            severity=FindingSeverity.HIGH,
                            category=FindingCategory.SECURITY_PATTERN,
                            file_path=self.file_path,
                            start_line=node_line,
                            end_line=node_line,
                            title="Potentially unsafe dynamic execution via new Function()",
                            explanation=(
                                "Using 'new Function()' dynamically compiles and executes code strings, "
                                "introducing arbitrary code execution risks similar to eval()."
                            ),
                            suggested_fix="Define static functions or use structured callbacks instead of dynamic Function construction.",
                        )
                    )

            # -----------------------------------------------------------------
            # 2. AssignmentExpression Checks (JS002: innerHTML / outerHTML)
            # -----------------------------------------------------------------
            elif node_type == "AssignmentExpression":
                left = getattr(node, "left", None)
                right = getattr(node, "right", None)
                if left and getattr(left, "type", None) in ("MemberExpression", "StaticMemberExpression"):
                    prop = getattr(left, "property", None)
                    prop_name = getattr(prop, "name", None) if prop else None
                    if prop_name in ("innerHTML", "outerHTML"):
                        target_line = self._get_mapped_line(right) or self._get_mapped_line(node)
                        if self._is_in_changed_lines(target_line):
                            self._add_finding(
                                CandidateFinding(
                                    rule_id="JS002",
                                    source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                                    severity=FindingSeverity.HIGH,
                                    category=FindingCategory.SECURITY_PATTERN,
                                    file_path=self.file_path,
                                    start_line=target_line,
                                    end_line=target_line,
                                    title=f"Potential DOM HTML injection via {prop_name} assignment",
                                    explanation=(
                                        f"Assigning dynamic content to '{prop_name}' renders unescaped HTML into the DOM, "
                                        "risking Cross-Site Scripting (XSS) if user input is rendered without sanitization."
                                    ),
                                    suggested_fix="Use 'textContent' or 'innerText' for text content, or sanitize markup with DOMPurify.",
                                )
                            )

            # -----------------------------------------------------------------
            # 3. Object Property / JSX Checks (JS002: dangerouslySetInnerHTML)
            # -----------------------------------------------------------------
            elif node_type == "Property":
                key = getattr(node, "key", None)
                key_name = getattr(key, "name", None) or getattr(key, "value", None)
                if key_name == "dangerouslySetInnerHTML":
                    target_line = self._get_mapped_line(node)
                    if self._is_in_changed_lines(target_line):
                        self._add_finding(
                            CandidateFinding(
                                rule_id="JS002",
                                source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                                severity=FindingSeverity.HIGH,
                                category=FindingCategory.SECURITY_PATTERN,
                                file_path=self.file_path,
                                start_line=target_line,
                                end_line=target_line,
                                title="Potential DOM HTML injection via dangerouslySetInnerHTML",
                                explanation=(
                                    "Rendering unescaped HTML using 'dangerouslySetInnerHTML' introduces Cross-Site Scripting (XSS) "
                                    "vulnerabilities if untrusted input is included."
                                ),
                                suggested_fix="Sanitize markup using a dedicated HTML sanitizer (e.g., DOMPurify) before passing to dangerouslySetInnerHTML.",
                            )
                        )

            # -----------------------------------------------------------------
            # 4. VariableDeclarator SQL Pattern Check (JS004)
            # -----------------------------------------------------------------
            elif node_type == "VariableDeclarator":
                init = getattr(node, "init", None)
                if init and _is_dynamic_string(init) and _contains_sql_keywords(init):
                    target_line = self._get_mapped_line(init) or self._get_mapped_line(node)
                    if self._is_in_changed_lines(target_line):
                        self._add_finding(
                            CandidateFinding(
                                rule_id="JS004",
                                source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                                severity=FindingSeverity.HIGH,
                                category=FindingCategory.SECURITY_PATTERN,
                                file_path=self.file_path,
                                start_line=target_line,
                                end_line=target_line,
                                title="Potentially unsafe SQL query construction via string formatting",
                                explanation=(
                                    "Constructing SQL query strings with string concatenation or template literal interpolation "
                                    "bypasses parameterization, creating SQL injection risks."
                                ),
                                suggested_fix="Pass parameters separately as query arguments to the database driver.",
                            )
                        )


def analyze_javascript_file_diff(file_diff: ParsedFileDiff) -> List[CandidateFinding]:
    """
    Run ESTree-based deterministic rules on the modified hunks of a JavaScript/TypeScript file.
    Supports .js, .jsx, .ts, and .tsx with diff line grounding.
    """
    if file_diff.is_binary or not file_diff.added_lines:
        return []

    findings: List[CandidateFinding] = []
    added_set = set(file_diff.added_lines)

    for hunk in file_diff.hunks:
        reconstructed_lines: List[str] = []
        line_mapping: Dict[int, int] = {}
        rel_idx = 1

        for diff_line in hunk.lines:
            if diff_line.type in ("+", " "):
                if diff_line.new_line_number is not None:
                    reconstructed_lines.append(diff_line.content)
                    line_mapping[rel_idx] = diff_line.new_line_number
                    rel_idx += 1

        snippet = "\n".join(reconstructed_lines)
        if not snippet.strip():
            continue

        is_ts_or_jsx = file_diff.file_path.lower().endswith((".ts", ".tsx", ".jsx"))
        parse_code = _preprocess_ts_and_jsx(snippet) if is_ts_or_jsx else snippet

        tree = None
        visitor_mapping = line_mapping

        # Attempt 1: Parse as ES Module
        try:
            tree = esprima.parseModule(parse_code, loc=True, tolerant=True)
        except Exception:
            # Attempt 2: If standard parse failed on .js, try preprocessing as well
            if not is_ts_or_jsx:
                try:
                    preprocessed = _preprocess_ts_and_jsx(snippet)
                    tree = esprima.parseModule(preprocessed, loc=True, tolerant=True)
                except Exception:
                    tree = None

            # Attempt 3: Parse as Script
            if tree is None:
                try:
                    tree = esprima.parseScript(parse_code, loc=True, tolerant=True)
                except Exception:
                    # Attempt 4: Synthetic function wrapper for indented statements
                    try:
                        wrapped = "function _synthetic_wrapper() {\n" + "\n".join("    " + line for line in parse_code.splitlines()) + "\n}"
                        tree = esprima.parseScript(wrapped, loc=True, tolerant=True)
                        visitor_mapping = {rel_i + 1: file_l for rel_i, file_l in line_mapping.items()}
                    except Exception:
                        tree = None

        if tree:
            visitor = JavaScriptAstRuleVisitor(
                file_path=file_diff.file_path,
                line_mapping=visitor_mapping,
                added_lines=added_set,
            )
            visitor.inspect(tree)
            findings.extend(visitor.findings)

    return findings
