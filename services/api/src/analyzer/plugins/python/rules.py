"""Deterministic Python Static Analysis Rules using AST and Structural Heuristics."""
import ast
import re
from typing import Dict, List, Optional, Set, Tuple
from src.parser.models import ParsedFileDiff, ParsedHunk
from src.schemas.findings import FindingCategory, FindingProvenance, FindingSeverity
from src.analyzer.base import CandidateFinding


SQL_KEYWORDS_REGEX = re.compile(
    r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|FROM|WHERE|JOIN)\b",
    re.IGNORECASE,
)


class PythonAstRuleVisitor(ast.NodeVisitor):
    """AST Visitor detecting deterministic Python code smells, bugs, and security risks."""

    def __init__(self, file_path: str, line_mapping: Dict[int, int], added_lines: Set[int]):
        self.file_path = file_path
        self.line_mapping = line_mapping  # AST lineno -> actual new file lineno
        self.added_lines = added_lines  # actual line numbers added/modified in diff
        self.findings: List[CandidateFinding] = []

    def _get_actual_line(self, node: ast.AST) -> Optional[int]:
        ast_lineno = getattr(node, "lineno", None)
        if ast_lineno is None:
            return None
        return self.line_mapping.get(ast_lineno, ast_lineno)

    def _is_in_changed_lines(self, actual_line: Optional[int]) -> bool:
        if actual_line is None:
            return False
        return actual_line in self.added_lines

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        """PY002: Bare except, BaseException, or silently passed exceptions."""
        actual_line = self._get_actual_line(node)
        if self._is_in_changed_lines(actual_line):
            # 1. Bare except:
            if node.type is None:
                self.findings.append(
                    CandidateFinding(
                        rule_id="PY002",
                        source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                        severity=FindingSeverity.HIGH,
                        category=FindingCategory.EXCEPTION_HANDLING,
                        file_path=self.file_path,
                        start_line=actual_line,
                        end_line=actual_line,
                        title="Bare except clause catches BaseException",
                        explanation=(
                            "A bare 'except:' clause intercepts all exceptions including "
                            "KeyboardInterrupt, SystemExit, and MemoryError, masking critical "
                            "runtime defects and preventing graceful shutdown."
                        ),
                        suggested_fix="Catch specific exception types (e.g., 'except (ValueError, KeyError):') or 'except Exception:'.",
                    )
                )
            # 2. Catching BaseException explicitly
            elif isinstance(node.type, ast.Name) and node.type.id == "BaseException":
                self.findings.append(
                    CandidateFinding(
                        rule_id="PY002",
                        source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                        severity=FindingSeverity.HIGH,
                        category=FindingCategory.EXCEPTION_HANDLING,
                        file_path=self.file_path,
                        start_line=actual_line,
                        end_line=actual_line,
                        title="Explicit catching of BaseException",
                        explanation="Catching 'BaseException' suppresses interpreter signals like SystemExit and KeyboardInterrupt.",
                        suggested_fix="Catch 'Exception' or specific application exception subclasses instead of BaseException.",
                    )
                )
            # 3. Suppressing Exception with a bare pass
            elif len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                self.findings.append(
                    CandidateFinding(
                        rule_id="PY002",
                        source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                        severity=FindingSeverity.MEDIUM,
                        category=FindingCategory.EXCEPTION_HANDLING,
                        file_path=self.file_path,
                        start_line=actual_line,
                        end_line=actual_line,
                        title="Silent exception suppression with bare pass",
                        explanation="The exception is caught and discarded silently with 'pass', concealing errors from logs and callers.",
                        suggested_fix="Log the caught exception or re-raise it if handling cannot recover.",
                    )
                )

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """PY003: Mutable default function arguments."""
        # Check positional defaults
        for default in node.args.defaults:
            actual_line = self._get_actual_line(default) or self._get_actual_line(node)
            if self._is_in_changed_lines(actual_line):
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    self.findings.append(
                        CandidateFinding(
                            rule_id="PY003",
                            source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                            severity=FindingSeverity.MEDIUM,
                            category=FindingCategory.CODE_QUALITY,
                            file_path=self.file_path,
                            start_line=actual_line,
                            end_line=actual_line,
                            title=f"Mutable default argument in function '{node.name}'",
                            explanation=(
                                f"Function '{node.name}' defines a mutable default parameter ({type(default).__name__.lower()}). "
                                "In Python, default arguments are evaluated only once at definition time, "
                                "sharing state across all function calls."
                            ),
                            suggested_fix="Use 'None' as the default argument value and initialize the mutable object inside the function body.",
                        )
                    )
                elif isinstance(default, ast.Call) and isinstance(default.func, ast.Name):
                    if default.func.id in ("list", "dict", "set"):
                        self.findings.append(
                            CandidateFinding(
                                rule_id="PY003",
                                source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                                severity=FindingSeverity.MEDIUM,
                                category=FindingCategory.CODE_QUALITY,
                                file_path=self.file_path,
                                start_line=actual_line,
                                end_line=actual_line,
                                title=f"Mutable constructor default in function '{node.name}'",
                                explanation=(
                                    f"Function '{node.name}' calls '{default.func.id}()' as a default argument, "
                                    "which creates a single shared instance evaluated once at module import."
                                ),
                                suggested_fix="Default to 'None' and instantiate inside the function: 'if arg is None: arg = ...'.",
                            )
                        )

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Also check async function definitions for mutable defaults."""
        for default in node.args.defaults:
            actual_line = self._get_actual_line(default) or self._get_actual_line(node)
            if self._is_in_changed_lines(actual_line) and isinstance(default, (ast.List, ast.Dict, ast.Set)):
                self.findings.append(
                    CandidateFinding(
                        rule_id="PY003",
                        source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                        severity=FindingSeverity.MEDIUM,
                        category=FindingCategory.CODE_QUALITY,
                        file_path=self.file_path,
                        start_line=actual_line,
                        end_line=actual_line,
                        title=f"Mutable default argument in async function '{node.name}'",
                        explanation="Default argument is a mutable literal evaluated once at function definition time.",
                        suggested_fix="Use 'None' as default value and initialize inside function body.",
                    )
                )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        """PY004: Unsafe eval, pickle deserialization, and SQL string concatenation."""
        actual_line = self._get_actual_line(node)

        if self._is_in_changed_lines(actual_line):
            # 1. Direct call to eval() or exec()
            if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"):
                self.findings.append(
                    CandidateFinding(
                        rule_id="PY004",
                        source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                        severity=FindingSeverity.CRITICAL,
                        category=FindingCategory.SECURITY_PATTERN,
                        file_path=self.file_path,
                        start_line=actual_line,
                        end_line=actual_line,
                        title=f"Potentially unsafe dynamic execution with '{node.func.id}()'",
                        explanation=(
                            f"Using '{node.func.id}()' executes arbitrary code strings at runtime. "
                            "If any portion of the input originates from external sources, this enables remote code execution."
                        ),
                        suggested_fix="Use 'ast.literal_eval()' for safe literal evaluation or replace with static dispatch parsing.",
                    )
                )

            # 2. pickle.loads / pickle.load
            elif isinstance(node.func, ast.Attribute) and node.func.attr in ("loads", "load"):
                is_pickle = False
                if isinstance(node.func.value, ast.Name) and node.func.value.id in ("pickle", "_pickle"):
                    is_pickle = True
                if is_pickle:
                    self.findings.append(
                        CandidateFinding(
                            rule_id="PY004",
                            source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                            severity=FindingSeverity.CRITICAL,
                            category=FindingCategory.SECURITY_PATTERN,
                            file_path=self.file_path,
                            start_line=actual_line,
                            end_line=actual_line,
                            title="Insecure deserialization via pickle",
                            explanation=(
                                "The 'pickle' module is not secure against erroneous or maliciously constructed data. "
                                "Deserializing untrusted payloads can trigger arbitrary code execution via __reduce__."
                            ),
                            suggested_fix="Use safer data interchange formats such as JSON, Protocol Buffers, or messagepack.",
                        )
                    )

            # 3. SQL string formatting or concatenation in database execute calls
            if isinstance(node.func, ast.Attribute) and node.func.attr in ("execute", "executemany"):
                if node.args:
                    query_arg = node.args[0]
                    # Check if query arg is an f-string
                    if isinstance(query_arg, ast.JoinedStr):
                        # Extract static text fragments
                        static_parts = [
                            part.value for part in query_arg.values if isinstance(part, ast.Constant) and isinstance(part.value, str)
                        ]
                        full_static = " ".join(static_parts)
                        if SQL_KEYWORDS_REGEX.search(full_static):
                            self.findings.append(
                                CandidateFinding(
                                    rule_id="PY004",
                                    source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                                    severity=FindingSeverity.HIGH,
                                    category=FindingCategory.SECURITY_PATTERN,
                                    file_path=self.file_path,
                                    start_line=actual_line,
                                    end_line=actual_line,
                                    title="Potential SQL injection via f-string query formatting",
                                    explanation=(
                                        "A SQL command is being assembled using Python f-string interpolation inside an 'execute()' call. "
                                        "This bypasses database driver escaping and allows SQL injection."
                                    ),
                                    suggested_fix="Use parameterized queries with placeholder bindings (e.g., 'execute(query, (param1, param2))').",
                                )
                            )
                    # Check if query arg is string concatenation (+) or % formatting
                    elif isinstance(query_arg, ast.BinOp):
                        if isinstance(query_arg.op, (ast.Add, ast.Mod)):
                            self.findings.append(
                                CandidateFinding(
                                    rule_id="PY004",
                                    source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                                    severity=FindingSeverity.HIGH,
                                    category=FindingCategory.SECURITY_PATTERN,
                                    file_path=self.file_path,
                                    start_line=actual_line,
                                    end_line=actual_line,
                                    title="Potential SQL injection via string concatenation or % formatting",
                                    explanation=(
                                        "Constructing SQL queries using string formatting or '+' concatenation exposes the application "
                                        "to SQL injection if any interpolated variable contains user input."
                                    ),
                                    suggested_fix="Pass parameters separately as query arguments to the database driver.",
                                )
                            )

        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript):
        """PY001: Context-aware check for missing input validation on external payload/request values."""
        actual_line = self._get_actual_line(node)
        if self._is_in_changed_lines(actual_line):
            # Check dictionary access on request/payload/params variables
            var_name = None
            if isinstance(node.value, ast.Name):
                var_name = node.value.id.lower()
            elif isinstance(node.value, ast.Attribute):
                var_name = node.value.attr.lower()

            target_keywords = ("payload", "request_data", "raw_input", "user_input", "post_data")
            if var_name and any(k in var_name for k in target_keywords):
                # Check if key is accessed as string literal
                key_name = None
                if isinstance(node.slice, ast.Constant):
                    key_name = str(node.slice.value)

                self.findings.append(
                    CandidateFinding(
                        rule_id="PY001",
                        source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                        severity=FindingSeverity.MEDIUM,
                        category=FindingCategory.INPUT_VALIDATION,
                        file_path=self.file_path,
                        start_line=actual_line,
                        end_line=actual_line,
                        title=f"Unchecked dictionary access on '{var_name}'",
                        explanation=(
                            f"Direct key access '{var_name}[{repr(key_name) if key_name else '...'}]' without prior verification "
                            "raises an unhandled KeyError if the external payload does not contain the expected field."
                        ),
                        suggested_fix=f"Use '{var_name}.get({repr(key_name) if key_name else '...'})' with a default or validate schema before access.",
                    )
                )

        self.generic_visit(node)


def analyze_python_file_diff(file_diff: ParsedFileDiff, all_pr_files: Optional[List[str]] = None) -> List[CandidateFinding]:
    """
    Run AST-based deterministic rules on the modified hunks of a Python file.
    """
    if file_diff.is_binary or not file_diff.added_lines:
        return []

    findings: List[CandidateFinding] = []
    added_set = set(file_diff.added_lines)

    # 1. Inspect each hunk by reconstructing its new text with line mapping
    for hunk in file_diff.hunks:
        reconstructed_lines: List[str] = []
        line_mapping: Dict[int, int] = {}  # 1-indexed relative line -> file line
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

        # Try parsing full snippet; if indented block, try dedenting and re-mapping
        tree = None
        try:
            tree = ast.parse(snippet)
        except SyntaxError:
            # Attempt parsing wrapped in synthetic function to handle indented statements
            try:
                wrapped = "def _synthetic_wrapper():\n" + "\n".join("    " + line for line in reconstructed_lines)
                wrapped_tree = ast.parse(wrapped)
                # Remap: wrapped line numbers are offset by 1
                wrapped_mapping = {ast_l - 1: file_l for ast_l, file_l in line_mapping.items()}
                visitor = PythonAstRuleVisitor(
                    file_path=file_diff.file_path, line_mapping=line_mapping, added_lines=added_set
                )
                visitor.visit(wrapped_tree)
                findings.extend(visitor.findings)
                continue
            except Exception:
                pass

        if tree:
            visitor = PythonAstRuleVisitor(
                file_path=file_diff.file_path, line_mapping=line_mapping, added_lines=added_set
            )
            visitor.visit(tree)
            findings.extend(visitor.findings)

    # 2. Rule PY005: Test Suggestion Heuristic
    # If business logic in this file has changes, check if test files were touched in the PR
    norm_path = file_diff.file_path.lower()
    is_test_file = (
        norm_path.startswith("test_")
        or norm_path.endswith("_test.py")
        or "/tests/" in norm_path
        or "\\tests\\" in norm_path
        or norm_path.startswith("tests/")
    )

    if not is_test_file and file_diff.added_lines and all_pr_files is not None:
        has_tests_in_pr = any(
            f.lower().startswith("test_")
            or f.lower().endswith("_test.py")
            or "/tests/" in f.lower()
            or "\\tests\\" in f.lower()
            or f.lower().startswith("tests/")
            for f in all_pr_files
        )
        if not has_tests_in_pr:
            # Anchor to the first added line of the file
            first_changed_line = file_diff.added_lines[0]
            findings.append(
                CandidateFinding(
                    rule_id="PY005",
                    source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    severity=FindingSeverity.INFO,
                    category=FindingCategory.TEST_SUGGESTION,
                    file_path=file_diff.file_path,
                    start_line=first_changed_line,
                    end_line=first_changed_line,
                    title="Missing test coverage for modified logic",
                    explanation=(
                        f"Pull request modifies business logic in '{file_diff.file_path}', "
                        "but no test files (e.g., in 'tests/' or 'test_*.py') were added or updated."
                    ),
                    suggested_fix="Add unit tests covering the new or changed code paths.",
                )
            )

    return findings
