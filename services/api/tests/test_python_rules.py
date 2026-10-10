"""Unit tests for deterministic Python AST rules PY001 through PY005."""
import pytest
from src.analyzer.plugins.python.rules import analyze_python_file_diff
from src.parser.diff_parser import parse_single_file_patch
from src.schemas.findings import FindingCategory, FindingProvenance, FindingSeverity


def test_py001_input_validation_positive():
    patch = """@@ -1,3 +1,6 @@
 def handler(payload):
-    pass
+    # Unchecked subscript access
+    user_id = payload["id"]
+    return user_id
"""
    file_diff = parse_single_file_patch(patch, filename="src/handler.py")
    findings = analyze_python_file_diff(file_diff)
    py001_findings = [f for f in findings if f.rule_id == "PY001"]
    assert len(py001_findings) == 1
    assert py001_findings[0].category == FindingCategory.INPUT_VALIDATION
    assert py001_findings[0].severity == FindingSeverity.MEDIUM
    assert py001_findings[0].start_line == 3


def test_py001_input_validation_negative():
    patch = """@@ -1,3 +1,6 @@
 def handler(payload):
-    pass
+    # Safe access via get with default
+    user_id = payload.get("id", None)
+    return user_id
"""
    file_diff = parse_single_file_patch(patch, filename="src/handler.py")
    findings = analyze_python_file_diff(file_diff)
    py001_findings = [f for f in findings if f.rule_id == "PY001"]
    assert len(py001_findings) == 0


def test_py002_bare_except_positive():
    patch = """@@ -5,4 +5,8 @@ def parse_data():
     try:
         risky_operation()
-    except ValueError:
+    except:
+        print("failed")
"""
    file_diff = parse_single_file_patch(patch, filename="src/parser.py")
    findings = analyze_python_file_diff(file_diff)
    py002_findings = [f for f in findings if f.rule_id == "PY002"]
    assert len(py002_findings) == 1
    assert "Bare except" in py002_findings[0].title
    assert py002_findings[0].start_line == 7
    assert py002_findings[0].severity == FindingSeverity.HIGH


def test_py002_base_exception_positive():
    patch = """@@ -5,4 +5,7 @@ def worker():
     try:
         run()
+    except BaseException:
+        pass
"""
    file_diff = parse_single_file_patch(patch, filename="src/worker.py")
    findings = analyze_python_file_diff(file_diff)
    py002_findings = [f for f in findings if f.rule_id == "PY002"]
    assert len(py002_findings) >= 1
    assert any("BaseException" in f.title for f in py002_findings)


def test_py002_silent_suppression_positive():
    patch = """@@ -1,4 +1,7 @@
 def quiet():
     try:
         do_work()
+    except Exception:
+        pass
"""
    file_diff = parse_single_file_patch(patch, filename="src/quiet.py")
    findings = analyze_python_file_diff(file_diff)
    py002_findings = [f for f in findings if f.rule_id == "PY002"]
    assert len(py002_findings) == 1
    assert "Silent exception suppression" in py002_findings[0].title


def test_py003_mutable_defaults_positive():
    patch = """@@ -1,3 +1,6 @@
-def register_user(name):
+def register_user(name, tags=[], metadata={}, items=list()):
     return name
"""
    file_diff = parse_single_file_patch(patch, filename="src/auth.py")
    findings = analyze_python_file_diff(file_diff)
    py003_findings = [f for f in findings if f.rule_id == "PY003"]
    assert len(py003_findings) >= 2
    assert all(f.category == FindingCategory.CODE_QUALITY for f in py003_findings)
    assert all(f.start_line == 1 for f in py003_findings)


def test_py003_mutable_defaults_negative():
    patch = """@@ -1,3 +1,7 @@
-def safe_func():
+def safe_func(tags=None):
+    if tags is None:
+        tags = []
     return tags
"""
    file_diff = parse_single_file_patch(patch, filename="src/safe.py")
    findings = analyze_python_file_diff(file_diff)
    py003_findings = [f for f in findings if f.rule_id == "PY003"]
    assert len(py003_findings) == 0


