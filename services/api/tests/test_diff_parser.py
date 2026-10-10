"""Unit tests for Git unified diff parser and line mapping."""
import pytest
from src.core.errors import ErrorCode, PatchwiseAPIException
from src.parser.diff_parser import parse_single_file_patch, parse_unified_diff
from src.parser.models import FileChangeStatus, LineType

SAMPLE_MULTI_HUNK_DIFF = """diff --git a/src/math.py b/src/math.py
index e69de29..d95f3ad 100644
--- a/src/math.py
+++ b/src/math.py
@@ -5,6 +5,8 @@ def add(a, b):
     # Context line
     return a + b
 
+def subtract(a, b):
+    return a - b
 
 def multiply(a, b):
     return a * b
@@ -20,5 +22,7 @@ def divide(a, b):
     if b == 0:
         raise ZeroDivisionError()
-    return a / b
+    # Safe division
+    result = a / b
+    return result
"""

SAMPLE_NEW_FILE_DIFF = """diff --git a/src/new_mod.py b/src/new_mod.py
new file mode 100644
index 0000000..a1b2c3d
--- /dev/null
+++ b/src/new_mod.py
@@ -0,0 +1,3 @@
+def brand_new():
+    return "hello"
+
"""

SAMPLE_DELETED_FILE_DIFF = """diff --git a/src/obsolete.py b/src/obsolete.py
deleted file mode 100644
index a1b2c3d..0000000
--- a/src/obsolete.py
+++ /dev/null
@@ -1,3 +0,0 @@
-def obsolete():
-    pass
-
"""

SAMPLE_RENAMED_DIFF = """diff --git a/old_dir/service.py b/new_dir/service.py
similarity index 98%
rename from old_dir/service.py
rename to new_dir/service.py
index 1234567..89abcdef 100644
--- a/old_dir/service.py
+++ b/new_dir/service.py
@@ -1,3 +1,3 @@
 def run():
-    return 1
+    return 2
"""

SAMPLE_BINARY_DIFF = """diff --git a/assets/image.png b/assets/image.png
index 1234567..89abcdef 100644
Binary files a/assets/image.png and b/assets/image.png differ
"""


def test_parse_multi_hunk_diff():
    result = parse_unified_diff(SAMPLE_MULTI_HUNK_DIFF)
    assert result.total_files == 1
    file_diff = result.files[0]
    assert file_diff.file_path == "src/math.py"
    assert file_diff.status == FileChangeStatus.MODIFIED
    assert len(file_diff.hunks) == 2

    # Hunk 1 verification
    hunk1 = file_diff.hunks[0]
    assert hunk1.old_start == 5
    assert hunk1.new_start == 5
    # Lines 8 and 9 were added
    assert 8 in hunk1.added_lines
    assert 9 in hunk1.added_lines
    assert len(hunk1.deleted_lines) == 0

    # Hunk 2 verification
    hunk2 = file_diff.hunks[1]
    assert hunk2.old_start == 20
    assert hunk2.new_start == 22
    assert 22 in hunk2.deleted_lines  # Deleted from old file line 22
    assert 24 in hunk2.added_lines  # Added in new file
    assert 25 in hunk2.added_lines
    assert 26 in hunk2.added_lines

    # File-level line aggregations
    assert file_diff.added_lines == [8, 9, 24, 25, 26]
    assert 22 in file_diff.deleted_lines


def test_parse_new_file_diff():
    result = parse_unified_diff(SAMPLE_NEW_FILE_DIFF)
    assert result.total_files == 1
    file_diff = result.files[0]
    assert file_diff.status == FileChangeStatus.ADDED
    assert file_diff.added_lines == [1, 2, 3]
    assert len(file_diff.deleted_lines) == 0


def test_parse_deleted_file_diff():
    result = parse_unified_diff(SAMPLE_DELETED_FILE_DIFF)
    assert result.total_files == 1
    file_diff = result.files[0]
    assert file_diff.status == FileChangeStatus.DELETED
    assert len(file_diff.added_lines) == 0
    assert file_diff.deleted_lines == [1, 2, 3]


def test_parse_renamed_file_diff():
    result = parse_unified_diff(SAMPLE_RENAMED_DIFF)
    assert result.total_files == 1
    file_diff = result.files[0]
    assert file_diff.status == FileChangeStatus.RENAMED
    assert file_diff.old_path == "old_dir/service.py"
    assert file_diff.new_path == "new_dir/service.py"
    assert file_diff.added_lines == [2]
    assert file_diff.deleted_lines == [2]


def test_parse_binary_diff():
    result = parse_unified_diff(SAMPLE_BINARY_DIFF)
    assert result.total_files == 1
    file_diff = result.files[0]
    assert file_diff.is_binary is True
    assert file_diff.status == FileChangeStatus.BINARY
    assert len(file_diff.hunks) == 0


def test_parse_single_file_patch_helper():
    patch_text = "@@ -1,3 +1,4 @@\n context\n+added line\n context"
    file_diff = parse_single_file_patch(patch_text, filename="app/utils.py")
    assert file_diff.file_path == "app/utils.py"
    assert file_diff.added_lines == [2]
    assert 1 in file_diff.context_lines
    assert 3 in file_diff.context_lines


def test_empty_patch_handling():
    file_diff = parse_single_file_patch("", filename="empty.txt")
    assert file_diff.file_path == "empty.txt"
    assert file_diff.added_lines == []
    assert file_diff.hunks == []


def test_patch_size_limit_enforcement():
    small_diff = SAMPLE_MULTI_HUNK_DIFF
    # Setting max_patch_chars smaller than diff size must raise PATCH_TOO_LARGE
    with pytest.raises(PatchwiseAPIException) as exc_info:
        parse_unified_diff(small_diff, max_patch_chars=50, strict_limits=True)
    assert exc_info.value.error_code == ErrorCode.PATCH_TOO_LARGE


def test_file_count_limit_enforcement():
    multi_file_diff = (
        SAMPLE_NEW_FILE_DIFF + "\n" + SAMPLE_DELETED_FILE_DIFF + "\n" + SAMPLE_RENAMED_DIFF
    )
    # 3 files; max_files=2
    with pytest.raises(PatchwiseAPIException) as exc_info:
        parse_unified_diff(multi_file_diff, max_files=2, strict_limits=True)
    assert exc_info.value.error_code == ErrorCode.PATCH_TOO_LARGE


def test_malformed_patch_tolerance():
    corrupted_patch = """diff --git a/bad.py b/bad.py
--- a/bad.py
+++ b/bad.py
@@ -corrupted header @@
+valid line
@@ -10,2 +10,2 @@
 context
+new line
"""
    result = parse_unified_diff(corrupted_patch)
    assert result.total_files == 1
    # Second hunk is parsed cleanly despite the first hunk having a corrupted header
    assert len(result.warnings) > 0
    assert 11 in result.files[0].added_lines
