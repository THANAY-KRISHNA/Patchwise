"""Comprehensive Unit Tests for JavaScript and TypeScript AST Rules (JS001 - JS004)."""
from typing import List, Optional
from src.analyzer.plugins.javascript.rules import analyze_javascript_file_diff
from src.parser.models import DiffLine, FileChangeStatus, LineType, ParsedFileDiff, ParsedHunk
from src.schemas.findings import FindingProvenance, FindingSeverity


def _make_file_diff(
    file_path: str,
    patch_lines: List[str],
    old_start: int = 1,
    new_start: int = 1,
) -> ParsedFileDiff:
    """Helper to construct a ParsedFileDiff from patch lines ('+...', '-...', ' ...')."""
    diff_lines: List[DiffLine] = []
    added_lines: List[int] = []
    deleted_lines: List[int] = []
    context_lines: List[int] = []

    cur_old = old_start
    cur_new = new_start

    for line in patch_lines:
        prefix = line[0] if line else " "
        content = line[1:] if len(line) > 1 else ""

        if prefix == "+":
            diff_lines.append(
                DiffLine(type=LineType.ADDED, content=content, old_line_number=None, new_line_number=cur_new)
            )
            added_lines.append(cur_new)
            cur_new += 1
        elif prefix == "-":
            diff_lines.append(
                DiffLine(type=LineType.DELETED, content=content, old_line_number=cur_old, new_line_number=None)
            )
            deleted_lines.append(cur_old)
            cur_old += 1
        else:
            diff_lines.append(
                DiffLine(type=LineType.CONTEXT, content=content, old_line_number=cur_old, new_line_number=cur_new)
            )
            context_lines.append(cur_new)
            cur_old += 1
            cur_new += 1

    hunk = ParsedHunk(
        old_start=old_start,
        old_length=len(deleted_lines) + len(context_lines),
        new_start=new_start,
        new_length=len(added_lines) + len(context_lines),
        header=f"@@ -{old_start},{len(deleted_lines) + len(context_lines)} +{new_start},{len(added_lines) + len(context_lines)} @@",
        lines=diff_lines,
        added_lines=added_lines,
        deleted_lines=deleted_lines,
        context_lines=context_lines,
    )

    return ParsedFileDiff(
        file_path=file_path,
        status=FileChangeStatus.MODIFIED,
        is_binary=False,
        hunks=[hunk],
        added_lines=added_lines,
        deleted_lines=deleted_lines,
        context_lines=context_lines,
    )


# =============================================================================
# Rule JS001: Unsafe Dynamic Code Execution
# =============================================================================

def test_js001_eval_positive():
    diff = _make_file_diff(
        "src/runtime.js",
        [
            " function execute(payload) {",
            "+    const result = eval(payload.code);",
            "+    return result;",
            " }",
        ],
        new_start=10,
    )
    findings = analyze_javascript_file_diff(diff)
    assert len(findings) == 1
    assert findings[0].rule_id == "JS001"
    assert findings[0].start_line == 11
    assert findings[0].source == FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS
    assert findings[0].severity == FindingSeverity.HIGH
    assert "eval" in findings[0].title.lower()


def test_js001_new_function_positive():
    diff = _make_file_diff(
        "src/factory.ts",
        [
            " interface Options { dynamic: boolean; }",
            "+const builder = new Function('a', 'b', 'return a + b;');",
            "+const res = builder(1, 2);",
        ],
        new_start=20,
    )
    findings = analyze_javascript_file_diff(diff)
    assert len(findings) == 1
    assert findings[0].rule_id == "JS001"
    assert findings[0].start_line == 21
    assert "function" in findings[0].title.lower()


def test_js001_set_timeout_string_positive():
    diff = _make_file_diff(
        "src/timer.js",
        [
            " function delayedAlert(msg) {",
            "+    setTimeout('alert(' + msg + ')', 1000);",
            " }",
        ],
        new_start=5,
    )
    findings = analyze_javascript_file_diff(diff)
    assert len(findings) == 1
    assert findings[0].rule_id == "JS001"
    assert findings[0].start_line == 6


def test_js001_set_timeout_callback_negative():
    diff = _make_file_diff(
        "src/timer.js",
        [
            " function delayedAlert(msg) {",
            "+    setTimeout(() => { console.log(msg); }, 1000);",
            "+    setTimeout(onComplete, 500);",
            " }",
        ],
        new_start=5,
    )
    findings = analyze_javascript_file_diff(diff)
    assert len(findings) == 0