def test_py004_eval_and_pickle_positive():
    patch = """@@ -1,4 +1,8 @@
 def execute_dynamic(user_expr, raw_payload):
-    return None
+    import pickle
+    val = eval(user_expr)
+    obj = pickle.loads(raw_payload)
+    return val, obj
"""
    file_diff = parse_single_file_patch(patch, filename="src/danger.py")
    findings = analyze_python_file_diff(file_diff)
    py004_findings = [f for f in findings if f.rule_id == "PY004"]
    assert len(py004_findings) == 2
    titles = [f.title for f in py004_findings]
    assert any("eval" in t for t in titles)
    assert any("pickle" in t for t in titles)
    assert all(f.severity == FindingSeverity.CRITICAL for f in py004_findings)


def test_py004_sql_injection_positive():
    patch = """@@ -1,4 +1,6 @@
 def query_user(cursor, user_id):
-    pass
+    # Dangerous SQL f-string
+    cursor.execute(f"SELECT * FROM accounts WHERE id = {user_id}")
"""
    file_diff = parse_single_file_patch(patch, filename="src/db_service.py")
    findings = analyze_python_file_diff(file_diff)
    py004_findings = [f for f in findings if f.rule_id == "PY004"]
    assert len(py004_findings) == 1
    assert "SQL injection" in py004_findings[0].title
    assert py004_findings[0].severity == FindingSeverity.HIGH


def test_py004_sql_injection_negative():
    patch = """@@ -1,4 +1,6 @@
 def query_user(cursor, user_id):
-    pass
+    # Safe parameterized query
+    cursor.execute("SELECT * FROM accounts WHERE id = %s", (user_id,))
"""
    file_diff = parse_single_file_patch(patch, filename="src/db_service.py")
    findings = analyze_python_file_diff(file_diff)
    py004_findings = [f for f in findings if f.rule_id == "PY004"]
    assert len(py004_findings) == 0


def test_py005_test_suggestion_heuristic_when_tests_missing():
    patch = """@@ -1,2 +1,5 @@
 def business_logic():
+    x = 42
+    return x * 2
"""
    file_diff = parse_single_file_patch(patch, filename="src/business_logic.py")
    # All files modified in PR do NOT include any test file
    all_files_in_pr = ["src/business_logic.py", "docs/notes.md"]
    findings = analyze_python_file_diff(file_diff, all_pr_files=all_files_in_pr)
    py005_findings = [f for f in findings if f.rule_id == "PY005"]
    assert len(py005_findings) == 1
    assert py005_findings[0].category == FindingCategory.TEST_SUGGESTION
    assert py005_findings[0].severity == FindingSeverity.INFO
    assert "Missing test coverage" in py005_findings[0].title


def test_py005_test_suggestion_not_emitted_when_tests_present():
    patch = """@@ -1,2 +1,5 @@
 def business_logic():
+    x = 42
+    return x * 2
"""
    file_diff = parse_single_file_patch(patch, filename="src/business_logic.py")
    # PR touches a test file!
    all_files_in_pr = ["src/business_logic.py", "tests/test_business_logic.py"]
    findings = analyze_python_file_diff(file_diff, all_pr_files=all_files_in_pr)
    py005_findings = [f for f in findings if f.rule_id == "PY005"]
    assert len(py005_findings) == 0


def test_multiple_diff_hunks_exact_line_mapping():
    """Verify findings across multiple hunks map to exact new file lines in each hunk."""
    patch = """@@ -10,3 +10,6 @@ def parse_request(req):
     header = req.header
-    pass
+    # Hunk 1: Unchecked dict access on line 12
+    user_id = payload["user_id"]
+    return user_id
@@ -50,3 +53,6 @@ def process_items():
     items = []
-    pass
+    # Hunk 2: Mutable default on line 55
+    def helper(options=[]):
+        return options
"""
    file_diff = parse_single_file_patch(patch, filename="src/service.py")
    findings = analyze_python_file_diff(file_diff)
    
    py001 = [f for f in findings if f.rule_id == "PY001"]
    py003 = [f for f in findings if f.rule_id == "PY003"]

    assert len(py001) == 1
    assert py001[0].start_line == 12
    assert py001[0].end_line == 12

    assert len(py003) == 1
    assert py003[0].start_line == 55
    assert py003[0].end_line == 55


