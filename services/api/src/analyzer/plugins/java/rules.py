"""Deterministic Static Rules for Java (JV001 - JV004).

Rules:
- JV001: Potentially unsafe Java deserialization involving ObjectInputStream.readObject() / readUnshared().
- JV002: Potentially unsafe dynamic command construction passed to Runtime.exec() or ProcessBuilder.
- JV003: Potential SQL injection through dynamically constructed SQL passed to JDBC query or update methods.
- JV004: Potential path traversal involving dynamically constructed filesystem paths.
"""
import re
from typing import Dict, List, Optional, Set, Tuple
from pygments.lexers.jvm import JavaLexer
from pygments.token import Token

from src.analyzer.base import CandidateFinding
from src.parser.models import ParsedFileDiff, ParsedHunk
from src.schemas.findings import FindingCategory, FindingProvenance, FindingSeverity

SQL_KEYWORDS = {
    "SELECT", "INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
    "CREATE", "TABLE", "TRUNCATE", "FROM", "WHERE", "JOIN",
}

JDBC_CALL_NAMES = {
    "executeQuery", "executeUpdate", "execute", "addBatch",
    "prepareStatement", "prepareCall",
}

JDBC_RECEIVER_SUBSTRINGS = (
    "stmt", "statement", "conn", "connection", "jdbc", "datasource", "session",
)

PATH_CONSTRUCTOR_NAMES = {
    "File", "java.io.File",
    "FileInputStream", "java.io.FileInputStream",
    "FileOutputStream", "java.io.FileOutputStream",
    "FileReader", "java.io.FileReader",
    "FileWriter", "java.io.FileWriter",
}

PATH_METHOD_NAMES = {"get", "of"}


class JavaToken:
    """Represents a token with accurate source line and column coordinates."""
    __slots__ = ("ttype", "value", "line", "col")

    def __init__(self, ttype, value: str, line: int, col: int):
        self.ttype = ttype
        self.value = value
        self.line = line
        self.col = col

    def __repr__(self) -> str:
        return f"{self.value}"


class CallNode:
    """Represents a method invocation or constructor instantiation in Java."""
    __slots__ = ("kind", "target", "name", "args_tokens", "line")

    def __init__(self, kind: str, target: str, name: str, args_tokens: List[List[JavaToken]], line: int):
        self.kind = kind  # 'method' or 'constructor'
        self.target = target  # receiver string e.g. 'Runtime.getRuntime()'
        self.name = name  # method name or class name
        self.args_tokens = args_tokens  # list of token lists (one list per argument)
        self.line = line

    def get_arg_text(self, index: int = 0) -> str:
        if 0 <= index < len(self.args_tokens):
            return "".join(t.value for t in self.args_tokens[index])
        return ""


def tokenize_java(code: str) -> List[JavaToken]:
    """Tokenize Java source code and assign accurate 1-indexed line numbers."""
    lexer = JavaLexer(stripnl=False, ensurenl=False)
    tokens: List[JavaToken] = []
    line = 1
    col = 0
    for ttype, val in lexer.get_tokens(code):
        tok = JavaToken(ttype, val, line, col)
        tokens.append(tok)
        lines_in_val = val.count("\n")
        if lines_in_val > 0:
            line += lines_in_val
            col = len(val.split("\n")[-1])
        else:
            col += len(val)
    return tokens


def _extract_args(tokens: List[JavaToken], open_paren_idx: int) -> Tuple[List[List[JavaToken]], int]:
    """Extract argument token lists between matching '(' and ')'."""
    args: List[List[JavaToken]] = []
    curr_arg: List[JavaToken] = []
    depth = 1
    idx = open_paren_idx + 1
    n = len(tokens)

    while idx < n and depth > 0:
        t = tokens[idx]
        if t.value in ("(", "[", "{"):
            depth += 1
            curr_arg.append(t)
        elif t.value in (")", "]", "}"):
            depth -= 1
            if depth == 0:
                if curr_arg:
                    args.append(curr_arg)
                break
            else:
                curr_arg.append(t)
        elif t.value == "," and depth == 1:
            args.append(curr_arg)
            curr_arg = []
        else:
            curr_arg.append(t)
        idx += 1

    return args, idx