# =============================================================================
# Rule JS002: DOM HTML Injection / XSS
# =============================================================================

def test_js002_inner_html_positive():
    diff = _make_file_diff(
        "src/renderer.js",
        [
            " function render(container, markup) {",
            "+    container.innerHTML = markup;",
            " }",
        ],
        new_start=15,
    )
    findings = analyze_javascript_file_diff(diff)
    assert len(findings) == 1
    assert findings[0].rule_id == "JS002"
    assert findings[0].start_line == 16
    assert "innerhtml" in findings[0].title.lower()


def test_js002_document_write_positive():
    diff = _make_file_diff(
        "src/legacy.js",
        [
            " function output(userText) {",
            "+    document.write('<div>' + userText + '</div>');",
            " }",
        ],
        new_start=30,
    )
    findings = analyze_javascript_file_diff(diff)
    assert len(findings) == 1
    assert findings[0].rule_id == "JS002"
    assert findings[0].start_line == 31
    assert "document.write" in findings[0].title.lower()


def test_js002_dangerously_set_inner_html_jsx_positive():
    diff = _make_file_diff(
        "src/components/Article.tsx",
        [
            " export function Article({ content }: { content: string }) {",
            "+    return (",
            "+        <div className='article' dangerouslySetInnerHTML={{ __html: content }} />",
            "+    );",
            " }",
        ],
        new_start=40,
    )
    findings = analyze_javascript_file_diff(diff)
    assert len(findings) == 1
    assert findings[0].rule_id == "JS002"
    assert findings[0].start_line in (41, 42)
    assert "dangerouslysetinnerhtml" in findings[0].title.lower()


def test_js002_safe_text_content_negative():
    diff = _make_file_diff(
        "src/renderer.js",
        [
            " function renderSafe(container, text) {",
            "+    container.textContent = text;",
            "+    container.innerText = text;",
            " }",
        ],
        new_start=15,
    )
    findings = analyze_javascript_file_diff(diff)
    assert len(findings) == 0


# =============================================================================
# Rule JS003: Unsafe Shell Command Construction
# =============================================================================

def test_js003_exec_template_literal_positive():
    diff = _make_file_diff(
        "src/cli.ts",
        [
            " import { exec } from 'child_process';",
            " function inspectFile(filePath: string): void {",
            "+    exec(`ls -la ${filePath}`);",
            " }",
        ],
        new_start=1,
    )
    findings = analyze_javascript_file_diff(diff)
    assert len(findings) == 1
    assert findings[0].rule_id == "JS003"
    assert findings[0].start_line == 3
    assert "shell" in findings[0].title.lower()


def test_js003_exec_concat_positive():
    diff = _make_file_diff(
        "src/runner.js",
        [
            " const cp = require('child_process');",
            " function pingHost(host) {",
            "+    cp.execSync('ping -c 1 ' + host);",
            " }",
        ],
        new_start=10,
    )
    findings = analyze_javascript_file_diff(diff)
    assert len(findings) == 1
    assert findings[0].rule_id == "JS003"
    assert findings[0].start_line == 12


def test_js003_exec_file_safe_negative():
    diff = _make_file_diff(
        "src/cli.js",
        [
            " const { execFile, exec } = require('child_process');",
            " function runSafe(arg) {",
            "+    execFile('ls', ['-la', arg]);",
            "+    exec('git status');",
            " }",
        ],
        new_start=1,
    )
    findings = analyze_javascript_file_diff(diff)
    assert len(findings) == 0


# =============================================================================
# Rule JS004: Potentially Unsafe SQL Query Construction
# =============================================================================

def test_js004_sql_template_literal_positive():
    diff = _make_file_diff(
        "src/db/users.ts",
        [
            " async function getUser(userId: string) {",
            "+    const result = await db.query(`SELECT * FROM users WHERE id = ${userId}`);",
            "+    return result.rows[0];",
            " }",
        ],
        new_start=25,
    )
    findings = analyze_javascript_file_diff(diff)
    assert len(findings) == 1
    assert findings[0].rule_id == "JS004"
    assert findings[0].start_line == 26
    assert "sql" in findings[0].title.lower()


