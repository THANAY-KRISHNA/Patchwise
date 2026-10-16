"""Deterministic Static Rules for C and C++ (CC001 - CC004).

Rules:
- CC001: Risky unbounded string operations or formatting APIs (gets, strcpy, strcat, sprintf, vsprintf).
- CC002: Potential format-string misuse (non-literal format argument in printf-family functions).
- CC003: Potential command injection via dynamically constructed commands in system(), popen(), or _popen().
- CC004: Insecure temporary-name APIs susceptible to race conditions (tmpnam, tempnam, mktemp).

Detection method:
Lexical tokenization and syntax-aware call extraction via Pygments CLexer/CppLexer.
This is a lightweight token-based static check with exact diff line grounding,
not a compiler AST or interprocedural data-flow engine.
"""
import os
import re
from typing import Dict, List, Optional, Set, Tuple
from pygments.lexers.c_cpp import CLexer, CppLexer
from pygments.token import Token

from src.analyzer.base import CandidateFinding
from src.parser.models import ParsedFileDiff, ParsedHunk
from src.schemas.findings import FindingCategory, FindingProvenance, FindingSeverity

UNBOUNDED_STRING_FUNCS = {"gets", "strcpy", "strcat", "sprintf", "vsprintf"}
TEMP_FILE_FUNCS = {"tmpnam", "tempnam", "mktemp"}
EXEC_FUNCS = {"system", "popen", "_popen"}

# Format string functions and the 0-indexed position of their format argument
FORMAT_STRING_FUNCS: Dict[str, int] = {
    "printf": 0,
    "wprintf": 0,
    "vprintf": 0,
    "vwprintf": 0,
    "fprintf": 1,
    "fwprintf": 1,
    "vfprintf": 1,
    "vfwprintf": 1,
    "sprintf": 1,
    "wsprintf": 1,
    "vsprintf": 1,
    "snprintf": 2,
    "vsnprintf": 2,
    "swprintf": 2,
    "vswprintf": 2,
    "syslog": 1,
    "vsyslog": 1,
    "dprintf": 1,
    "vdprintf": 1,
    "asprintf": 1,
    "vasprintf": 1,
}


class CppToken:
    """Represents a lexical token with 1-indexed source line and column coordinates."""
    __slots__ = ("ttype", "value", "line", "col")

    def __init__(self, ttype, value: str, line: int, col: int):
        self.ttype = ttype
        self.value = value
        self.line = line
        self.col = col

    def __repr__(self) -> str:
        return f"{self.value}"


class CppCallNode:
    """Represents a function call invocation in C/C++ source code."""
    __slots__ = ("target", "name", "args_tokens", "line")

    def __init__(self, target: str, name: str, args_tokens: List[List[CppToken]], line: int):
        self.target = target  # e.g., 'std::' or receiver object
        self.name = name      # e.g., 'strcpy', 'printf', 'system'
        self.args_tokens = args_tokens
        self.line = line

    def get_arg_text(self, index: int = 0) -> str:
        if 0 <= index < len(self.args_tokens):
            return "".join(t.value for t in self.args_tokens[index]).strip()
        return ""


def tokenize_cpp(code: str, file_path: str = "main.cpp") -> List[CppToken]:
    """Tokenize C or C++ source code preserving exact 1-indexed line numbers."""
    _, ext = os.path.splitext(file_path.lower())
    is_c_only = ext in (".c", ".h")
    lexer = CLexer(stripnl=False, ensurenl=False) if is_c_only else CppLexer(stripnl=False, ensurenl=False)

    tokens: List[CppToken] = []
    line = 1
    col = 0
    for ttype, val in lexer.get_tokens(code):
        tok = CppToken(ttype, val, line, col)
        tokens.append(tok)
        lines_in_val = val.count("\n")
        if lines_in_val > 0:
            line += lines_in_val
            col = len(val.split("\n")[-1])
        else:
            col += len(val)
    return tokens


