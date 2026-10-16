"""Deterministic static analysis rules for SQL and HiveQL.

Implements Tier 1 deterministic static rules:
- SQL001: UPDATE or DELETE without a WHERE clause (broad modification / data loss risk)
- SQL002: Risky dynamic SQL construction (EXECUTE IMMEDIATE, sp_executesql, EXEC)
- SQL003: Overly broad privilege grant (GRANT ALL PRIVILEGES, WITH GRANT OPTION)
- SQL004: Hardcoded credentials in account management (CREATE/ALTER USER with masked secret)
- SQL005: HiveQL unpartitioned INSERT OVERWRITE or DROP TABLE PURGE (operational data loss risk)

All findings strictly use FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS and
enforce diff line grounding. Zero source code or database queries are executed.
"""
import re
from typing import Dict, List, Optional, Set, Tuple
from pygments.lexers.sql import SqlLexer
from pygments.token import Token

from src.analyzer.base import CandidateFinding
from src.parser.models import ParsedFileDiff, ParsedHunk
from src.schemas.findings import FindingCategory, FindingProvenance, FindingSeverity


class SqlToken:
    """Represents a lexical SQL token with 1-indexed line and column coordinates."""
    __slots__ = ("ttype", "value", "line", "col")

    def __init__(self, ttype, value: str, line: int, col: int):
        self.ttype = ttype
        self.value = value
        self.line = line
        self.col = col

    def __repr__(self) -> str:
        return f"SqlToken({self.ttype}, {self.value!r}, L{self.line}:{self.col})"


class SqlStatement:
    """Represents a segmented SQL statement with start and end line bounds."""
    __slots__ = ("tokens", "start_line", "end_line")

    def __init__(self, tokens: List[SqlToken], start_line: int, end_line: int):
        self.tokens = tokens
        self.start_line = start_line
        self.end_line = end_line

    @property
    def code_tokens(self) -> List[SqlToken]:
        """Tokens excluding whitespace and comments."""
        return [
            t for t in self.tokens
            if t.ttype not in Token.Comment and t.ttype not in Token.Text and t.value.strip()
        ]

    def get_text(self) -> str:
        """Raw source text of the statement."""
        return "".join(t.value for t in self.tokens).strip()


def is_whitespace_or_comment(tok: SqlToken) -> bool:
    """Return True if token is whitespace, comment, or blank text."""
    return tok.ttype in Token.Text or tok.ttype in Token.Comment or not tok.value.strip()


def tokenize_sql(
    code: str, file_path: str = "query.sql", line_map: Optional[Dict[int, int]] = None
) -> List[SqlToken]:
    """Tokenize SQL / HiveQL source code into line-annotated SqlToken list using Pygments.

    If line_map is provided, local lines are translated to exact original file line numbers.
    stripnl=False is enforced so leading/trailing newlines in diff hunks are not stripped.
    """
    lexer = SqlLexer(stripnl=False)
    tokens: List[SqlToken] = []
    local_line = 1
    col = 1

    for ttype, val in lexer.get_tokens(code):
        file_line = line_map.get(local_line, local_line) if line_map else local_line
        tokens.append(SqlToken(ttype=ttype, value=val, line=file_line, col=col))
        if "\n" in val:
            local_line += val.count("\n")
            col = len(val.split("\n")[-1])
        else:
            col += len(val)
    return tokens


def segment_sql_statements(tokens: List[SqlToken]) -> List[SqlStatement]:
    """
    Segment a list of tokens into individual SQL statements bounded by semicolons.
    """
    statements: List[SqlStatement] = []
    curr_tokens: List[SqlToken] = []

    for tok in tokens:
        curr_tokens.append(tok)
        if tok.value == ";" and tok.ttype in (Token.Punctuation, Token.Operator):
            # End of statement
            non_ws = [t for t in curr_tokens if not is_whitespace_or_comment(t)]
            if non_ws:
                s_line = non_ws[0].line
                e_line = non_ws[-1].line
                statements.append(SqlStatement(tokens=curr_tokens, start_line=s_line, end_line=e_line))
            curr_tokens = []

    if curr_tokens:
        non_ws = [t for t in curr_tokens if not is_whitespace_or_comment(t)]
        if non_ws:
            s_line = non_ws[0].line
            e_line = non_ws[-1].line
            statements.append(SqlStatement(tokens=curr_tokens, start_line=s_line, end_line=e_line))

    return statements


