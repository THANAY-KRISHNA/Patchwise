"""Comprehensive unit and edge-case tests for C/C++ static analysis rules (CC001-CC004)."""
import pytest
from src.analyzer.plugins.cpp.rules import analyze_cpp_file_diff
from src.parser.models import DiffLine, FileChangeStatus, LineType, ParsedFileDiff, ParsedHunk
from src.schemas.findings import FindingCategory, FindingProvenance, FindingSeverity


def _make_cpp_diff(lines_tuples, file_path="src/service.cpp") -> ParsedFileDiff:
    """Helper to build a ParsedFileDiff from (type_char, content, old_line, new_line)."""
    diff_lines = []
    added = []
    deleted = []
    context = []

    for l_type, content, old_no, new_no in lines_tuples:
        if l_type == "+":
            t = LineType.ADDED
            if new_no is not None:
                added.append(new_no)
        elif l_type == "-":
            t = LineType.DELETED
            if old_no is not None:
                deleted.append(old_no)
        else:
            t = LineType.CONTEXT
            if new_no is not None:
                context.append(new_no)

        diff_lines.append(DiffLine(type=t, content=content, old_line_number=old_no, new_line_number=new_no))

    hunk = ParsedHunk(
        old_start=1,
        old_length=len(diff_lines),
        new_start=1,
        new_length=len(diff_lines),
        header="@@ -1,5 +1,5 @@",
        lines=diff_lines,
        added_lines=added,
        deleted_lines=deleted,
        context_lines=context,
    )

    return ParsedFileDiff(
        file_path=file_path,
        status=FileChangeStatus.MODIFIED,
        is_binary=False,
        hunks=[hunk],
        added_lines=added,
        deleted_lines=deleted,
    )


# =============================================================================
# CC001: Unbounded String Operations Tests
# =============================================================================

def test_cc001_gets_positive():
    diff = _make_cpp_diff([
        (" ", "void read_input() {", 1, 1),
        (" ", "    char buf[256];", 2, 2),
        ("+", "    gets(buf);", None, 3),
        (" ", "}", 3, 4),
    ], file_path="src/input.c")
    findings = analyze_cpp_file_diff(diff)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "CC001"
    assert f.start_line == 3
    assert f.source == FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS
    assert f.severity == FindingSeverity.HIGH


def test_cc001_strcpy_and_strcat_positive():
    diff = _make_cpp_diff([
        (" ", "void copy_name(const char* src) {", 1, 1),
        (" ", "    char dest[64];", 2, 2),
        ("+", "    strcpy(dest, src);", None, 3),
        ("+", '    strcat(dest, "_suffix");', None, 4),
        (" ", "}", 3, 5),
    ], file_path="src/names.c")
    findings = analyze_cpp_file_diff(diff)
    assert len(findings) == 2
    rule_lines = {f.start_line: f.rule_id for f in findings}
    assert rule_lines == {3: "CC001", 4: "CC001"}


def test_cc001_sprintf_positive():
    diff = _make_cpp_diff([
        (" ", "void format_str(int id) {", 1, 1),
        (" ", "    char buffer[32];", 2, 2),
        ("+", '    sprintf(buffer, "item_%d", id);', None, 3),
        (" ", "}", 3, 4),
    ], file_path="src/fmt.c")
    findings = analyze_cpp_file_diff(diff)
    assert len(findings) == 1
    assert findings[0].rule_id == "CC001"
    assert findings[0].start_line == 3


def test_cc001_safe_bounded_string_negative():
    diff = _make_cpp_diff([
        (" ", "void safe_copy(const char* src) {", 1, 1),
        (" ", "    char buf[128];", 2, 2),
        ("+", "    fgets(buf, sizeof(buf), stdin);", None, 3),
        ("+", "    strncpy(buf, src, sizeof(buf) - 1);", None, 4),
        ("+", '    snprintf(buf, sizeof(buf), "prefix_%s", src);', None, 5),
        (" ", "}", 3, 6),
    ], file_path="src/safe_str.c")
    findings = analyze_cpp_file_diff(diff)
    assert len(findings) == 0


# =============================================================================
# CC002: Format String Misuse Tests
# =============================================================================

def test_cc002_printf_variable_format_positive():
    diff = _make_cpp_diff([
        (" ", "void log_message(const char* user_msg) {", 1, 1),
        ("+", "    printf(user_msg);", None, 2),
        (" ", "}", 2, 3),
    ], file_path="src/logger.c")
    findings = analyze_cpp_file_diff(diff)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "CC002"
    assert f.start_line == 2
    assert f.source == FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS
    assert f.severity == FindingSeverity.HIGH


def test_cc002_fprintf_and_syslog_variable_format_positive():
    diff = _make_cpp_diff([
        (" ", "void report(FILE* f, const char* err) {", 1, 1),
        ("+", "    fprintf(f, err);", None, 2),
        ("+", "    syslog(LOG_ERR, err);", None, 3),
        (" ", "}", 2, 4),
    ], file_path="src/report.c")
    findings = analyze_cpp_file_diff(diff)
    assert len(findings) == 2
    for f in findings:
        assert f.rule_id == "CC002"