def is_whitespace_or_comment(tok: CppToken) -> bool:
    """Return True if token is whitespace, comment, or blank text."""
    return tok.ttype in Token.Text or tok.ttype in Token.Comment or not tok.value.strip()


def _extract_args(tokens: List[CppToken], open_paren_idx: int) -> Tuple[List[List[CppToken]], int]:
    """Extract argument token lists between matching '(' and ')'."""
    args: List[List[CppToken]] = []
    curr_arg: List[CppToken] = []
    depth = 1
    idx = open_paren_idx + 1
    n = len(tokens)

    while idx < n and depth > 0:
        tok = tokens[idx]
        val = tok.value

        if val in ("(", "{", "["):
            depth += 1
            curr_arg.append(tok)
        elif val in (")", "}", "]"):
            depth -= 1
            if depth == 0:
                break
            curr_arg.append(tok)
        elif val == "," and depth == 1:
            args.append(curr_arg)
            curr_arg = []
        else:
            curr_arg.append(tok)
        idx += 1

    if curr_arg:
        # Check if argument has non-whitespace content
        if any(not is_whitespace_or_comment(t) for t in curr_arg):
            args.append(curr_arg)

    return args, idx


def parse_cpp_calls(code: str, file_path: str = "main.cpp") -> List[CppCallNode]:
    """
    Parse function call expressions from C/C++ tokens.
    Extracts function name, receiver namespace, arguments, and line numbers.
    """
    tokens = tokenize_cpp(code, file_path)
    calls: List[CppCallNode] = []
    n = len(tokens)
    idx = 0

    while idx < n:
        tok = tokens[idx]

        # Look for identifiers
        if tok.ttype in (Token.Name, Token.Name.Function, Token.Name.Builtin):
            name = tok.value
            call_line = tok.line

            # Check preceding tokens for namespace or receiver: e.g. std:: or obj. or ptr->
            target = ""
            p_idx = idx - 1
            # Skip preceding whitespace
            while p_idx >= 0 and is_whitespace_or_comment(tokens[p_idx]):
                p_idx -= 1
            if p_idx >= 0 and tokens[p_idx].value in ("::", ".", "->"):
                op = tokens[p_idx].value
                p_idx -= 1
                while p_idx >= 0 and is_whitespace_or_comment(tokens[p_idx]):
                    p_idx -= 1
                if p_idx >= 0 and tokens[p_idx].ttype in (Token.Name, Token.Name.Namespace):
                    target = tokens[p_idx].value + op
                else:
                    target = op

            # Look forward for '('
            f_idx = idx + 1
            while f_idx < n and is_whitespace_or_comment(tokens[f_idx]):
                f_idx += 1

            if f_idx < n and tokens[f_idx].value == "(":
                args, end_paren_idx = _extract_args(tokens, f_idx)
                calls.append(CppCallNode(target=target, name=name, args_tokens=args, line=call_line))
                idx = end_paren_idx
        idx += 1

    return calls


def is_literal_string_argument(tokens: List[CppToken]) -> bool:
    """
    Check if an argument consists purely of string literal tokens
    (and optional string literal concatenation like "part1 " "part2").
    """
    non_ws_tokens = [t for t in tokens if not is_whitespace_or_comment(t)]
    if not non_ws_tokens:
        return False

    # In C/C++, adjacent string literals are concatenated: "a" "b"
    # All non-whitespace tokens must be string literal tokens (e.g. String.Double, String.Escape)
    for t in non_ws_tokens:
        if t.ttype not in Token.Literal.String:
            return False
    return True


def is_dynamic_command_argument(tokens: List[CppToken]) -> bool:
    """
    Returns True if an argument is dynamically constructed (not a pure static string literal).
    Returns False if it is a pure string literal or empty.
    """
    non_ws_tokens = [t for t in tokens if not is_whitespace_or_comment(t)]
    if not non_ws_tokens:
        return False

    # If it is entirely string literals, it is a fixed command (e.g. system("ls -la"))
    if is_literal_string_argument(tokens):
        return False

    # Any identifier, operator (+, <<), function call, or non-literal expression is dynamic
    return True