def reconstruct_hunk_lines(hunk: ParsedHunk) -> Tuple[str, Dict[int, int]]:
    """
    Reconstruct unified diff hunk content and return (code_text, local_to_file_line_map).
    local_to_file_line_map maps 1-indexed local line in code -> actual file new_line_number.
    """
    code_lines: List[str] = []
    line_map: Dict[int, int] = {}
    local_idx = 1

    for line in hunk.lines:
        l_type = line.type.value if hasattr(line.type, "value") else str(line.type)
        if l_type in ("+", " ") and line.new_line_number is not None:
            code_lines.append(line.content)
            line_map[local_idx] = line.new_line_number
            local_idx += 1

    return "\n".join(code_lines), line_map


# =============================================================================
# Rule Checkers
# =============================================================================

def check_sql001_missing_where(stmt: SqlStatement, hunk_added_lines: Set[int], file_path: str) -> Optional[CandidateFinding]:
    """
    SQL001: Detect UPDATE or DELETE statements without a WHERE clause.
    """
    code_toks = stmt.code_tokens
    if not code_toks:
        return None

    words = [t.value.upper() for t in code_toks]
    first_word = words[0]

    is_update = False
    is_delete = False
    action_line = code_toks[0].line

    if first_word == "UPDATE":
        # Ensure it has SET (valid UPDATE statement)
        if "SET" in words:
            is_update = True
    elif first_word == "DELETE":
        # DELETE FROM or DELETE ...
        is_delete = True
    elif len(words) >= 2 and words[0] in ("WITH",) and ("UPDATE" in words or "DELETE" in words):
        # CTE modifying queries: find where UPDATE or DELETE occurs
        for i, w in enumerate(words):
            if w == "UPDATE" and "SET" in words[i:]:
                is_update = True
                action_line = code_toks[i].line
                break
            elif w == "DELETE":
                is_delete = True
                action_line = code_toks[i].line
                break

    if not (is_update or is_delete):
        return None

    # Check if WHERE keyword is present
    has_where = any(t.value.upper() == "WHERE" and t.ttype in Token.Keyword for t in code_toks)
    if not has_where:
        # Check grounding: statement action line must be in hunk added lines
        if action_line in hunk_added_lines:
            stmt_kind = "UPDATE" if is_update else "DELETE"
            return CandidateFinding(
                rule_id="SQL001",
                source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                severity=FindingSeverity.HIGH,
                category=FindingCategory.SECURITY_PATTERN,
                file_path=file_path,
                start_line=action_line,
                end_line=action_line,
                title=f"Potentially Unbounded {stmt_kind} Statement Missing WHERE Clause",
                explanation=(
                    f"Detected '{stmt_kind}' statement modifying records without a WHERE clause. "
                    f"Executing an unbounded {stmt_kind} modifies or deletes all rows in the target table, "
                    "risking catastrophic data loss (CWE-89, Data Loss Risk). "
                    "Limitations: Complex CTEs, vendor-specific syntax, or statements relying on triggers must "
                    "explicitly specify a WHERE clause (e.g., WHERE 1=1 if an intentional full-table operation is desired)."
                ),
                suggested_fix=f"Add a restrictive WHERE clause to scope rows: {stmt_kind} ... WHERE id = ...",
            )
    return None


