"""Curated and Versioned Benchmark Dataset Fixtures for JavaScript and TypeScript (v1.0.0).

Contains 20 labelled code diffs with ground-truth expected findings for deterministic rules
JS001–JS004 across .js, .jsx, .ts, and .tsx, clean negative examples (true negatives),
edge cases, and malformed inputs.
"""
from typing import List
from ..schemas.findings import FindingProvenance
from .models import BenchmarkCase, BenchmarkDataset, ExpectedFinding

DATASET_VERSION_JS = "v1.0.0"
DATASET_NAME_JS = "patchwise-javascript-deterministic-benchmark"


def get_javascript_benchmark_dataset() -> BenchmarkDataset:
    """Builds and returns the frozen JavaScript/TypeScript benchmark dataset (v1.0.0)."""
    cases: List[BenchmarkCase] = [
        # =====================================================================
        # Category 1: Deterministic Rule Positives (JS001 - JS004)
        # =====================================================================
        BenchmarkCase(
            id="js001_eval_positive",
            name="JS001: Arbitrary code execution with eval()",
            description="Evaluating dynamic code string via eval() introduces remote code execution.",
            diff_patch="""@@ -10,1 +10,3 @@ function runSnippet(payload) {
 function runSnippet(payload) {
+    const result = eval(payload.untrustedScript);
+    return result;
 }
""",
            target_file="src/engine.js",
            all_pr_files=["src/engine.js", "tests/engine.test.js"],
            expected_findings=[
                ExpectedFinding(
                    rule_id="JS001",
                    file_path="src/engine.js",
                    start_line=11,
                    end_line=11,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Arbitrary code execution via eval(payload.untrustedScript)",
                )
            ],
            tags=["js001", "dynamic_execution", "positive"],
        ),
        BenchmarkCase(
            id="js001_new_function_positive",
            name="JS001: Dynamic code execution via new Function()",
            description="Compiling code strings via new Function() introduces code evaluation risks.",
            diff_patch="""@@ -5,1 +5,3 @@ function createAdder(expression: string) {
 function createAdder(expression: string) {
+    const fn = new Function('a', 'b', 'return ' + expression);
+    return fn;
 }
""",
            target_file="src/factory.ts",
            all_pr_files=["src/factory.ts", "tests/factory.test.ts"],
            expected_findings=[
                ExpectedFinding(
                    rule_id="JS001",
                    file_path="src/factory.ts",
                    start_line=6,
                    end_line=6,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Dynamic compilation via new Function()",
                )
            ],
            tags=["js001", "dynamic_execution", "positive"],
        ),
        BenchmarkCase(
            id="js001_set_timeout_string_positive",
            name="JS001: String-based dynamic evaluation in setTimeout()",
            description="Passing dynamic string to setTimeout invokes eval parser in runtime.",
            diff_patch="""@@ -20,1 +20,3 @@ function scheduleAlert(userMsg) {
 function scheduleAlert(userMsg) {
+    setTimeout("alert(" + userMsg + ")", 500);
+    return true;
 }
""",
            target_file="src/timer.js",
            all_pr_files=["src/timer.js"],
            expected_findings=[
                ExpectedFinding(
                    rule_id="JS001",
                    file_path="src/timer.js",
                    start_line=21,
                    end_line=21,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="String evaluation in setTimeout",
                )
            ],
            tags=["js001", "dynamic_execution", "positive"],
        ),
        BenchmarkCase(
            id="js002_inner_html_positive",
            name="JS002: DOM HTML injection via innerHTML assignment",
            description="Directly assigning unescaped markup to innerHTML creates DOM-based XSS.",
            diff_patch="""@@ -15,1 +15,3 @@ function displayComment(container, comment) {
 function displayComment(container, comment) {
+    container.innerHTML = comment.rawHtml;
+    return container;
 }
""",
            target_file="src/comments.js",
            all_pr_files=["src/comments.js"],
            expected_findings=[
                ExpectedFinding(
                    rule_id="JS002",
                    file_path="src/comments.js",
                    start_line=16,
                    end_line=16,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="DOM injection via innerHTML",
                )
            ],
            tags=["js002", "dom_injection", "positive"],
        ),
        BenchmarkCase(
            id="js002_document_write_positive",
            name="JS002: Direct DOM stream injection via document.write()",
            description="Writing unescaped markup directly to active document causes XSS vulnerabilities.",
            diff_patch="""@@ -30,1 +30,3 @@ function renderBanner(title) {
 function renderBanner(title) {
+    document.write("<h1>" + title + "</h1>");
+    return true;
 }
""",
            target_file="src/banner.js",
            all_pr_files=["src/banner.js"],
            expected_findings=[
                ExpectedFinding(
                    rule_id="JS002",
                    file_path="src/banner.js",
                    start_line=31,
                    end_line=31,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="DOM injection via document.write()",
                )
            ],
            tags=["js002", "dom_injection", "positive"],
        ),
        BenchmarkCase(
            id="js002_dangerously_set_inner_html_positive",
            name="JS002: Unsanitized React rendering with dangerouslySetInnerHTML",
            description="Using dangerouslySetInnerHTML in JSX exposes application to XSS.",
            diff_patch="""@@ -1,3 +1,5 @@ export function PostView(props: { content: string }) {
 export function PostView(props: { content: string }) {
     return (
+        <div className="post-body" dangerouslySetInnerHTML={{ __html: props.content }} />
     );
 }
""",
            target_file="src/PostView.tsx",
            all_pr_files=["src/PostView.tsx"],
            expected_findings=[
                ExpectedFinding(
                    rule_id="JS002",
                    file_path="src/PostView.tsx",
                    start_line=3,
                    end_line=3,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="DOM injection via dangerouslySetInnerHTML",
                )
            ],
            tags=["js002", "dom_injection", "positive"],
        ),
        BenchmarkCase(
            id="js003_exec_template_literal_positive",
            name="JS003: Shell command injection via template literal",
            description="Interpolating unvalidated input in child_process.exec() leads to command execution.",
            diff_patch="""@@ -1,2 +1,5 @@ import { exec } from "child_process";
 import { exec } from "child_process";
+export function cloneRepo(repoUrl: string): void {
+    exec(`git clone ${repoUrl}`);
+}
""",
            target_file="src/git_service.ts",
            all_pr_files=["src/git_service.ts"],
            expected_findings=[
                ExpectedFinding(
                    rule_id="JS003",
                    file_path="src/git_service.ts",
                    start_line=3,
                    end_line=3,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Command injection via exec template literal",
                )
            ],
            tags=["js003", "shell_injection", "positive"],
        ),
        BenchmarkCase(
            id="js003_exec_concat_positive",
            name="JS003: Shell command injection via string concatenation",
            description="Concatenating input into cp.execSync() enables host command injection.",
            diff_patch="""@@ -1,2 +1,5 @@ const cp = require("child_process");
 const cp = require("child_process");
+function pingHost(host) {
+    cp.execSync("ping -c 1 " + host);
+}
""",
            target_file="src/network.js",
            all_pr_files=["src/network.js"],
            expected_findings=[
                ExpectedFinding(
                    rule_id="JS003",
                    file_path="src/network.js",
                    start_line=3,
                    end_line=3,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Command injection via cp.execSync concatenation",
                )
            ],
            tags=["js003", "shell_injection", "positive"],
        ),
        BenchmarkCase(
            id="js004_sql_template_positive",
            name="JS004: SQL injection via template literal in db.query()",
            description="Interpolating variables directly in SQL query strings bypasses parameterization.",
            diff_patch="""@@ -10,1 +10,4 @@ async function fetchProfile(userId: string) {
 async function fetchProfile(userId: string) {
+    const result = await db.query(`SELECT id, email, role FROM users WHERE id = ${userId}`);
+    return result.rows[0];
 }
""",
            target_file="src/user_store.ts",
            all_pr_files=["src/user_store.ts"],
            expected_findings=[
                ExpectedFinding(
                    rule_id="JS004",
                    file_path="src/user_store.ts",
                    start_line=11,
                    end_line=11,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="SQL injection in db.query template literal",
                )
            ],
            tags=["js004", "sql_injection", "positive"],
        ),
        BenchmarkCase(
            id="js004_sql_concat_positive",
            name="JS004: SQL injection via string concatenation",
            description="Concatenating dynamic values into SQL statement strings creates injection flaw.",
            diff_patch="""@@ -5,1 +5,4 @@ function getOrders(status) {
 function getOrders(status) {
+    const query = "SELECT * FROM orders WHERE status = '" + status + "'";
+    return client.execute(query);
 }
""",
            target_file="src/orders.js",
            all_pr_files=["src/orders.js"],
            expected_findings=[
                ExpectedFinding(
                    rule_id="JS004",
                    file_path="src/orders.js",
                    start_line=6,
                    end_line=6,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="SQL injection via string concatenation",
                )
            ],
            tags=["js004", "sql_injection", "positive"],
        ),
        # =====================================================================
        # Category 2: Clean Negative Cases (True Negatives, 0 Expected Findings)
        # =====================================================================
        BenchmarkCase(
            id="clean_js_safe_timeout_negative",
            name="Clean: Safe callback function passed to setTimeout",
            description="Passing function reference or closure to setTimeout does not invoke eval.",
            diff_patch="""@@ -10,1 +10,3 @@ function scheduleTask(handler) {
 function scheduleTask(handler) {
+    setTimeout(() => { handler(); }, 1000);
+    return true;
 }
""",
            target_file="src/scheduler.js",
            all_pr_files=["src/scheduler.js"],
            expected_findings=[],
            is_negative_case=True,
            tags=["clean", "negative"],
        ),
        BenchmarkCase(
            id="clean_js_text_content_negative",
            name="Clean: Safe DOM update using textContent",
            description="Assigning text to element.textContent encodes entities and prevents XSS.",
            diff_patch="""@@ -12,1 +12,3 @@ function setLabel(container, labelText) {
 function setLabel(container, labelText) {
+    container.textContent = labelText;
+    return container;
 }
""",
            target_file="src/ui.js",
            all_pr_files=["src/ui.js"],
            expected_findings=[],
            is_negative_case=True,
            tags=["clean", "negative"],
        ),
        BenchmarkCase(
            id="clean_js_exec_file_negative",
            name="Clean: Safe process execution via execFile with argument array",
            description="Using execFile with explicit argument vector avoids shell parsing.",
            diff_patch="""@@ -1,2 +1,4 @@ const { execFile } = require("child_process");
 const { execFile } = require("child_process");
+function getVersion() {
+    return execFile("git", ["--version"]);
 }
""",
            target_file="src/tools.js",
            all_pr_files=["src/tools.js"],
            expected_findings=[],
            is_negative_case=True,
            tags=["clean", "negative"],
        ),
        BenchmarkCase(
            id="clean_js_parameterized_sql_negative",
            name="Clean: Parameterized SQL query with driver bind variables",
            description="Parameterized queries with bind array isolate SQL structure from input data.",
            diff_patch="""@@ -1,2 +1,4 @@ async function findUser(id: string) {
 async function findUser(id: string) {
+    return await db.query("SELECT id, name FROM users WHERE id = $1", [id]);
 }
""",
            target_file="src/queries.ts",
            all_pr_files=["src/queries.ts"],
            expected_findings=[],
            is_negative_case=True,
            tags=["clean", "negative"],
        ),
        BenchmarkCase(
            id="clean_jsx_component_negative",
            name="Clean: Standard React JSX rendering without raw HTML",
            description="Standard JSX children rendering automatically applies React HTML escaping.",
            diff_patch="""@@ -1,2 +1,4 @@ export function Badge({ label }: { label: string }) {
 export function Badge({ label }: { label: string }) {
+    return <span className="badge">{label}</span>;
 }
""",
            target_file="src/Badge.tsx",
            all_pr_files=["src/Badge.tsx"],
            expected_findings=[],
            is_negative_case=True,
            tags=["clean", "negative"],
        ),
        # =====================================================================
        # Category 3: Edge Cases (0 Expected Findings)
        # =====================================================================
        BenchmarkCase(
            id="edge_js_empty_diff",
            name="Edge: Empty diff patch",
            description="Diff with zero added lines and empty hunk content.",
            diff_patch="",
            target_file="src/empty.js",
            all_pr_files=["src/empty.js"],
            expected_findings=[],
            is_negative_case=True,
            tags=["edge", "empty_diff"],
        ),
        BenchmarkCase(
            id="edge_js_binary_file_diff",
            name="Edge: Binary file diff",
            description="Binary bundle file marked as is_binary, should be skipped safely.",
            diff_patch="Binary files a/dist/bundle.js and b/dist/bundle.js differ",
            target_file="dist/bundle.js",
            all_pr_files=["dist/bundle.js"],
            expected_findings=[],
            is_negative_case=True,
            tags=["edge", "binary"],
        ),
        BenchmarkCase(
            id="edge_js_non_js_markdown",
            name="Edge: Non-JavaScript markdown documentation diff",
            description="Markdown documentation file should not trigger JS rules.",
            diff_patch="""@@ -1,1 +1,3 @@ # Documentation
 # Documentation
+Use `eval()` carefully when designing compilers.
+Inner HTML attributes should be sanitized.
""",
            target_file="docs/SECURITY.md",
            all_pr_files=["docs/SECURITY.md"],
            expected_findings=[],
            is_negative_case=True,
            tags=["edge", "non_js"],
        ),
        BenchmarkCase(
            id="edge_js_syntax_error",
            name="Edge: JavaScript code with intentional syntax error",
            description="Tolerates incomplete or invalid syntax without crashing the runner.",
            diff_patch="""@@ -1,1 +1,3 @@ function brokenSyntax( {
 function brokenSyntax( {
+    const = @@@ 123;
+    return;
 }
""",
            target_file="src/broken.js",
            all_pr_files=["src/broken.js"],
            expected_findings=[],
            is_negative_case=True,
            tags=["edge", "syntax_error"],
        ),
        BenchmarkCase(
            id="edge_js_renamed_file_no_changes",
            name="Edge: Renamed file with zero modified lines",
            description="File renamed without any content modifications.",
            diff_patch="""@@ -1,3 +1,3 @@ export const VERSION = "1.0.0";
 export const VERSION = "1.0.0";
 export const APP = "Patchwise";
""",
            target_file="src/constants.ts",
            all_pr_files=["src/constants.ts"],
            expected_findings=[],
            is_negative_case=True,
            tags=["edge", "renamed"],
        ),
    ]

    return BenchmarkDataset(
        name=DATASET_NAME_JS,
        version=DATASET_VERSION_JS,
        description="Frozen, curated evaluation benchmark dataset for JavaScript and TypeScript AST rules (v1.0.0).",
        cases=cases,
    )