def test_js004_sql_concatenation_positive():
    diff = _make_file_diff(
        "src/services/catalog.js",
        [
            " function findItems(catId) {",
            "+    const sql = 'SELECT id, name FROM items WHERE category = ' + catId;",
            "+    return client.execute(sql);",
            " }",
        ],
        new_start=50,
    )
    findings = analyze_javascript_file_diff(diff)
    assert len(findings) >= 1
    assert any(f.rule_id == "JS004" for f in findings)


def test_js004_prisma_raw_unsafe_positive():
    diff = _make_file_diff(
        "src/repo.ts",
        [
            " async function queryRaw(userQuery: string) {",
            "+    return await prisma.$queryRawUnsafe(userQuery);",
            " }",
        ],
        new_start=1,
    )
    findings = analyze_javascript_file_diff(diff)
    assert len(findings) == 1
    assert findings[0].rule_id == "JS004"


def test_js004_parameterized_query_negative():
    diff = _make_file_diff(
        "src/db/users.js",
        [
            " async function getUserSafe(userId) {",
            "+    const result = await db.query('SELECT * FROM users WHERE id = $1', [userId]);",
            "+    return result.rows[0];",
            " }",
        ],
        new_start=1,
    )
    findings = analyze_javascript_file_diff(diff)
    assert len(findings) == 0


# =============================================================================
# Edge Cases, Multi-Hunk Line Mappings, and Non-JS Handling
# =============================================================================

def test_javascript_multi_hunk_line_mapping():
    # Hunk 1 at line 10, Hunk 2 at line 50
    hunk1 = ParsedHunk(
        old_start=10,
        old_length=2,
        new_start=10,
        new_length=3,
        header="@@ -10,2 +10,3 @@",
        lines=[
            DiffLine(type=LineType.CONTEXT, content="function init() {", old_line_number=10, new_line_number=10),
            DiffLine(type=LineType.ADDED, content="    eval(initScript);", old_line_number=None, new_line_number=11),
            DiffLine(type=LineType.CONTEXT, content="}", old_line_number=11, new_line_number=12),
        ],
        added_lines=[11],
        deleted_lines=[],
        context_lines=[10, 12],
    )
    hunk2 = ParsedHunk(
        old_start=50,
        old_length=2,
        new_start=50,
        new_length=3,
        header="@@ -50,2 +50,3 @@",
        lines=[
            DiffLine(type=LineType.CONTEXT, content="function render(el, val) {", old_line_number=50, new_line_number=50),
            DiffLine(type=LineType.ADDED, content="    el.innerHTML = val;", old_line_number=None, new_line_number=51),
            DiffLine(type=LineType.CONTEXT, content="}", old_line_number=51, new_line_number=52),
        ],
        added_lines=[51],
        deleted_lines=[],
        context_lines=[50, 52],
    )

    diff = ParsedFileDiff(
        file_path="src/multi.js",
        status=FileChangeStatus.MODIFIED,
        is_binary=False,
        hunks=[hunk1, hunk2],
        added_lines=[11, 51],
        deleted_lines=[],
        context_lines=[10, 12, 50, 52],
    )

    findings = analyze_javascript_file_diff(diff)
    assert len(findings) == 2
    rule_ids = {f.rule_id for f in findings}
    assert rule_ids == {"JS001", "JS002"}
    line_map = {f.rule_id: f.start_line for f in findings}
    assert line_map["JS001"] == 11
    assert line_map["JS002"] == 51


def test_empty_diff_handling():
    diff = ParsedFileDiff(
        file_path="src/empty.js",
        status=FileChangeStatus.MODIFIED,
        is_binary=False,
        hunks=[],
        added_lines=[],
        deleted_lines=[],
        context_lines=[],
    )
    assert analyze_javascript_file_diff(diff) == []


def test_binary_diff_handling():
    diff = ParsedFileDiff(
        file_path="assets/bundle.min.js",
        status=FileChangeStatus.MODIFIED,
        is_binary=True,
        hunks=[],
        added_lines=[1, 2],
        deleted_lines=[],
        context_lines=[],
    )
    assert analyze_javascript_file_diff(diff) == []


def test_syntax_error_tolerance():
    diff = _make_file_diff(
        "src/broken.js",
        [
            "+function broken( {",
            "+    const x = @@@;",
        ],
        new_start=1,
    )
    # Must not raise exception, return empty list gracefully
    findings = analyze_javascript_file_diff(diff)
    assert findings == []