def check_sql002_dynamic_sql(stmt: SqlStatement, hunk_added_lines: Set[int], file_path: str) -> Optional[CandidateFinding]:
    """
    SQL002: Detect risky dynamic SQL construction via EXECUTE IMMEDIATE, sp_executesql, or EXEC().
    """
    code_toks = stmt.code_tokens
    if not code_toks:
        return None

    n = len(code_toks)
    for i in range(n):
        tok = code_toks[i]
        val_upper = tok.value.upper()

        # 1. EXECUTE IMMEDIATE <expr>
        if val_upper == "EXECUTE" and i + 1 < n and code_toks[i + 1].value.upper() == "IMMEDIATE":
            call_line = tok.line
            expr_toks = code_toks[i + 2:]
            if _is_dynamic_sql_expression(expr_toks):
                if call_line in hunk_added_lines:
                    return CandidateFinding(
                        rule_id="SQL002",
                        source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                        severity=FindingSeverity.HIGH,
                        category=FindingCategory.SECURITY_PATTERN,
                        file_path=file_path,
                        start_line=call_line,
                        end_line=call_line,
                        title="Potentially Risky Dynamic SQL Execution (EXECUTE IMMEDIATE)",
                        explanation=(
                            "Detected EXECUTE IMMEDIATE with dynamically constructed query expression. "
                            "Assembling SQL commands from variable identifiers or concatenated strings enables "
                            "SQL injection vulnerabilities (CWE-89). "
                            "Static heuristics flag non-constant query expressions; verify data sources or use parameterized queries."
                        ),
                        suggested_fix="Use parameterized queries with bind variables (e.g., USING :param) or fixed literal statements.",
                    )

        # 2. sp_executesql <expr> or EXEC sp_executesql
        elif val_upper in ("SP_EXECUTESQL",) or (val_upper in ("EXEC", "EXECUTE") and i + 1 < n and code_toks[i + 1].value.upper() == "SP_EXECUTESQL"):
            call_line = tok.line
            start_expr = i + 2 if val_upper in ("EXEC", "EXECUTE") else i + 1
            expr_toks = code_toks[start_expr:]
            if _is_dynamic_sql_expression(expr_toks):
                if call_line in hunk_added_lines:
                    return CandidateFinding(
                        rule_id="SQL002",
                        source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                        severity=FindingSeverity.HIGH,
                        category=FindingCategory.SECURITY_PATTERN,
                        file_path=file_path,
                        start_line=call_line,
                        end_line=call_line,
                        title="Potentially Risky Dynamic SQL Execution (sp_executesql)",
                        explanation=(
                            "Detected sp_executesql with dynamically concatenated query parameter. "
                            "Concatenating dynamic values into SQL strings risks SQL injection (CWE-89)."
                        ),
                        suggested_fix="Pass parameters via sp_executesql parameter definition and parameter list, not string concatenation.",
                    )

        # 3. EXEC( <expr> ) or EXECUTE( <expr> )
        elif val_upper in ("EXEC", "EXECUTE") and i + 1 < n and code_toks[i + 1].value == "(":
            call_line = tok.line
            # Gather inside parentheses
            inside: List[SqlToken] = []
            depth = 1
            j = i + 2
            while j < n and depth > 0:
                if code_toks[j].value == "(":
                    depth += 1
                elif code_toks[j].value == ")":
                    depth -= 1
                    if depth == 0:
                        break
                inside.append(code_toks[j])
                j += 1

            if _is_dynamic_sql_expression(inside):
                if call_line in hunk_added_lines:
                    return CandidateFinding(
                        rule_id="SQL002",
                        source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                        severity=FindingSeverity.HIGH,
                        category=FindingCategory.SECURITY_PATTERN,
                        file_path=file_path,
                        start_line=call_line,
                        end_line=call_line,
                        title=f"Potentially Risky Dynamic SQL Execution ({val_upper})",
                        explanation=(
                            f"Detected {val_upper}() with dynamically assembled query expression. "
                            "Executing dynamic SQL from concatenated expressions or variables risks SQL injection (CWE-89)."
                        ),
                        suggested_fix="Use parameterized queries with driver bind parameters instead of dynamic string evaluation.",
                    )

    return None


def _is_dynamic_sql_expression(tokens: List[SqlToken]) -> bool:
    """
    Returns True if an expression contains concatenation (||, +) or variable names
    rather than a single constant string literal.
    """
    non_ws = [t for t in tokens if not is_whitespace_or_comment(t)]
    if not non_ws:
        return False

    # Check for string concatenation operators: || or +
    for idx, t in enumerate(non_ws):
        if t.value in ("||", "+") and t.ttype in (Token.Operator, Token.Punctuation):
            return True
        # Pygments lexes '||' as two consecutive '|' operator tokens
        if t.value == "|" and idx + 1 < len(non_ws) and non_ws[idx + 1].value == "|":
            return True

    # Check for variables or identifiers (e.g. @sql, @cmd, v_query, sql_stmt, table_var)
    for t in non_ws:
        if t.value.upper() == "USING":
            break  # End of query expression in EXECUTE IMMEDIATE ... USING :param
        if t.ttype in (Token.Name, Token.Name.Variable) or t.value.startswith("@"):
            return True

    # If it consists solely of string literals, it is static
    if all(t.ttype in Token.Literal.String for t in non_ws):
        return False

    return False