def reconstruct_hunk_lines(hunk: ParsedHunk) -> Tuple[str, Dict[int, str]]:
    """
    Reconstruct unified diff hunk content preserving exact file line numbers.
    Lines prior to hunk start are padded with blank lines so that 1-indexed lines match.
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


def check_cc001_unbounded_string(call: CppCallNode, hunk_added_lines: Set[int], file_path: str) -> Optional[CandidateFinding]:
    """CC001: Risky unbounded string operations or formatting APIs."""
    if call.name in UNBOUNDED_STRING_FUNCS:
        if call.line in hunk_added_lines:
            target_prefix = call.target if call.target else ""
            arg_preview = ", ".join(call.get_arg_text(i) for i in range(min(2, len(call.args_tokens))))
            evidence = f"{target_prefix}{call.name}({arg_preview})"

            remediations = {
                "gets": "Replace with fgets(buf, sizeof(buf), stdin) to enforce bounded reads.",
                "strcpy": "Replace with strncpy, strlcpy, or C++ std::string / std::string_view.",
                "strcat": "Replace with strncat, strlcat, or C++ std::string::operator+=.",
                "sprintf": "Replace with snprintf(buf, sizeof(buf), fmt, ...) or C++ std::format / fmt::format.",
                "vsprintf": "Replace with vsnprintf(buf, sizeof(buf), fmt, args) to bound target buffer writes.",
            }
            fix = remediations.get(call.name, "Use bounds-checked string APIs.")

            return CandidateFinding(
                rule_id="CC001",
                source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                severity=FindingSeverity.HIGH if call.name in ("gets", "strcpy") else FindingSeverity.MEDIUM,
                category=FindingCategory.SECURITY_PATTERN,
                file_path=file_path,
                start_line=call.line,
                end_line=call.line,
                title=f"Risky Unbounded String Operation ({call.name})",
                explanation=(
                    f"Detected invocation of unbounded API '{evidence}'. "
                    f"The function '{call.name}' does not check target buffer capacities, introducing buffer overflow "
                    "vulnerabilities (CWE-120, CWE-676) if input lengths exceed destination bounds. "
                    "Note: API detection flags high-risk usage patterns; exploitability depends on caller buffer allocation."
                ),
                suggested_fix=fix,
            )
    return None


def check_cc002_format_string(call: CppCallNode, hunk_added_lines: Set[int], file_path: str) -> Optional[CandidateFinding]:
    """CC002: Format-string misuse (non-literal format argument in printf-family)."""
    if call.name in FORMAT_STRING_FUNCS:
        fmt_idx = FORMAT_STRING_FUNCS[call.name]
        if len(call.args_tokens) > fmt_idx:
            fmt_arg_tokens = call.args_tokens[fmt_idx]
            # Flag if format argument is NOT a string literal (e.g. printf(user_input))
            if not is_literal_string_argument(fmt_arg_tokens):
                if call.line in hunk_added_lines:
                    fmt_text = call.get_arg_text(fmt_idx)
                    evidence = f"{call.target}{call.name}(..., {fmt_text}, ...)" if fmt_idx > 0 else f"{call.target}{call.name}({fmt_text})"
                    return CandidateFinding(
                        rule_id="CC002",
                        source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                        severity=FindingSeverity.HIGH,
                        category=FindingCategory.SECURITY_PATTERN,
                        file_path=file_path,
                        start_line=call.line,
                        end_line=call.line,
                        title="Potential Format String Vulnerability (Non-literal Format)",
                        explanation=(
                            f"Detected non-literal format argument passed to '{call.name}': '{evidence}'. "
                            "Passing variable or user-controlled strings as format specifiers allows attackers to read or write arbitrary "
                            "stack memory via format specifiers like %x, %s, or %n (CWE-134)."
                        ),
                        suggested_fix=(
                            f'Pass a static format string with %s placeholder instead, e.g.: {call.name}("%s", {fmt_text})'
                            if fmt_idx == 0
                            else f'Use a fixed format string, e.g.: {call.name}(..., "%s", {fmt_text})'
                        ),
                    )
    return None


def check_cc003_command_injection(call: CppCallNode, hunk_added_lines: Set[int], file_path: str) -> Optional[CandidateFinding]:
    """CC003: Potential command injection via dynamic commands in system() or popen()."""
    if call.name in EXEC_FUNCS:
        if call.args_tokens:
            cmd_arg_tokens = call.args_tokens[0]
            # Only flag if the command argument is dynamically constructed (not a constant string literal)
            if is_dynamic_command_argument(cmd_arg_tokens):
                if call.line in hunk_added_lines:
                    cmd_text = call.get_arg_text(0)
                    evidence = f"{call.target}{call.name}({cmd_text})"
                    return CandidateFinding(
                        rule_id="CC003",
                        source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                        severity=FindingSeverity.HIGH,
                        category=FindingCategory.SECURITY_PATTERN,
                        file_path=file_path,
                        start_line=call.line,
                        end_line=call.line,
                        title=f"Potential Command Injection in {call.name}()",
                        explanation=(
                            f"Detected dynamically constructed shell command passed to {call.name}(): '{evidence}'. "
                            "Executing shell commands constructed from variables or non-literal expressions can allow command injection (CWE-78). "
                            "Limitation: Static call analysis detects non-literal arguments; sanitize inputs if dynamic command execution is required."
                        ),
                        suggested_fix=(
                            "Avoid passing commands to the shell. Use execve(), posix_spawn(), or platform APIs with discrete argument arrays "
                            "without shell interpolation."
                        ),
                    )
    return None


def check_cc004_temp_file(call: CppCallNode, hunk_added_lines: Set[int], file_path: str) -> Optional[CandidateFinding]:
    """CC004: Insecure temporary-name APIs susceptible to race conditions (tmpnam, tempnam, mktemp)."""
    if call.name in TEMP_FILE_FUNCS:
        if call.line in hunk_added_lines:
            target_prefix = call.target if call.target else ""
            arg_text = ", ".join(call.get_arg_text(i) for i in range(len(call.args_tokens)))
            evidence = f"{target_prefix}{call.name}({arg_text})"
            return CandidateFinding(
                rule_id="CC004",
                source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                severity=FindingSeverity.MEDIUM,
                category=FindingCategory.SECURITY_PATTERN,
                file_path=file_path,
                start_line=call.line,
                end_line=call.line,
                title=f"Insecure Temporary File Generation ({call.name})",
                explanation=(
                    f"Detected call to insecure temporary filename generator '{evidence}'. "
                    f"The function '{call.name}' creates a file path without opening it atomically, creating a time-of-check to time-of-use "
                    "(TOCTOU) race condition that can allow symlink exploitation or unauthorized file hijacking (CWE-377)."
                ),
                suggested_fix=(
                    "Use mkstemp() (POSIX) to atomically create and open the file, or C++17 std::filesystem::temp_directory_path() "
                    "with secure creation flags (O_CREAT | O_EXCL)."
                ),
            )
    return None


def analyze_cpp_file_diff(file_diff: ParsedFileDiff) -> List[CandidateFinding]:
    """
    Run deterministic C/C++ token-based static analysis across changed hunks.
    Strictly grounds all findings to diff added lines.
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

        try:
            calls = parse_cpp_calls(reconstructed_code, file_diff.file_path)
        except Exception:
            # Tolerant against unexpected syntax or lexer exceptions
            continue

        for call in calls:
            candidate = (
                check_cc001_unbounded_string(call, hunk_added_lines, file_diff.file_path)
                or check_cc002_format_string(call, hunk_added_lines, file_diff.file_path)
                or check_cc003_command_injection(call, hunk_added_lines, file_diff.file_path)
                or check_cc004_temp_file(call, hunk_added_lines, file_diff.file_path)
            )

            if candidate and candidate.start_line is not None:
                key = (candidate.rule_id, candidate.start_line)
                if key not in seen_keys:
                    seen_keys.add(key)
                    findings.append(candidate)

    return findings