def parse_java_calls(code: str) -> List[CallNode]:
    """
    Parse method invocations and constructor instantiations from Java source code.
    Robust against incomplete diff fragments and syntax errors.
    """
    all_tokens = tokenize_java(code)
    # Filter out whitespace and comments while preserving line coordinates
    code_tokens = [
        t for t in all_tokens
        if t.ttype not in (
            Token.Text.Whitespace,
            Token.Comment,
            Token.Comment.Single,
            Token.Comment.Multiline,
        )
    ]

    calls: List[CallNode] = []
    i = 0
    n = len(code_tokens)

    while i < n:
        tok = code_tokens[i]

        # 1. Constructor call: 'new ClassName(...)'
        if tok.value == "new" and i + 1 < n:
            j = i + 1
            class_parts: List[str] = []
            while j < n and code_tokens[j].value != "(":
                # Skip generics e.g. <String>
                if code_tokens[j].value == "<":
                    depth = 1
                    j += 1
                    while j < n and depth > 0:
                        if code_tokens[j].value == "<":
                            depth += 1
                        elif code_tokens[j].value == ">":
                            depth -= 1
                        j += 1
                    continue
                class_parts.append(code_tokens[j].value)
                j += 1

            class_name = "".join(class_parts)
            if j < n and code_tokens[j].value == "(":
                call_line = tok.line
                args, next_idx = _extract_args(code_tokens, j)
                calls.append(CallNode("constructor", "", class_name, args, call_line))
                i = next_idx
                continue

        # 2. Method call: [receiver.]methodName(...)
        if tok.value == "(" and i > 0:
            prev = code_tokens[i - 1]
            if prev.ttype in (Token.Name, Token.Name.Function) or prev.value.isidentifier():
                method_name = prev.value
                call_line = prev.line

                # Trace backwards to reconstruct the receiver chain: e.g. 'Runtime.getRuntime().'
                receiver_parts: List[str] = []
                k = i - 2
                if k >= 0 and code_tokens[k].value == ".":
                    k -= 1
                    paren_depth = 0
                    while k >= 0:
                        t = code_tokens[k]
                        if t.value == ")":
                            paren_depth += 1
                            receiver_parts.insert(0, t.value)
                        elif t.value == "(":
                            paren_depth -= 1
                            receiver_parts.insert(0, t.value)
                            if paren_depth == 0 and k > 0 and code_tokens[k - 1].value == ".":
                                pass
                        elif paren_depth > 0:
                            receiver_parts.insert(0, t.value)
                        elif t.value == "." or t.ttype in (Token.Name, Token.Name.Class, Token.Name.Function) or t.value.isidentifier():
                            receiver_parts.insert(0, t.value)
                        else:
                            break
                        k -= 1

                receiver = "".join(receiver_parts)
                args, next_idx = _extract_args(code_tokens, i)
                calls.append(CallNode("method", receiver, method_name, args, call_line))
                i = next_idx
                continue

        i += 1

    return calls


def is_dynamic_argument(tokens: List[JavaToken]) -> bool:
    """
    Check if an argument expression is dynamically constructed at runtime.
    Returns True if:
    - Contains string concatenation '+' with at least one variable identifier.
    - Consists solely of a variable identifier.
    - Calls String.format(...) or uses dynamic string builders.
    Returns False for compile-time constants (literals).
    """
    if not tokens:
        return False

    # Check for '+' operator combined with identifiers
    has_plus = any(t.value == "+" and t.ttype in (Token.Operator, Token.Punctuation) for t in tokens)
    has_identifier = any(
        t.ttype in (Token.Name, Token.Name.Variable, Token.Name.Attribute) or (t.value.isidentifier() and t.value not in ("true", "false", "null"))
        for t in tokens
        if t.ttype not in (Token.Keyword, Token.Keyword.Type)
    )
    if has_plus and has_identifier:
        return True

    # If the expression is a single identifier variable (e.g. cmd, query, path)
    if len(tokens) == 1:
        tok = tokens[0]
        if tok.ttype in (Token.Name, Token.Name.Variable) and tok.value not in ("null", "true", "false"):
            return True

    # Check for String.format, MessageFormat.format, or .toString() calls
    arg_text = "".join(t.value for t in tokens)
    if "String.format" in arg_text or "MessageFormat.format" in arg_text:
        return True
    if ".toString()" in arg_text and ("builder" in arg_text.lower() or "buffer" in arg_text.lower()):
        return True

    return False


def argument_has_sql_keywords(tokens: List[JavaToken]) -> bool:
    """Check if any string literal token in the argument contains SQL keywords."""
    for t in tokens:
        if t.ttype in (Token.Literal.String, Token.Literal.String.Double, Token.Literal.String.Single):
            val_upper = t.value.upper()
            if any(kw in val_upper for kw in SQL_KEYWORDS):
                return True
    return False


def is_jdbc_receiver(receiver: str) -> bool:
    """Check if method receiver name looks like a JDBC statement or connection."""
    rec_lower = receiver.lower()
    return any(sub in rec_lower for sub in JDBC_RECEIVER_SUBSTRINGS)