def check_sql003_broad_privileges(stmt: SqlStatement, hunk_added_lines: Set[int], file_path: str) -> Optional[CandidateFinding]:
    """
    SQL003: Detect overly broad privilege grants (GRANT ALL PRIVILEGES, WITH GRANT OPTION).
    """
    code_toks = stmt.code_tokens
    if not code_toks:
        return None

    words = [t.value.upper() for t in code_toks]
    if words[0] != "GRANT":
        return None

    grant_line = code_toks[0].line
    has_all_privileges = False
    has_grant_option = False

    for i in range(len(words)):
        if words[i] == "ALL":
            # GRANT ALL or GRANT ALL PRIVILEGES
            has_all_privileges = True
        elif words[i] == "WITH" and i + 2 < len(words) and words[i + 1] == "GRANT" and words[i + 2] == "OPTION":
            has_grant_option = True
        elif words[i] == "WITH" and i + 2 < len(words) and words[i + 1] == "ADMIN" and words[i + 2] == "OPTION":
            has_grant_option = True

    if has_all_privileges or has_grant_option:
        if grant_line in hunk_added_lines:
            detail = []
            if has_all_privileges:
                detail.append("ALL PRIVILEGES")
            if has_grant_option:
                detail.append("WITH GRANT OPTION")
            reasons = " and ".join(detail)

            return CandidateFinding(
                rule_id="SQL003",
                source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                severity=FindingSeverity.HIGH if has_all_privileges else FindingSeverity.MEDIUM,
                category=FindingCategory.SECURITY_PATTERN,
                file_path=file_path,
                start_line=grant_line,
                end_line=grant_line,
                title=f"Overly Broad Privilege Grant ({reasons})",
                explanation=(
                    f"Detected SQL grant with {reasons}. "
                    "Granting unrestricted privileges or delegate permissions violates the Principle of Least Privilege "
                    "(CWE-250, CWE-269), allowing compromised accounts to perform unauthorized schema changes or data exfiltration. "
                    "Note: This is a static security warning indicating broad administrative access; verify caller role necessity."
                ),
                suggested_fix="Grant only the specific required privileges (e.g., GRANT SELECT, INSERT ON <table> TO <role>).",
            )

    return None


def check_sql004_hardcoded_credentials(stmt: SqlStatement, hunk_added_lines: Set[int], file_path: str) -> Optional[CandidateFinding]:
    """
    SQL004: Detect hardcoded credentials in account management statements.
    Ensures that detected secret literals are ALWAYS masked as '***' in evidence and explanations.
    """
    code_toks = stmt.code_tokens
    if not code_toks:
        return None

    words = [t.value.upper() for t in code_toks]
    # Restrict to account management statements: CREATE USER, ALTER USER, CREATE ROLE, ALTER ROLE
    if len(words) < 3:
        return None

    first_two = f"{words[0]} {words[1]}"
    if first_two not in ("CREATE USER", "ALTER USER", "CREATE ROLE", "ALTER ROLE"):
        return None

    mgmt_line = code_toks[0].line
    found_cred = False

    # Look for IDENTIFIED BY '<literal>' or WITH PASSWORD '<literal>' or PASSWORD '<literal>'
    for i in range(len(words) - 1):
        if words[i] == "IDENTIFIED" and words[i + 1] == "BY":
            # Next non-ws token must be a string literal
            if i + 2 < len(code_toks) and code_toks[i + 2].ttype in Token.Literal.String:
                found_cred = True
                mgmt_line = code_toks[i + 2].line
                break
        elif words[i] == "PASSWORD" or (words[i] == "WITH" and words[i + 1] == "PASSWORD"):
            target_idx = i + 2 if words[i] == "WITH" else i + 1
            if target_idx < len(code_toks) and code_toks[target_idx].ttype in Token.Literal.String:
                found_cred = True
                mgmt_line = code_toks[target_idx].line
                break

    if found_cred:
        if mgmt_line in hunk_added_lines:
            return CandidateFinding(
                rule_id="SQL004",
                source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                severity=FindingSeverity.HIGH,
                category=FindingCategory.SECURITY_PATTERN,
                file_path=file_path,
                start_line=mgmt_line,
                end_line=mgmt_line,
                title="Hardcoded Database Credential in Account Management Statement",
                explanation=(
                    f"Detected plaintext credential literal in '{first_two} ... IDENTIFIED BY '***''. "
                    "Storing plaintext database passwords in version-controlled scripts risks credential exposure (CWE-798). "
                    "Plaintext credentials can be leaked through repository history, logs, or unauthorized access."
                ),
                suggested_fix="Provision credentials via external secret management, IAM authentication, or environment variables.",
            )

    return None


