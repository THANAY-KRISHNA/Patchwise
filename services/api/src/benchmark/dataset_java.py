"""Curated and Versioned Benchmark Dataset Fixtures for Java (v1.0.0).

Contains 20 labelled code diffs with ground-truth expected findings for deterministic rules
JV001–JV004 across .java files, clean negative examples (true negatives),
edge cases, and malformed inputs.
"""
from typing import List
from ..schemas.findings import FindingProvenance
from .models import BenchmarkCase, BenchmarkDataset, ExpectedFinding

DATASET_VERSION_JAVA = "v1.0.0"
DATASET_NAME_JAVA = "patchwise-java-deterministic-benchmark"


def get_java_benchmark_dataset() -> BenchmarkDataset:
    """Builds and returns the frozen Java benchmark dataset (v1.0.0)."""
    cases: List[BenchmarkCase] = [
        # =====================================================================
        # Category 1: Deterministic Rule Positives (JV001 - JV004)
        # =====================================================================
        BenchmarkCase(
            id="jv001_read_object_positive",
            name="JV001: Potentially unsafe Java deserialization via readObject()",
            description="Deserializing untrusted byte streams using ObjectInputStream.readObject() allows arbitrary code execution.",
            diff_patch="""@@ -8,1 +8,4 @@ public class ObjectReceiver {
 public class ObjectReceiver {
+    public Object deserialize(byte[] data) throws Exception {
+        ObjectInputStream ois = new ObjectInputStream(new ByteArrayInputStream(data));
+        return ois.readObject();
+    }
 }
""",
            target_file="src/main/java/com/example/ObjectReceiver.java",
            all_pr_files=["src/main/java/com/example/ObjectReceiver.java"],
            language="java",
            expected_findings=[
                ExpectedFinding(
                    rule_id="JV001",
                    file_path="src/main/java/com/example/ObjectReceiver.java",
                    start_line=11,
                    end_line=11,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Unsafe deserialization via ois.readObject()",
                )
            ],
            tags=["jv001", "deserialization", "positive"],
        ),
        BenchmarkCase(
            id="jv001_read_unshared_positive",
            name="JV001: Potentially unsafe Java deserialization via readUnshared()",
            description="Deserializing untrusted streams via readUnshared() introduces gadget execution risk.",
            diff_patch="""@@ -12,1 +12,4 @@ public class UnsharedReceiver {
 public class UnsharedReceiver {
+    public Object readPayload(ObjectInputStream stream) throws Exception {
+        return stream.readUnshared();
+    }
 }
""",
            target_file="src/main/java/com/example/UnsharedReceiver.java",
            all_pr_files=["src/main/java/com/example/UnsharedReceiver.java"],
            language="java",
            expected_findings=[
                ExpectedFinding(
                    rule_id="JV001",
                    file_path="src/main/java/com/example/UnsharedReceiver.java",
                    start_line=14,
                    end_line=14,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Unsafe deserialization via stream.readUnshared()",
                )
            ],
            tags=["jv001", "deserialization", "positive"],
        ),
        BenchmarkCase(
            id="jv002_runtime_exec_concat_positive",
            name="JV002: Shell command injection via Runtime.getRuntime().exec() concatenation",
            description="Dynamically constructing shell commands using string concatenation allows command injection.",
            diff_patch="""@@ -15,1 +15,4 @@ public class NetworkTool {
 public class NetworkTool {
+    public void pingHost(String host) throws Exception {
+        Runtime.getRuntime().exec("ping -c 1 " + host);
+    }
 }
""",
            target_file="src/main/java/com/example/NetworkTool.java",
            all_pr_files=["src/main/java/com/example/NetworkTool.java"],
            language="java",
            expected_findings=[
                ExpectedFinding(
                    rule_id="JV002",
                    file_path="src/main/java/com/example/NetworkTool.java",
                    start_line=17,
                    end_line=17,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Command injection in Runtime.getRuntime().exec()",
                )
            ],
            tags=["jv002", "command_injection", "positive"],
        ),
        BenchmarkCase(
            id="jv002_runtime_exec_variable_positive",
            name="JV002: Shell command injection via Runtime.exec() variable argument",
            description="Passing variable command strings directly to Runtime.exec() without array tokenization.",
            diff_patch="""@@ -20,1 +20,4 @@ public class CommandDispatcher {
 public class CommandDispatcher {
+    public void executeUserCommand(String userCmd) throws Exception {
+        Runtime.getRuntime().exec(userCmd);
+    }
 }
""",
            target_file="src/main/java/com/example/CommandDispatcher.java",
            all_pr_files=["src/main/java/com/example/CommandDispatcher.java"],
            language="java",
            expected_findings=[
                ExpectedFinding(
                    rule_id="JV002",
                    file_path="src/main/java/com/example/CommandDispatcher.java",
                    start_line=22,
                    end_line=22,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Command injection via variable passed to Runtime.exec()",
                )
            ],
            tags=["jv002", "command_injection", "positive"],
        ),
        BenchmarkCase(
            id="jv002_process_builder_concat_positive",
            name="JV002: Command injection via ProcessBuilder dynamic argument",
            description="Dynamic string concatenation inside ProcessBuilder invocation.",
            diff_patch="""@@ -30,1 +30,5 @@ public class ShellWorker {
 public class ShellWorker {
+    public void spawnProcess(String filename) throws Exception {
+        ProcessBuilder pb = new ProcessBuilder("sh", "-c", "cat " + filename);
+        pb.start();
+    }
 }
""",
            target_file="src/main/java/com/example/ShellWorker.java",
            all_pr_files=["src/main/java/com/example/ShellWorker.java"],
            language="java",
            expected_findings=[
                ExpectedFinding(
                    rule_id="JV002",
                    file_path="src/main/java/com/example/ShellWorker.java",
                    start_line=32,
                    end_line=32,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Command injection in ProcessBuilder constructor",
                )
            ],
            tags=["jv002", "command_injection", "positive"],
        ),
        BenchmarkCase(
            id="jv003_statement_execute_query_concat_positive",
            name="JV003: SQL injection via Statement.executeQuery() concatenation",
            description="Concatenating user parameters into SQL statements in JDBC Statement.executeQuery().",
            diff_patch="""@@ -40,1 +40,4 @@ public class UserDao {
 public class UserDao {
+    public ResultSet findByUsername(Statement stmt, String username) throws Exception {
+        return stmt.executeQuery("SELECT * FROM users WHERE username = '" + username + "'");
+    }
 }
""",
            target_file="src/main/java/com/example/UserDao.java",
            all_pr_files=["src/main/java/com/example/UserDao.java"],
            language="java",
            expected_findings=[
                ExpectedFinding(
                    rule_id="JV003",
                    file_path="src/main/java/com/example/UserDao.java",
                    start_line=42,
                    end_line=42,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="SQL injection via Statement.executeQuery() concatenation",
                )
            ],
            tags=["jv003", "sql_injection", "positive"],
        ),
        BenchmarkCase(
            id="jv003_connection_prepare_statement_concat_positive",
            name="JV003: SQL injection via Connection.prepareStatement() concatenation",
            description="Dynamic concatenation inside Connection.prepareStatement() instead of bind parameters.",
            diff_patch="""@@ -50,1 +50,4 @@ public class OrderDao {
 public class OrderDao {
+    public PreparedStatement createQuery(Connection conn, String status) throws Exception {
+        return conn.prepareStatement("SELECT * FROM orders WHERE status = " + status);
+    }
 }
""",
            target_file="src/main/java/com/example/OrderDao.java",
            all_pr_files=["src/main/java/com/example/OrderDao.java"],
            language="java",
            expected_findings=[
                ExpectedFinding(
                    rule_id="JV003",
                    file_path="src/main/java/com/example/OrderDao.java",
                    start_line=52,
                    end_line=52,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="SQL injection in Connection.prepareStatement()",
                )
            ],
            tags=["jv003", "sql_injection", "positive"],
        ),
        BenchmarkCase(
            id="jv003_statement_execute_update_concat_positive",
            name="JV003: SQL injection via Statement.executeUpdate() concatenation",
            description="Concatenating dynamic values into DELETE SQL statement in Statement.executeUpdate().",
            diff_patch="""@@ -60,1 +60,4 @@ public class AdminDao {
 public class AdminDao {
+    public int deleteRecord(Statement stmt, String recordId) throws Exception {
+        return stmt.executeUpdate("DELETE FROM audit_logs WHERE id = " + recordId);
+    }
 }
""",
            target_file="src/main/java/com/example/AdminDao.java",
            all_pr_files=["src/main/java/com/example/AdminDao.java"],
            language="java",
            expected_findings=[
                ExpectedFinding(
                    rule_id="JV003",
                    file_path="src/main/java/com/example/AdminDao.java",
                    start_line=62,
                    end_line=62,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="SQL injection in Statement.executeUpdate()",
                )
            ],
            tags=["jv003", "sql_injection", "positive"],
        ),
        BenchmarkCase(
            id="jv004_new_file_concat_positive",
            name="JV004: Path traversal via new File() dynamic string concatenation",
            description="Constructing File paths using dynamic string concatenation allows directory traversal.",
            diff_patch="""@@ -70,1 +70,4 @@ public class StorageService {
 public class StorageService {
+    public File getUploadFile(String uploadDir, String filename) {
+        return new File(uploadDir + "/" + filename);
+    }
 }
""",
            target_file="src/main/java/com/example/StorageService.java",
            all_pr_files=["src/main/java/com/example/StorageService.java"],
            language="java",
            expected_findings=[
                ExpectedFinding(
                    rule_id="JV004",
                    file_path="src/main/java/com/example/StorageService.java",
                    start_line=72,
                    end_line=72,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Path traversal via new File() concatenation",
                )
            ],
            tags=["jv004", "path_traversal", "positive"],
        ),
        BenchmarkCase(
            id="jv004_paths_get_dynamic_positive",
            name="JV004: Path traversal via Paths.get() dynamic parameters",
            description="Constructing Path using unvalidated variable parameters in Paths.get().",
            diff_patch="""@@ -80,1 +80,4 @@ public class PathResolver {
 public class PathResolver {
+    public Path resolveDoc(String baseFolder, String docName) {
+        return Paths.get(baseFolder, docName);
+    }
 }
""",
            target_file="src/main/java/com/example/PathResolver.java",
            all_pr_files=["src/main/java/com/example/PathResolver.java"],
            language="java",
            expected_findings=[
                ExpectedFinding(
                    rule_id="JV004",
                    file_path="src/main/java/com/example/PathResolver.java",
                    start_line=82,
                    end_line=82,
                    expected_source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                    description="Path traversal via Paths.get() with variable parameters",
                )
            ],
            tags=["jv004", "path_traversal", "positive"],
        ),

        # =====================================================================
        # Category 2: Clean Negative Examples (True Negatives)
        # =====================================================================
        BenchmarkCase(
            id="clean_java_buffered_reader_negative",
            name="Clean: Safe stream processing using BufferedReader",
            description="Standard line-by-line reading with BufferedReader without ObjectInputStream.",
            diff_patch="""@@ -5,1 +5,4 @@ public class SafeReader {
 public class SafeReader {
+    public String readHeader(BufferedReader reader) throws Exception {
+        return reader.readLine();
+    }
 }
""",
            target_file="src/main/java/com/example/SafeReader.java",
            all_pr_files=["src/main/java/com/example/SafeReader.java"],
            language="java",
            expected_findings=[],
            is_negative_case=True,
            tags=["clean", "true_negative", "deserialization"],
        ),
        BenchmarkCase(
            id="clean_java_runtime_exec_constant_negative",
            name="Clean: Safe constant command in Runtime.exec()",
            description="Constant string passed to Runtime.exec() without dynamic interpolation.",
            diff_patch="""@@ -10,1 +10,4 @@ public class UptimeChecker {
 public class UptimeChecker {
+    public void checkUptime() throws Exception {
+        Runtime.getRuntime().exec("uptime");
+    }
 }
""",
            target_file="src/main/java/com/example/UptimeChecker.java",
            all_pr_files=["src/main/java/com/example/UptimeChecker.java"],
            language="java",
            expected_findings=[],
            is_negative_case=True,
            tags=["clean", "true_negative", "command_injection"],
        ),
        BenchmarkCase(
            id="clean_java_process_builder_constant_negative",
            name="Clean: Safe ProcessBuilder invocation with constant array arguments",
            description="ProcessBuilder invoked with separate constant argument tokens.",
            diff_patch="""@@ -15,1 +15,4 @@ public class Lister {
 public class Lister {
+    public void listDir() throws Exception {
+        ProcessBuilder pb = new ProcessBuilder("ls", "-la");
+    }
 }
""",
            target_file="src/main/java/com/example/Lister.java",
            all_pr_files=["src/main/java/com/example/Lister.java"],
            language="java",
            expected_findings=[],
            is_negative_case=True,
            tags=["clean", "true_negative", "command_injection"],
        ),
        BenchmarkCase(
            id="clean_java_parameterized_sql_negative",
            name="Clean: Parameterized SQL query with PreparedStatement bind placeholders",
            description="Parameterized SQL query using '?' placeholder without dynamic string concatenation.",
            diff_patch="""@@ -20,1 +20,6 @@ public class SafeDao {
 public class SafeDao {
+    public PreparedStatement buildQuery(Connection conn, String id) throws Exception {
+        PreparedStatement ps = conn.prepareStatement("SELECT * FROM users WHERE id = ?");
+        ps.setString(1, id);
+        return ps;
+    }
 }
""",
            target_file="src/main/java/com/example/SafeDao.java",
            all_pr_files=["src/main/java/com/example/SafeDao.java"],
            language="java",
            expected_findings=[],
            is_negative_case=True,
            tags=["clean", "true_negative", "sql_injection"],
        ),
        BenchmarkCase(
            id="clean_java_constant_file_path_negative",
            name="Clean: Safe constant filesystem path creation",
            description="Creating File instance with fixed static string literal path.",
            diff_patch="""@@ -25,1 +25,4 @@ public class LogConfig {
 public class LogConfig {
+    public File getLogFile() {
+        return new File("/var/log/application.log");
+    }
 }
""",
            target_file="src/main/java/com/example/LogConfig.java",
            all_pr_files=["src/main/java/com/example/LogConfig.java"],
            language="java",
            expected_findings=[],
            is_negative_case=True,
            tags=["clean", "true_negative", "path_traversal"],
        ),

        # =====================================================================
        # Category 3: Edge Cases & Robustness
        # =====================================================================
        BenchmarkCase(
            id="edge_java_empty_diff",
            name="Edge: Empty diff patch",
            description="Zero hunks and empty patch string must produce zero findings gracefully.",
            diff_patch="",
            target_file="src/main/java/com/example/Unchanged.java",
            all_pr_files=["src/main/java/com/example/Unchanged.java"],
            language="java",
            expected_findings=[],
            is_negative_case=True,
            tags=["edge_case", "empty_diff"],
        ),
        BenchmarkCase(
            id="edge_java_binary_file_diff",
            name="Edge: Binary .class file diff",
            description="Binary compiled bytecode file must be detected and skipped without error.",
            diff_patch="GIT binary patch\nliteral 0\nHc$@<O00001\n",
            target_file="target/classes/com/example/App.class",
            all_pr_files=["target/classes/com/example/App.class"],
            language="java",
            expected_findings=[],
            is_negative_case=True,
            tags=["edge_case", "binary_diff"],
        ),
        BenchmarkCase(
            id="edge_java_non_java_markdown",
            name="Edge: Non-Java markdown documentation diff",
            description="Documentation files (.md) in Java projects must not trigger Java rules.",
            diff_patch="""@@ -1,3 +1,5 @@
 # Architecture Notes
+ObjectInputStream ois = new ObjectInputStream(in);
+ois.readObject();
""",
            target_file="docs/architecture.md",
            all_pr_files=["docs/architecture.md"],
            language="java",
            expected_findings=[],
            is_negative_case=True,
            tags=["edge_case", "non_java"],
        ),
        BenchmarkCase(
            id="edge_java_syntax_error",
            name="Edge: Java code with intentional syntax error",
            description="Malformed Java code tokens must not throw exceptions or crash the pipeline.",
            diff_patch="""@@ -1,2 +1,3 @@
 public class Broken {
+    int x = ;;; {{ @@@ !!!
 }
""",
            target_file="src/main/java/com/example/Broken.java",
            all_pr_files=["src/main/java/com/example/Broken.java"],
            language="java",
            expected_findings=[],
            is_negative_case=True,
            tags=["edge_case", "syntax_error"],
        ),
        BenchmarkCase(
            id="edge_java_renamed_file_no_changes",
            name="Edge: Renamed file with zero modified lines",
            description="File rename without added hunk lines must produce zero findings.",
            diff_patch="",
            target_file="src/main/java/com/example/RenamedService.java",
            all_pr_files=["src/main/java/com/example/RenamedService.java"],
            language="java",
            expected_findings=[],
            is_negative_case=True,
            tags=["edge_case", "file_rename"],
        ),
    ]

    return BenchmarkDataset(
        name=DATASET_NAME_JAVA,
        version=DATASET_VERSION_JAVA,
        description="Frozen evaluation benchmark dataset for Patchwise Java AST static rules (v1.0.0)",
        cases=cases,
    )