def reconstruct_hunk_lines(hunk: ParsedHunk) -> Tuple[str, Dict[int, str]]:
    """
    Reconstruct unified diff hunk content preserving exact file line numbers.
    Lines prior to hunk start are padded with blank lines so that line numbers match.
    """
    lines_by_num: Dict[int, str] = {}
    for line in hunk.lines:
        if line.type in ("+", " ") and line.new_line_number is not None:
            lines_by_num[line.new_line_number] = line.content

    if not lines_by_num:
        return "", {}

    max_line = max(lines_by_num.keys())
    padded_lines = [""] * max_line
    for num, content in lines_by_num.items():
        padded_lines[num - 1] = content

    return "\n".join(padded_lines), lines_by_num


def check_jv001_deserialization(call: CallNode, hunk_added_lines: Set[int], file_path: str) -> Optional[CandidateFinding]:
    """JV001: ObjectInputStream.readObject() / readUnshared()."""
    if call.kind == "method" and call.name in ("readObject", "readUnshared"):
        if call.line in hunk_added_lines:
            target_str = f"{call.target}." if call.target else ""
            evidence = f"{target_str}{call.name}()"
            return CandidateFinding(
                rule_id="JV001",
                source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                severity=FindingSeverity.HIGH,
                category=FindingCategory.SECURITY_PATTERN,
                file_path=file_path,
                start_line=call.line,
                end_line=call.line,
                title="Potential Unsafe Java Deserialization (ObjectInputStream.readObject)",
                explanation=(
                    f"Detected call to '{evidence}'. Deserializing untrusted byte streams using "
                    "ObjectInputStream without an ObjectInputFilter can lead to arbitrary remote code execution "
                    "via gadget chain exploitation (CWE-502)."
                ),
                suggested_fix=(
                    "Configure an ObjectInputFilter (Java 9+) or use safe serialization alternatives "
                    "such as JSON, Protocol Buffers, or Jackson with safe polymorphic typing."
                ),
            )
    return None


def check_jv002_command_injection(call: CallNode, hunk_added_lines: Set[int], file_path: str) -> Optional[CandidateFinding]:
    """JV002: Runtime.exec() or ProcessBuilder with dynamic command construction."""
    # Pattern 1: Runtime.exec(...)
    if call.kind == "method" and call.name in ("exec", "execSync"):
        if "Runtime" in call.target or call.target.lower() in ("runtime", "rt", "r"):
            if call.args_tokens and is_dynamic_argument(call.args_tokens[0]):
                if call.line in hunk_added_lines:
                    arg_str = call.get_arg_text(0)
                    evidence = f"{call.target}.{call.name}({arg_str})"
                    return CandidateFinding(
                        rule_id="JV002",
                        source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                        severity=FindingSeverity.HIGH,
                        category=FindingCategory.SECURITY_PATTERN,
                        file_path=file_path,
                        start_line=call.line,
                        end_line=call.line,
                        title="Potential Unsafe Shell Command Construction (Command Injection)",
                        explanation=(
                            f"Detected dynamically constructed command passed to Runtime.exec(): '{evidence}'. "
                            "Constructing shell commands using string concatenation or variables may allow command injection (CWE-78)."
                        ),
                        suggested_fix=(
                            "Pass arguments as a discrete String[] array or use ProcessBuilder with individual argument tokens "
                            "without invoking shell interpreters (sh -c / cmd.exe)."
                        ),
                    )

    # Pattern 2: new ProcessBuilder(...)
    if call.kind == "constructor" and call.name in ("ProcessBuilder", "java.lang.ProcessBuilder"):
        if any(is_dynamic_argument(arg) for arg in call.args_tokens):
            if call.line in hunk_added_lines:
                evidence = f"new ProcessBuilder({', '.join(call.get_arg_text(i) for i in range(len(call.args_tokens)))})"
                return CandidateFinding(
                    rule_id="JV002",
                    source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    severity=FindingSeverity.HIGH,
                    category=FindingCategory.SECURITY_PATTERN,
                    file_path=file_path,
                    start_line=call.line,
                    end_line=call.line,
                    title="Potential Unsafe Shell Command Construction (ProcessBuilder)",
                    explanation=(
                        f"Detected dynamically concatenated command tokens in ProcessBuilder: '{evidence}'. "
                        "Passing untrusted inputs into command lists can lead to argument injection (CWE-78)."
                    ),
                    suggested_fix=(
                        "Ensure all command arguments are strictly validated against an allowlist and not concatenated dynamically."
                    ),
                )
    return None