def test_cc002_syslog_individual_positive_and_negative():
    # Positives: syslog(LOG_ERR, user_input)
    diff_pos = _make_cpp_diff([
        (" ", "void log_syslog(const char* user_input) {", 1, 1),
        ("+", "    syslog(LOG_ERR, user_input);", None, 2),
        (" ", "}", 2, 3),
    ], file_path="src/syslog_test.c")
    findings_pos = analyze_cpp_file_diff(diff_pos)
    assert len(findings_pos) == 1
    assert findings_pos[0].rule_id == "CC002"
    assert findings_pos[0].start_line == 2

    # Negative: syslog(LOG_ERR, "%s", user_input)
    diff_neg = _make_cpp_diff([
        (" ", "void log_syslog(const char* user_input) {", 1, 1),
        ("+", '    syslog(LOG_ERR, "%s", user_input);', None, 2),
        (" ", "}", 2, 3),
    ], file_path="src/syslog_test.c")
    findings_neg = analyze_cpp_file_diff(diff_neg)
    assert len(findings_neg) == 0


def test_cc002_fprintf_individual_positive_and_negative():
    # Positive: fprintf(stderr, user_input)
    diff_pos = _make_cpp_diff([
        (" ", "void log_stderr(const char* user_input) {", 1, 1),
        ("+", "    fprintf(stderr, user_input);", None, 2),
        (" ", "}", 2, 3),
    ], file_path="src/err_test.c")
    findings_pos = analyze_cpp_file_diff(diff_pos)
    assert len(findings_pos) == 1
    assert findings_pos[0].rule_id == "CC002"
    assert findings_pos[0].start_line == 2

    # Negative: fprintf(stderr, "%s", user_input)
    diff_neg = _make_cpp_diff([
        (" ", "void log_stderr(const char* user_input) {", 1, 1),
        ("+", '    fprintf(stderr, "%s", user_input);', None, 2),
        (" ", "}", 2, 3),
    ], file_path="src/err_test.c")
    findings_neg = analyze_cpp_file_diff(diff_neg)
    assert len(findings_neg) == 0


def test_cc002_snprintf_and_posix_variants_safe_and_unsafe():
    # Unsafe: snprintf at idx 2, dprintf at idx 1, asprintf at idx 1
    diff_unsafe = _make_cpp_diff([
        (" ", "void test_variants(char* buf, size_t sz, int fd, char** out, const char* user_input) {", 1, 1),
        ("+", "    snprintf(buf, sz, user_input);", None, 2),
        ("+", "    dprintf(fd, user_input);", None, 3),
        ("+", "    asprintf(out, user_input);", None, 4),
        (" ", "}", 2, 5),
    ], file_path="src/variants.c")
    findings_unsafe = analyze_cpp_file_diff(diff_unsafe)
    assert len(findings_unsafe) == 3
    assert {f.start_line for f in findings_unsafe} == {2, 3, 4}
    for f in findings_unsafe:
        assert f.rule_id == "CC002"

    # Safe: with format specifiers
    diff_safe = _make_cpp_diff([
        (" ", "void test_variants(char* buf, size_t sz, int fd, char** out, const char* user_input) {", 1, 1),
        ("+", '    snprintf(buf, sz, "%s", user_input);', None, 2),
        ("+", '    dprintf(fd, "%s", user_input);', None, 3),
        ("+", '    asprintf(out, "%s", user_input);', None, 4),
        (" ", "}", 2, 5),
    ], file_path="src/variants.c")
    findings_safe = analyze_cpp_file_diff(diff_safe)
    assert len(findings_safe) == 0


def test_cc002_printf_safe_format_specifier_negative():
    """Passing user_msg with an explicit static '%s' format specifier must NOT trigger CC002."""
    diff = _make_cpp_diff([
        (" ", "void log_message(const char* user_msg) {", 1, 1),
        ("+", '    printf("%s", user_msg);', None, 2),
        ("+", '    fprintf(stderr, "Error: %s\\n", user_msg);', None, 3),
        (" ", "}", 2, 4),
    ], file_path="src/logger.c")
    findings = analyze_cpp_file_diff(diff)
    assert len(findings) == 0


def test_cc002_printf_fixed_literal_negative():
    diff = _make_cpp_diff([
        (" ", "void greet() {", 1, 1),
        ("+", '    printf("Hello, world!\\n");', None, 2),
        (" ", "}", 2, 3),
    ], file_path="src/greet.c")
    findings = analyze_cpp_file_diff(diff)
    assert len(findings) == 0


# =============================================================================
# CC003: Command Injection Tests
# =============================================================================

def test_cc003_system_dynamic_command_positive():
    diff = _make_cpp_diff([
        (" ", "void execute_script(const char* script) {", 1, 1),
        ("+", "    system(script);", None, 2),
        (" ", "}", 2, 3),
    ], file_path="src/runner.cpp")
    findings = analyze_cpp_file_diff(diff)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "CC003"
    assert f.start_line == 2
    assert f.source == FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS
    assert f.severity == FindingSeverity.HIGH