def check_sql005_hive_overwrite(stmt: SqlStatement, hunk_added_lines: Set[int], file_path: str) -> Optional[CandidateFinding]:
    """
    SQL005: Detect HiveQL unpartitioned INSERT OVERWRITE or DROP TABLE PURGE.
    """
    code_toks = stmt.code_tokens
    if not code_toks:
        return None

    words = [t.value.upper() for t in code_toks]
    stmt_line = code_toks[0].line

    # 1. INSERT OVERWRITE TABLE <tbl> (without PARTITION)
    if len(words) >= 3 and words[0] == "INSERT" and words[1] == "OVERWRITE":
        has_partition = "PARTITION" in words
        if not has_partition:
            if stmt_line in hunk_added_lines:
                tbl_name = code_toks[3].value if len(code_toks) > 3 and words[2] == "TABLE" else "table"
                return CandidateFinding(
                    rule_id="SQL005",
                    source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    severity=FindingSeverity.LOW,
                    category=FindingCategory.CODE_QUALITY,
                    file_path=file_path,
                    start_line=stmt_line,
                    end_line=stmt_line,
                    title="HiveQL Unpartitioned Table Overwrite Risk",
                    explanation=(
                        f"Detected 'INSERT OVERWRITE TABLE {tbl_name}' without a PARTITION clause. "
                        "An unpartitioned overwrite unconditionally truncates and replaces the entire target dataset, "
                        "introducing data loss risk if executed against production tables."
                    ),
                    suggested_fix="Specify a partition using 'PARTITION (key = ...)' or use 'INSERT INTO' for append operations.",
                )

    # 2. DROP TABLE <tbl> PURGE (bypasses Trash)
    if len(words) >= 3 and words[0] == "DROP" and words[1] == "TABLE" and "PURGE" in words:
        if stmt_line in hunk_added_lines:
            return CandidateFinding(
                rule_id="SQL005",
                source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                severity=FindingSeverity.LOW,
                category=FindingCategory.CODE_QUALITY,
                file_path=file_path,
                start_line=stmt_line,
                end_line=stmt_line,
                title="HiveQL DROP TABLE with PURGE (Bypasses Trash)",
                explanation=(
                    "Detected 'DROP TABLE ... PURGE'. Specifying PURGE completely bypasses the Hive Trash folder, "
                    "permanently destroying table metadata and underlying HDFS/Cloud storage data without recovery options."
                ),
                suggested_fix="Omit the PURGE option to allow standard Hive trash retention, or verify permanent deletion is intended.",
            )

    return None


# =============================================================================
# Diff-Level Orchestration
# =============================================================================

def analyze_sql_file_diff(file_diff: ParsedFileDiff) -> List[CandidateFinding]:
    """
    Run SQL and HiveQL deterministic static rules over a parsed file diff.
    Operates strictly intra-hunk and preserves exact diff line numbers.
    """
    findings: List[CandidateFinding] = []

    if file_diff.is_binary or not file_diff.hunks:
        return findings

    for hunk in file_diff.hunks:
        hunk_added_lines = set(hunk.added_lines)
        if not hunk_added_lines:
            continue

        reconstructed_code, line_map = reconstruct_hunk_lines(hunk)
        if not reconstructed_code.strip():
            continue

        try:
            tokens = tokenize_sql(reconstructed_code, file_path=file_diff.file_path, line_map=line_map)
            statements = segment_sql_statements(tokens)
        except Exception:
            # Gracefully tolerate syntax or tokenization errors without crashing
            continue

        for stmt in statements:
            # Run all 5 rules
            f1 = check_sql001_missing_where(stmt, hunk_added_lines, file_diff.file_path)
            if f1:
                findings.append(f1)

            f2 = check_sql002_dynamic_sql(stmt, hunk_added_lines, file_diff.file_path)
            if f2:
                findings.append(f2)

            f3 = check_sql003_broad_privileges(stmt, hunk_added_lines, file_diff.file_path)
            if f3:
                findings.append(f3)

            f4 = check_sql004_hardcoded_credentials(stmt, hunk_added_lines, file_diff.file_path)
            if f4:
                findings.append(f4)

            f5 = check_sql005_hive_overwrite(stmt, hunk_added_lines, file_diff.file_path)
            if f5:
                findings.append(f5)

    return findings