def test_indented_snippet_wrapped_line_mapping():
    """Diff snippet with statements only valid inside functions (e.g. return) uses synthetic wrapper and preserves exact line mapping."""
    patch = """@@ -25,2 +25,3 @@
-    return None
+    return user_input["token"]
"""
    file_diff = parse_single_file_patch(patch, filename="src/handler.py")
    findings = analyze_python_file_diff(file_diff)
    
    py001 = [f for f in findings if f.rule_id == "PY001"]
    assert len(py001) == 1
    # Line 25 is the exact line of return user_input["token"]
    assert py001[0].start_line == 25
    assert py001[0].end_line == 25


def test_multiline_execute_line_mapping():
    """Multiline cursor.execute call correctly maps finding to query line."""
    patch = """@@ -30,2 +30,6 @@ def fetch_record(cursor, item_id):
     # start
-    pass
+    cursor.execute(
+        f"SELECT * FROM items "
+        f"WHERE id = {item_id}"
+    )
"""
    file_diff = parse_single_file_patch(patch, filename="src/db.py")
    findings = analyze_python_file_diff(file_diff)
    
    py004 = [f for f in findings if f.rule_id == "PY004"]
    assert len(py004) == 1
    # Must point to line 31 or 32 (both are in added_lines)
    assert py004[0].start_line in (31, 32)


def test_py004_non_sql_execute_negative():
    """Non-SQL arbitrary string concatenation or f-strings in execute() are not flagged."""
    patch = """@@ -10,3 +10,7 @@ def run_task(executor, task_name, task_id):
-    pass
+    # Calling an executor/runner with non-SQL string operations
+    executor.execute("start_" + task_name)
+    executor.execute(f"job-prefix-{task_id}")
+    executor.execute("run_worker_%s" % task_id)
"""
    file_diff = parse_single_file_patch(patch, filename="src/jobs.py")
    findings = analyze_python_file_diff(file_diff)
    
    py004 = [f for f in findings if f.rule_id == "PY004"]
    assert len(py004) == 0


def test_py004_sql_concat_and_percent_positive():
    """Binary string concatenation and %-formatting containing SQL keywords are flagged."""
    patch = """@@ -15,3 +15,6 @@ def run_queries(cursor, table_name, user_id):
-    pass
+    cursor.execute("SELECT * FROM " + table_name)
+    cursor.execute("DELETE FROM sessions WHERE uid = %s" % user_id)
"""
    file_diff = parse_single_file_patch(patch, filename="src/dao.py")
    findings = analyze_python_file_diff(file_diff)
    
    py004 = [f for f in findings if f.rule_id == "PY004"]
    assert len(py004) == 2
    assert all("Potential SQL injection" in f.title for f in py004)


def test_py005_unrelated_test_does_not_suppress_suggestion():
    """An unrelated test file in PR does NOT suppress missing test suggestion for modified logic."""
    patch = """@@ -1,2 +1,5 @@
 def calculate_pricing(units):
+    rate = 1.25
+    return units * rate
"""
    file_diff = parse_single_file_patch(patch, filename="src/billing/pricing.py")
    # PR touches an unrelated test file (test_auth.py)
    all_files_in_pr = ["src/billing/pricing.py", "tests/test_auth.py"]
    findings = analyze_python_file_diff(file_diff, all_pr_files=all_files_in_pr)
    
    py005 = [f for f in findings if f.rule_id == "PY005"]
    assert len(py005) == 1
    assert "Missing test coverage" in py005[0].title


def test_py005_related_directory_or_module_test_suppresses_suggestion():
    """A related test file (matching module stem or directory) suppresses suggestion."""
    patch = """@@ -1,2 +1,5 @@
 def calculate_pricing(units):
+    rate = 1.25
+    return units * rate
"""
    file_diff = parse_single_file_patch(patch, filename="src/billing/pricing.py")
    # 1. Matching module stem
    all_pr_1 = ["src/billing/pricing.py", "tests/test_pricing.py"]
    findings1 = analyze_python_file_diff(file_diff, all_pr_files=all_pr_1)
    assert len([f for f in findings1 if f.rule_id == "PY005"]) == 0

    # 2. Matching directory token
    all_pr_2 = ["src/billing/pricing.py", "tests/billing/test_calculator.py"]
    findings2 = analyze_python_file_diff(file_diff, all_pr_files=all_pr_2)
    assert len([f for f in findings2 if f.rule_id == "PY005"]) == 0

