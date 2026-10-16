"""Curated and Versioned Benchmark Dataset Fixtures for C and C++ (v1.0.0).

Contains 20 labelled code diffs with ground-truth expected findings for deterministic rules
CC001–CC004 across C and C++ files (.c, .h, .cpp, .hpp, .cc), clean negative examples (true negatives),
edge cases, and malformed inputs.
"""
from typing import List
from ..schemas.findings import FindingProvenance
from .models import BenchmarkCase, BenchmarkDataset, ExpectedFinding

DATASET_VERSION_CPP = "v1.0.0"
DATASET_NAME_CPP = "patchwise-cpp-deterministic-benchmark"


def get_cpp_benchmark_dataset() -> BenchmarkDataset:
    """Builds and returns the frozen C and C++ benchmark dataset (v1.0.0)."""
    cases: List[BenchmarkCase] = [
        # =====================================================================
        # Category 1: Deterministic Rule Positives (CC001 - CC004)
        # =====================================================================
        BenchmarkCase(
            id="cc001_gets_positive",
            name="CC001: Unbounded buffer read via gets()",
            description="Reading unbounded input from stdin into fixed buffer using gets() causes stack buffer overflow.",
            diff_patch="""@@ -5,1 +5,4 @@ void read_credentials() {
 void read_credentials() {
+    char password[64];
+    gets(password);
 }
""",
            target_file="src/auth.c",
            all_pr_files=["src/auth.c"],
            language="cpp",
            expected_findings=[
                ExpectedFinding(
                    rule_id="CC001",
                    file_path="src/auth.c",
                    start_line=7,
                    end_line=7,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Unbounded gets() invocation",
                )
            ],
            tags=["cc001", "buffer_overflow", "positive"],
        ),
        BenchmarkCase(
            id="cc001_strcpy_positive",
            name="CC001: Unbounded string copy via strcpy()",
            description="Copying unbounded source string into destination buffer using strcpy().",
            diff_patch="""@@ -10,1 +10,4 @@ void copy_username(const char* name) {
 void copy_username(const char* name) {
+    char dest[32];
+    strcpy(dest, name);
 }
""",
            target_file="src/user.c",
            all_pr_files=["src/user.c"],
            language="cpp",
            expected_findings=[
                ExpectedFinding(
                    rule_id="CC001",
                    file_path="src/user.c",
                    start_line=12,
                    end_line=12,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Unbounded strcpy() call",
                )
            ],
            tags=["cc001", "buffer_overflow", "positive"],
        ),
        BenchmarkCase(
            id="cc001_sprintf_positive",
            name="CC001: Unbounded string formatting via sprintf()",
            description="Formatting dynamic arguments into buffer using sprintf() without length boundary.",
            diff_patch="""@@ -15,1 +15,4 @@ void format_log(int code, const char* msg) {
 void format_log(int code, const char* msg) {
+    char log_entry[128];
+    sprintf(log_entry, "Error [%d]: %s", code, msg);
 }
""",
            target_file="src/logger.cpp",
            all_pr_files=["src/logger.cpp"],
            language="cpp",
            expected_findings=[
                ExpectedFinding(
                    rule_id="CC001",
                    file_path="src/logger.cpp",
                    start_line=17,
                    end_line=17,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Unbounded sprintf() call",
                )
            ],
            tags=["cc001", "buffer_overflow", "positive"],
        ),
        BenchmarkCase(
            id="cc002_printf_variable_format_positive",
            name="CC002: Format string vulnerability via printf(user_input)",
            description="Passing variable directly as format argument to printf() without string literal specifier.",
            diff_patch="""@@ -20,1 +20,4 @@ void output_message(const char* user_input) {
 void output_message(const char* user_input) {
+    printf(user_input);
 }
""",
            target_file="src/display.c",
            all_pr_files=["src/display.c"],
            language="cpp",
            expected_findings=[
                ExpectedFinding(
                    rule_id="CC002",
                    file_path="src/display.c",
                    start_line=21,
                    end_line=21,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Format string misuse in printf()",
                )
            ],
            tags=["cc002", "format_string", "positive"],
        ),
        BenchmarkCase(
            id="cc002_fprintf_variable_format_positive",
            name="CC002: Format string vulnerability via fprintf(stderr, error_msg)",
            description="Passing non-literal error message as format specifier to fprintf().",
            diff_patch="""@@ -25,1 +25,4 @@ void log_error(FILE* fp, const char* error_msg) {
 void log_error(FILE* fp, const char* error_msg) {
+    fprintf(fp, error_msg);
 }
""",
            target_file="src/error.c",
            all_pr_files=["src/error.c"],
            language="cpp",
            expected_findings=[
                ExpectedFinding(
                    rule_id="CC002",
                    file_path="src/error.c",
                    start_line=26,
                    end_line=26,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Format string misuse in fprintf()",
                )
            ],
            tags=["cc002", "format_string", "positive"],
        ),
        BenchmarkCase(
            id="cc002_snprintf_variable_format_positive",
            name="CC002: Format string vulnerability via snprintf() non-literal format",
            description="Passing variable format string into snprintf() format argument position.",
            diff_patch="""@@ -30,1 +30,4 @@ void custom_format(char* buf, size_t size, const char* fmt) {
 void custom_format(char* buf, size_t size, const char* fmt) {
+    snprintf(buf, size, fmt);
 }
""",
            target_file="src/formatter.cpp",
            all_pr_files=["src/formatter.cpp"],
            language="cpp",
            expected_findings=[
                ExpectedFinding(
                    rule_id="CC002",
                    file_path="src/formatter.cpp",
                    start_line=31,
                    end_line=31,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Format string misuse in snprintf()",
                )
            ],
            tags=["cc002", "format_string", "positive"],
        ),
        BenchmarkCase(
            id="cc003_system_variable_command_positive",
            name="CC003: Command injection via system() dynamic command",
            description="Passing dynamically constructed command string to system().",
            diff_patch="""@@ -35,1 +35,4 @@ void run_custom_task(const char* task_cmd) {
 void run_custom_task(const char* task_cmd) {
+    system(task_cmd);
 }
""",
            target_file="src/task.cpp",
            all_pr_files=["src/task.cpp"],
            language="cpp",
            expected_findings=[
                ExpectedFinding(
                    rule_id="CC003",
                    file_path="src/task.cpp",
                    start_line=36,
                    end_line=36,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Command injection in system()",
                )
            ],
            tags=["cc003", "command_injection", "positive"],
        ),
        BenchmarkCase(
            id="cc003_popen_concat_command_positive",
            name="CC003: Command injection via popen() concatenated string",
            description="Passing dynamically concatenated string to popen().",
            diff_patch="""@@ -40,1 +40,4 @@ void query_dns(const std::string& domain) {
 void query_dns(const std::string& domain) {
+    FILE* p = popen(("nslookup " + domain).c_str(), "r");
 }
""",
            target_file="src/dns.cpp",
            all_pr_files=["src/dns.cpp"],
            language="cpp",
            expected_findings=[
                ExpectedFinding(
                    rule_id="CC003",
                    file_path="src/dns.cpp",
                    start_line=41,
                    end_line=41,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Command injection in popen()",
                )
            ],
            tags=["cc003", "command_injection", "positive"],
        ),
        BenchmarkCase(
            id="cc004_tmpnam_positive",
            name="CC004: Insecure temporary filename generation via tmpnam()",
            description="Generating temporary filename using tmpnam() introduces TOCTOU race condition.",
            diff_patch="""@@ -45,1 +45,5 @@ void create_cache_file() {
 void create_cache_file() {
+    char temp_name[L_tmpnam];
+    tmpnam(temp_name);
 }
""",
            target_file="src/cache.c",
            all_pr_files=["src/cache.c"],
            language="cpp",
            expected_findings=[
                ExpectedFinding(
                    rule_id="CC004",
                    file_path="src/cache.c",
                    start_line=47,
                    end_line=47,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Insecure tmpnam() temporary file generation",
                )
            ],
            tags=["cc004", "temp_file", "positive"],
        ),
        BenchmarkCase(
            id="cc004_mktemp_positive",
            name="CC004: Insecure temporary filename generation via mktemp()",
            description="Generating temporary filename with mktemp() introduces TOCTOU symlink attack vector.",
            diff_patch="""@@ -50,1 +50,5 @@ void make_scratch_pad() {
 void make_scratch_pad() {
+    char template_path[] = "/tmp/scratch_XXXXXX";
+    mktemp(template_path);
 }
""",
            target_file="src/scratch.c",
            all_pr_files=["src/scratch.c"],
            language="cpp",
            expected_findings=[
                ExpectedFinding(
                    rule_id="CC004",
                    file_path="src/scratch.c",
                    start_line=52,
                    end_line=52,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Insecure mktemp() temporary file generation",
                )
            ],
            tags=["cc004", "temp_file", "positive"],
        ),

        # =====================================================================
        # Category 2: Clean Negative Examples (True Negatives)
        # =====================================================================
        BenchmarkCase(
            id="clean_cpp_bounded_string_negative",
            name="Clean: Safe bounded string copying using strncpy and fgets",
            description="Copying strings with explicit buffer size bounds using fgets and strncpy.",
            diff_patch="""@@ -5,1 +5,5 @@ void safe_reader() {
 void safe_reader() {
+    char buf[128];
+    fgets(buf, sizeof(buf), stdin);
+    strncpy(buf, "constant", sizeof(buf) - 1);
 }
""",
            target_file="src/safe_io.c",
            all_pr_files=["src/safe_io.c"],
            language="cpp",
            expected_findings=[],
            is_negative_case=True,
            tags=["clean", "true_negative", "buffer_overflow"],
        ),
        BenchmarkCase(
            id="clean_cpp_printf_specifier_negative",
            name="Clean: Safe printf with static format specifier placeholder",
            description="Passing variable user string with fixed format string literal '%s'.",
            diff_patch="""@@ -10,1 +10,4 @@ void safe_print(const char* user_msg) {
 void safe_print(const char* user_msg) {
+    printf("%s", user_msg);
 }
""",
            target_file="src/safe_display.c",
            all_pr_files=["src/safe_display.c"],
            language="cpp",
            expected_findings=[],
            is_negative_case=True,
            tags=["clean", "true_negative", "format_string"],
        ),
        BenchmarkCase(
            id="clean_cpp_printf_fixed_literal_negative",
            name="Clean: Safe fixed string literal in printf()",
            description="Calling printf() with constant string literal and no variable format injection.",
            diff_patch="""@@ -15,1 +15,4 @@ void print_greeting() {
 void print_greeting() {
+    printf("Application started successfully.\\n");
 }
""",
            target_file="src/init.c",
            all_pr_files=["src/init.c"],
            language="cpp",
            expected_findings=[],
            is_negative_case=True,
            tags=["clean", "true_negative", "format_string"],
        ),
        BenchmarkCase(
            id="clean_cpp_system_constant_command_negative",
            name="Clean: Safe constant command literal in system()",
            description="Executing fixed constant shell command literal without user interpolation.",
            diff_patch="""@@ -20,1 +20,4 @@ void check_health() {
 void check_health() {
+    system("uptime");
 }
""",
            target_file="src/health.cpp",
            all_pr_files=["src/health.cpp"],
            language="cpp",
            expected_findings=[],
            is_negative_case=True,
            tags=["clean", "true_negative", "command_injection"],
        ),
        BenchmarkCase(
            id="clean_cpp_mkstemp_atomic_temp_negative",
            name="Clean: Safe atomic temporary file creation via mkstemp()",
            description="Creating temporary file atomically using mkstemp() avoiding TOCTOU races.",
            diff_patch="""@@ -25,1 +25,5 @@ void safe_temp() {
 void safe_temp() {
+    char tmpl[] = "/tmp/safe_XXXXXX";
+    int fd = mkstemp(tmpl);
 }
""",
            target_file="src/safe_file.c",
            all_pr_files=["src/safe_file.c"],
            language="cpp",
            expected_findings=[],
            is_negative_case=True,
            tags=["clean", "true_negative", "temp_file"],
        ),

        # =====================================================================
        # Category 3: Edge Cases & Robustness
        # =====================================================================
        BenchmarkCase(
            id="edge_cpp_empty_diff",
            name="Edge: Empty diff patch",
            description="Zero hunks and empty patch string must produce zero findings gracefully.",
            diff_patch="",
            target_file="src/unchanged.cpp",
            all_pr_files=["src/unchanged.cpp"],
            language="cpp",
            expected_findings=[],
            is_negative_case=True,
            tags=["edge_case", "empty_diff"],
        ),
        BenchmarkCase(
            id="edge_cpp_binary_object_file_diff",
            name="Edge: Binary compiled .o object file diff",
            description="Binary compiled object file patch must be skipped without errors.",
            diff_patch="GIT binary patch\nliteral 0\nHc$@<O00001\n",
            target_file="build/main.o",
            all_pr_files=["build/main.o"],
            language="cpp",
            expected_findings=[],
            is_negative_case=True,
            tags=["edge_case", "binary_diff"],
        ),
        BenchmarkCase(
            id="edge_cpp_non_cpp_markdown",
            name="Edge: Non-C/C++ markdown documentation diff",
            description="Documentation files (.md) in C/C++ repositories must not trigger C/C++ rules.",
            diff_patch="""@@ -1,3 +1,5 @@
 # Build Instructions
+char buf[10]; gets(buf);
+printf(buf);
""",
            target_file="docs/build.md",
            all_pr_files=["docs/build.md"],
            language="cpp",
            expected_findings=[],
            is_negative_case=True,
            tags=["edge_case", "non_cpp"],
        ),
        BenchmarkCase(
            id="edge_cpp_syntax_error",
            name="Edge: C/C++ code with intentional syntax error",
            description="Malformed syntax fragments must not throw exceptions or crash the pipeline.",
            diff_patch="""@@ -1,2 +1,3 @@
 void broken() {
+    int x = @@@ ??? <<<< ;;; :::
 }
""",
            target_file="src/broken.c",
            all_pr_files=["src/broken.c"],
            language="cpp",
            expected_findings=[],
            is_negative_case=True,
            tags=["edge_case", "syntax_error"],
        ),
        BenchmarkCase(
            id="edge_cpp_renamed_file_no_changes",
            name="Edge: Renamed header file with zero modified lines",
            description="File rename without added hunk lines must produce zero findings.",
            diff_patch="",
            target_file="include/renamed.hpp",
            all_pr_files=["include/renamed.hpp"],
            language="cpp",
            expected_findings=[],
            is_negative_case=True,
            tags=["edge_case", "file_rename"],
        ),
    ]

    return BenchmarkDataset(
        name=DATASET_NAME_CPP,
        version=DATASET_VERSION_CPP,
        description="Frozen evaluation benchmark dataset for Patchwise C and C++ static rules (v1.0.0)",
        cases=cases,
    )
