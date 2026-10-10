"""Curated and Versioned Benchmark Dataset Fixtures for Patchwise (v1.0.0).

Contains labelled code diffs with ground-truth expected findings for deterministic rules
PY001–PY005, clean negative examples (true negatives), edge cases, and malformed inputs.
"""
from typing import List
from ..schemas.findings import FindingProvenance
from .models import BenchmarkCase, BenchmarkDataset, ExpectedFinding

DATASET_VERSION = "v1.0.0"
DATASET_NAME = "patchwise-python-deterministic-benchmark"


def get_default_benchmark_dataset() -> BenchmarkDataset:
    """Builds and returns the frozen benchmark dataset (v1.0.0)."""
    cases: List[BenchmarkCase] = [
        # =====================================================================
        # Category 1: Deterministic Rule Positives (PY001 - PY005)
        # =====================================================================
        BenchmarkCase(
            id="py001_missing_validation_positive",
            name="PY001: Unchecked external payload dictionary key access",
            description="Direct dictionary key access on 'payload' without prior verification raises unhandled KeyError.",
            diff_patch="""@@ -10,1 +10,3 @@ def handle_request(payload):
 def handle_request(payload):
+    user_id = payload["user_id"]
+    return user_id
""",
            target_file="src/api.py",
            all_pr_files=["src/api.py", "tests/test_api.py"],
            expected_findings=[
                ExpectedFinding(
                    rule_id="PY001",
                    file_path="src/api.py",
                    start_line=11,
                    end_line=11,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Unchecked subscript access on payload['user_id']",
                )
            ],
            tags=["py001", "input_validation", "positive"],
        ),
        BenchmarkCase(
            id="py002_bare_except_positive",
            name="PY002: Bare except clause",
            description="Bare 'except:' intercepts all interpreter signals and hides bugs.",
            diff_patch="""@@ -15,1 +15,5 @@ def run_job():
 def run_job():
+    try:
+        do_work()
+    except:
+        pass
""",
            target_file="src/worker.py",
            all_pr_files=["src/worker.py", "tests/test_worker.py"],
            expected_findings=[
                ExpectedFinding(
                    rule_id="PY002",
                    file_path="src/worker.py",
                    start_line=18,
                    end_line=18,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Bare except catches BaseException and masks defects",
                )
            ],
            tags=["py002", "exception_handling", "positive"],
        ),
        BenchmarkCase(
            id="py002_base_exception_positive",
            name="PY002: Catching BaseException explicitly",
            description="Explicitly catching BaseException suppresses KeyboardInterrupt and SystemExit.",
            diff_patch="""@@ -5,1 +5,5 @@ def execute():
 def execute():
+    try:
+        step()
+    except BaseException:
+        cleanup()
""",
            target_file="src/runner.py",
            all_pr_files=["src/runner.py", "tests/test_runner.py"],
            expected_findings=[
                ExpectedFinding(
                    rule_id="PY002",
                    file_path="src/runner.py",
                    start_line=8,
                    end_line=8,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Explicit BaseException catch suppresses interpreter signals",
                )
            ],
            tags=["py002", "exception_handling", "positive"],
        ),
        BenchmarkCase(
            id="py002_silent_pass_positive",
            name="PY002: Silent exception suppression with pass",
            description="Silently discarding exceptions with bare pass conceals failures from monitoring.",
            diff_patch="""@@ -20,1 +20,5 @@ def safe_call():
 def safe_call():
+    try:
+        call()
+    except Exception:
+        pass
""",
            target_file="src/handler.py",
            all_pr_files=["src/handler.py", "tests/test_handler.py"],
            expected_findings=[
                ExpectedFinding(
                    rule_id="PY002",
                    file_path="src/handler.py",
                    start_line=23,
                    end_line=23,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Silent exception suppression using bare pass",
                )
            ],
            tags=["py002", "exception_handling", "positive"],
        ),
        BenchmarkCase(
            id="py003_mutable_list_default_positive",
            name="PY003: Mutable list default parameter",
            description="Default parameter items=[] is shared across all function calls.",
            diff_patch="""@@ -0,0 +1,3 @@
+def append_to_list(val, items=[]):
+    items.append(val)
+    return items
""",
            target_file="src/utils.py",
            all_pr_files=["src/utils.py", "tests/test_utils.py"],
            expected_findings=[
                ExpectedFinding(
                    rule_id="PY003",
                    file_path="src/utils.py",
                    start_line=1,
                    end_line=1,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Mutable list default evaluated once at definition time",
                )
            ],
            tags=["py003", "code_quality", "positive"],
        ),
        BenchmarkCase(
            id="py003_mutable_dict_default_positive",
            name="PY003: Mutable dictionary default parameter",
            description="Default parameter settings={} creates shared state across invocations.",
            diff_patch="""@@ -0,0 +1,2 @@
+def configure(settings={}):
+    return settings
""",
            target_file="src/config.py",
            all_pr_files=["src/config.py", "tests/test_config.py"],
            expected_findings=[
                ExpectedFinding(
                    rule_id="PY003",
                    file_path="src/config.py",
                    start_line=1,
                    end_line=1,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Mutable dict default evaluated once at definition time",
                )
            ],
            tags=["py003", "code_quality", "positive"],
        ),
        BenchmarkCase(
            id="py004_eval_positive",
            name="PY004: Insecure dynamic execution with eval()",
            description="Calling eval() on dynamic expressions enables remote code execution.",
            diff_patch="""@@ -8,1 +8,3 @@ def compute(expression):
 def compute(expression):
+    result = eval(expression)
+    return result
""",
            target_file="src/evaluator.py",
            all_pr_files=["src/evaluator.py", "tests/test_evaluator.py"],
            expected_findings=[
                ExpectedFinding(
                    rule_id="PY004",
                    file_path="src/evaluator.py",
                    start_line=9,
                    end_line=9,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Arbitrary code execution via eval()",
                )
            ],
            tags=["py004", "security", "positive"],
        ),
        BenchmarkCase(
            id="py004_pickle_positive",
            name="PY004: Insecure deserialization via pickle.loads()",
            description="Deserializing untrusted pickle streams triggers code execution via __reduce__.",
            diff_patch="""@@ -12,1 +12,3 @@ def restore(data):
 def restore(data):
+    obj = pickle.loads(data)
+    return obj
""",
            target_file="src/cache.py",
            all_pr_files=["src/cache.py", "tests/test_cache.py"],
            expected_findings=[
                ExpectedFinding(
                    rule_id="PY004",
                    file_path="src/cache.py",
                    start_line=13,
                    end_line=13,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Unsafe deserialization using pickle.loads",
                )
            ],
            tags=["py004", "security", "positive"],
        ),
        BenchmarkCase(
            id="py004_sql_injection_positive",
            name="PY004: SQL injection via f-string query formatting",
            description="Interpolating variables directly into execute() query strings causes SQL injection.",
            diff_patch="""@@ -25,1 +25,2 @@ def find_user(db, user_id):
 def find_user(db, user_id):
+    return db.execute(f"SELECT * FROM users WHERE id = '{user_id}'")
""",
            target_file="src/repository.py",
            all_pr_files=["src/repository.py", "tests/test_repo.py"],
            expected_findings=[
                ExpectedFinding(
                    rule_id="PY004",
                    file_path="src/repository.py",
                    start_line=26,
                    end_line=26,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="SQL injection via f-string formatting in execute()",
                )
            ],
            tags=["py004", "security", "positive"],
        ),
        BenchmarkCase(
            id="py005_missing_tests_heuristic_positive",
            name="PY005: Missing unit test recommendation",
            description="Recommends tests when business logic is modified without test file changes.",
            diff_patch="""@@ -5,0 +5,3 @@
+def calculate_price(base, rate):
+    discount = 0.1
+    return base * rate * (1 - discount)
""",
            target_file="src/pricing.py",
            all_pr_files=["src/pricing.py"],  # No test files in this PR!
            expected_findings=[
                ExpectedFinding(
                    rule_id="PY005",
                    file_path="src/pricing.py",
                    start_line=5,
                    end_line=5,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Business logic modified without corresponding test file changes",
                )
            ],
            tags=["py005", "test_suggestion", "positive"],
        ),


        # =====================================================================
        # Category 2: Clean Negative Examples (Expected 0 Findings)
        # =====================================================================
        BenchmarkCase(
            id="clean_safe_dict_get_negative",
            name="Clean: Safe dictionary access via .get()",
            description="Using .get() with default handles missing keys without throwing KeyError.",
            diff_patch="""@@ -10,1 +10,3 @@ def handle_request(payload):
 def handle_request(payload):
+    user_id = payload.get("user_id", "guest")
+    return user_id
""",
            target_file="src/api.py",
            all_pr_files=["src/api.py", "tests/test_api.py"],
            expected_findings=[],
            is_negative_case=True,
            tags=["clean", "true_negative", "py001"],
        ),
        BenchmarkCase(
            id="clean_specific_exception_negative",
            name="Clean: Catching specific exceptions and logging",
            description="Catches specific application exceptions and logs the error properly.",
            diff_patch="""@@ -15,1 +15,5 @@ def run_job():
 def run_job():
+    try:
+        do_work()
+    except ValueError as exc:
+        logger.warning(f"Invalid input: {exc}")
""",
            target_file="src/worker.py",
            all_pr_files=["src/worker.py", "tests/test_worker.py"],
            expected_findings=[],
            is_negative_case=True,
            tags=["clean", "true_negative", "py002"],
        ),
        BenchmarkCase(
            id="clean_immutable_default_negative",
            name="Clean: Safe None default with body initialization",
            description="Idiomatic Python default parameter handling using None.",
            diff_patch="""@@ -0,0 +1,5 @@
+def append_to_list(val, items=None):
+    if items is None:
+        items = []
+    items.append(val)
+    return items
""",
            target_file="src/utils.py",
            all_pr_files=["src/utils.py", "tests/test_utils.py"],
            expected_findings=[],
            is_negative_case=True,
            tags=["clean", "true_negative", "py003"],
        ),
        BenchmarkCase(
            id="clean_parameterized_sql_negative",
            name="Clean: Parameterized SQL statement with driver bindings",
            description="Uses parameterized query bindings to prevent SQL injection.",
            diff_patch="""@@ -25,1 +25,2 @@ def find_user(db, user_id):
 def find_user(db, user_id):
+    return db.execute("SELECT * FROM users WHERE id = :user_id", {"user_id": user_id})
""",
            target_file="src/repository.py",
            all_pr_files=["src/repository.py", "tests/test_repo.py"],
            expected_findings=[],
            is_negative_case=True,
            tags=["clean", "true_negative", "py004"],
        ),
        BenchmarkCase(
            id="clean_business_logic_with_tests_negative",
            name="Clean: Business logic modification accompanied by unit tests",
            description="PR includes both business logic updates and tests, so PY005 does not trigger.",
            diff_patch="""@@ -5,1 +5,3 @@ def calculate_price(base, rate):
 def calculate_price(base, rate):
+    discount = 0.1
+    return base * rate * (1 - discount)
""",
            target_file="src/pricing.py",
            all_pr_files=["src/pricing.py", "tests/test_pricing.py"],  # Tests included!
            expected_findings=[],
            is_negative_case=True,
            tags=["clean", "true_negative", "py005"],
        ),

        # =====================================================================
        # Category 3: Edge Cases and Malformed Diffs (Expected 0 Findings)
        # =====================================================================
        BenchmarkCase(
            id="edge_empty_diff",
            name="Edge: Empty diff patch",
            description="An empty patch string with no hunks should evaluate safely without errors.",
            diff_patch="",
            target_file="src/empty.py",
            all_pr_files=["src/empty.py"],
            expected_findings=[],
            is_negative_case=True,
            tags=["edge", "empty"],
        ),
        BenchmarkCase(
            id="edge_binary_file_diff",
            name="Edge: Binary file diff",
            description="Binary file change without patch text should produce no line-level findings.",
            diff_patch="",
            target_file="assets/logo.png",
            all_pr_files=["assets/logo.png"],
            expected_findings=[],
            is_negative_case=True,
            tags=["edge", "binary"],
        ),
        BenchmarkCase(
            id="edge_non_python_markdown",
            name="Edge: Non-Python markdown documentation",
            description="Markdown documentation file should not be processed by Python analyzer.",
            diff_patch="""@@ -0,0 +1,2 @@
+# Project Documentation
+Updated architecture documentation.
""",
            target_file="docs/README.md",
            all_pr_files=["docs/README.md"],
            expected_findings=[],
            is_negative_case=True,
            tags=["edge", "markdown"],
        ),
        BenchmarkCase(
            id="edge_python_syntax_error",
            name="Edge: Python code with syntax error",
            description="Malformed Python syntax is tolerated gracefully without crashing the runner.",
            diff_patch="""@@ -1,0 +1,2 @@
+def broken_syntax(:
+    return ===
""",
            target_file="src/broken.py",
            all_pr_files=["src/broken.py", "tests/test_broken.py"],
            expected_findings=[],
            is_negative_case=True,
            tags=["edge", "syntax_error"],
        ),
        BenchmarkCase(
            id="edge_renamed_file_no_changes",
            name="Edge: Renamed file with zero modified lines",
            description="Renamed file with no added lines should not produce false positive findings.",
            diff_patch="""@@ -1,2 +1,2 @@
 def existing():
     pass
""",
            target_file="src/renamed.py",
            all_pr_files=["src/renamed.py"],
            expected_findings=[],
            is_negative_case=True,
            tags=["edge", "rename"],
        ),
    ]

    return BenchmarkDataset(
        name=DATASET_NAME,
        version=DATASET_VERSION,
        description="Frozen evaluation benchmark suite for deterministic static analysis rules PY001-PY005, clean negatives, and edge cases.",
        cases=cases,
    )


def load_benchmark_dataset(version: str = DATASET_VERSION) -> BenchmarkDataset:
    """Loads a benchmark dataset by version tag."""
    if version == DATASET_VERSION:
        return get_default_benchmark_dataset()
    raise ValueError(f"Unknown benchmark dataset version: '{version}'. Available versions: ['{DATASET_VERSION}']")