def test_cc003_popen_dynamic_concat_positive():
    diff = _make_cpp_diff([
        (" ", "void ping_host(const std::string& host) {", 1, 1),
        ("+", '    FILE* p = popen(("ping -c 1 " + host).c_str(), "r");', None, 2),
        (" ", "}", 2, 3),
    ], file_path="src/net.cpp")
    findings = analyze_cpp_file_diff(diff)
    assert len(findings) == 1
    assert findings[0].rule_id == "CC003"
    assert findings[0].start_line == 2


def test_cc003_system_static_literal_negative():
    """Fixed constant string literals passed to system() must NOT trigger CC003."""
    diff = _make_cpp_diff([
        (" ", "void check_status() {", 1, 1),
        ("+", '    system("uptime");', None, 2),
        ("+", '    FILE* p = popen("ls -la", "r");', None, 3),
        (" ", "}", 2, 4),
    ], file_path="src/status.cpp")
    findings = analyze_cpp_file_diff(diff)
    assert len(findings) == 0


# =============================================================================
# CC004: Insecure Temporary File Name Tests
# =============================================================================

def test_cc004_tmpnam_and_mktemp_positive():
    diff = _make_cpp_diff([
        (" ", "void create_temp() {", 1, 1),
        (" ", "    char name[L_tmpnam];", 2, 2),
        ("+", "    tmpnam(name);", None, 3),
        ("+", '    char template_path[] = "/tmp/app_XXXXXX";', None, 4),
        ("+", "    mktemp(template_path);", None, 5),
        (" ", "}", 3, 6),
    ], file_path="src/temp.c")
    findings = analyze_cpp_file_diff(diff)
    assert len(findings) == 2
    rule_lines = {f.start_line: f.rule_id for f in findings}
    assert rule_lines == {3: "CC004", 5: "CC004"}


def test_cc004_safe_mkstemp_negative():
    diff = _make_cpp_diff([
        (" ", "void secure_temp() {", 1, 1),
        ("+", '    char template_path[] = "/tmp/secure_XXXXXX";', None, 2),
        ("+", "    int fd = mkstemp(template_path);", None, 3),
        (" ", "}", 2, 4),
    ], file_path="src/safe_temp.c")
    findings = analyze_cpp_file_diff(diff)
    assert len(findings) == 0


# =============================================================================
# Multi-Hunk Line Mapping & Robustness Tests
# =============================================================================

def test_cpp_multi_hunk_exact_line_mapping():
    """Verify exact line numbers are preserved across multiple diff hunks."""
    hunk1_lines = [
        DiffLine(type=LineType.CONTEXT, content="void func1() {", old_line_number=1, new_line_number=1),
        DiffLine(type=LineType.ADDED, content="    char b[10]; gets(b);", old_line_number=None, new_line_number=2),
    ]
    hunk1 = ParsedHunk(
        old_start=1, old_length=1, new_start=1, new_length=2,
        header="@@ -1,1 +1,2 @@",
        lines=hunk1_lines, added_lines=[2], deleted_lines=[], context_lines=[1],
    )

    hunk2_lines = [
        DiffLine(type=LineType.CONTEXT, content="void func2(char* s) {", old_line_number=25, new_line_number=26),
        DiffLine(type=LineType.ADDED, content="    printf(s);", old_line_number=None, new_line_number=27),
    ]
    hunk2 = ParsedHunk(
        old_start=25, old_length=1, new_start=26, new_length=2,
        header="@@ -25,1 +26,2 @@",
        lines=hunk2_lines, added_lines=[27], deleted_lines=[], context_lines=[26],
    )

    diff = ParsedFileDiff(
        file_path="src/multi.cpp",
        status=FileChangeStatus.MODIFIED,
        is_binary=False,
        hunks=[hunk1, hunk2],
        added_lines=[2, 27],
        deleted_lines=[],
    )

    findings = analyze_cpp_file_diff(diff)
    assert len(findings) == 2
    rule_lines = {f.rule_id: f.start_line for f in findings}
    assert rule_lines == {"CC001": 2, "CC002": 27}


def test_empty_cpp_diff_handling():
    diff = ParsedFileDiff(
        file_path="src/empty.cpp",
        status=FileChangeStatus.MODIFIED,
        is_binary=False,
        hunks=[],
        added_lines=[],
        deleted_lines=[],
    )
    assert analyze_cpp_file_diff(diff) == []


def test_binary_cpp_diff_handling():
    diff = ParsedFileDiff(
        file_path="bin/app.o",
        status=FileChangeStatus.MODIFIED,
        is_binary=True,
        hunks=[],
        added_lines=[],
        deleted_lines=[],
    )
    assert analyze_cpp_file_diff(diff) == []


def test_cpp_syntax_error_tolerance():
    """Unparseable or broken syntax fragments must not crash the analyzer."""
    diff = _make_cpp_diff([
        ("+", "void broken() { @@@ ??? <<<< ;;; :::", None, 1),
        ("+", "    int x = >>> *** ;;;", None, 2),
    ], file_path="src/broken.cpp")
    findings = analyze_cpp_file_diff(diff)
    assert findings == []