def check_jv003_sql_injection(call: CallNode, hunk_added_lines: Set[int], file_path: str) -> Optional[CandidateFinding]:
    """JV003: JDBC SQL query construction with string concatenation or dynamic formatting."""
    if call.kind == "method" and call.name in JDBC_CALL_NAMES:
        if call.args_tokens:
            sql_arg = call.args_tokens[0]
            if is_dynamic_argument(sql_arg):
                # Must contain SQL keywords or have a JDBC-like receiver name to avoid false positives on non-SQL methods
                if argument_has_sql_keywords(sql_arg) or is_jdbc_receiver(call.target):
                    if call.line in hunk_added_lines:
                        arg_str = call.get_arg_text(0)
                        evidence = f"{call.target}.{call.name}({arg_str})"
                        return CandidateFinding(
                            rule_id="JV003",
                            source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                            severity=FindingSeverity.HIGH,
                            category=FindingCategory.SECURITY_PATTERN,
                            file_path=file_path,
                            start_line=call.line,
                            end_line=call.line,
                            title="Potential SQL Injection in JDBC Query Construction",
                            explanation=(
                                f"Detected dynamically constructed SQL query passed to JDBC method: '{evidence}'. "
                                "Concatenating variables into SQL strings can allow SQL injection attacks (CWE-89)."
                            ),
                            suggested_fix=(
                                "Use parameterized queries with PreparedStatement and bind variables ('?') "
                                "instead of dynamic string concatenation."
                            ),
                        )
    return None


def check_jv004_path_traversal(call: CallNode, hunk_added_lines: Set[int], file_path: str) -> Optional[CandidateFinding]:
    """JV004: Potential path traversal in filesystem operations."""
    # Pattern 1: new File(...), new FileInputStream(...), etc.
    if call.kind == "constructor" and call.name in PATH_CONSTRUCTOR_NAMES:
        if any(is_dynamic_argument(arg) for arg in call.args_tokens):
            if call.line in hunk_added_lines:
                evidence = f"new {call.name}({', '.join(call.get_arg_text(i) for i in range(len(call.args_tokens)))})"
                return CandidateFinding(
                    rule_id="JV004",
                    source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    severity=FindingSeverity.MEDIUM,
                    category=FindingCategory.SECURITY_PATTERN,
                    file_path=file_path,
                    start_line=call.line,
                    end_line=call.line,
                    title="Potential Path Traversal in Filesystem Path Construction",
                    explanation=(
                        f"Detected dynamically constructed filesystem path: '{evidence}'. "
                        "Concatenating user-controlled variables into file paths can allow path traversal (CWE-22)."
                    ),
                    suggested_fix=(
                        "Normalize the path using Path.normalize() and verify that the canonical path starts "
                        "with the expected base directory (e.g. file.toPath().toRealPath().startsWith(baseDir))."
                    ),
                )

    # Pattern 2: Paths.get(...) or Path.of(...)
    if call.kind == "method" and call.name in PATH_METHOD_NAMES and ("Paths" in call.target or "Path" in call.target):
        if any(is_dynamic_argument(arg) for arg in call.args_tokens):
            if call.line in hunk_added_lines:
                evidence = f"{call.target}.{call.name}({', '.join(call.get_arg_text(i) for i in range(len(call.args_tokens)))})"
                return CandidateFinding(
                    rule_id="JV004",
                    source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    severity=FindingSeverity.MEDIUM,
                    category=FindingCategory.SECURITY_PATTERN,
                    file_path=file_path,
                    start_line=call.line,
                    end_line=call.line,
                    title="Potential Path Traversal in Filesystem Path Construction",
                    explanation=(
                        f"Detected dynamically constructed filesystem path via '{evidence}'. "
                        "Unvalidated path components can lead to path traversal vulnerabilities (CWE-22)."
                    ),
                    suggested_fix=(
                        "Use Path.normalize() and assert that path.toRealPath().startsWith(baseDir) before accessing files."
                    ),
                )

    return None


def analyze_java_file_diff(file_diff: ParsedFileDiff) -> List[CandidateFinding]:
    """
    Run deterministic Java AST static analysis across changed hunks in a Java file diff.
    Grounds all findings strictly to diff added lines.
    """
    if file_diff.is_binary or not file_diff.hunks:
        return []

    findings: List[CandidateFinding] = []
    seen_keys: Set[Tuple[str, int]] = set()

    for hunk in file_diff.hunks:
        hunk_added_lines = set(hunk.added_lines)
        if not hunk_added_lines:
            continue

        reconstructed_code, _ = reconstruct_hunk_lines(hunk)
        if not reconstructed_code.strip():
            continue

        calls = parse_java_calls(reconstructed_code)

        for call in calls:
            # Check rules
            candidate = (
                check_jv001_deserialization(call, hunk_added_lines, file_diff.file_path)
                or check_jv002_command_injection(call, hunk_added_lines, file_diff.file_path)
                or check_jv003_sql_injection(call, hunk_added_lines, file_diff.file_path)
                or check_jv004_path_traversal(call, hunk_added_lines, file_diff.file_path)
            )

            if candidate and candidate.start_line is not None:
                key = (candidate.rule_id, candidate.start_line)
                if key not in seen_keys:
                    seen_keys.add(key)
                    findings.append(candidate)

    return findings
