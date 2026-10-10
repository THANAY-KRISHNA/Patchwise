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
    assert py002_findings[0].start_line == 8
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
