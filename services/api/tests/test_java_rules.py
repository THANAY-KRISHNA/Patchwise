"""Comprehensive unit and edge-case tests for Java static analysis rules (JV001-JV004)."""
import pytest
from src.analyzer.plugins.java.rules import analyze_java_file_diff
from src.parser.models import DiffLine, FileChangeStatus, LineType, ParsedFileDiff, ParsedHunk
from src.schemas.findings import FindingCategory, FindingProvenance, FindingSeverity


def _make_java_diff(lines_tuples, file_path="src/main/java/com/example/Service.java") -> ParsedFileDiff:
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


# --- JV001: Java Deserialization Tests ---

def test_jv001_read_object_positive():
    diff = _make_java_diff([
        (" ", "public class Handler {", 1, 1),
        (" ", "    public void process(byte[] data) throws Exception {", 2, 2),
        ("+", "        ObjectInputStream ois = new ObjectInputStream(new ByteArrayInputStream(data));", None, 3),
        ("+", "        Object payload = ois.readObject();", None, 4),
        (" ", "    }", 3, 5),
        (" ", "}", 4, 6),
    ])
    findings = analyze_java_file_diff(diff)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "JV001"
    assert f.start_line == 4
    assert f.source == FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS
    assert f.severity == FindingSeverity.HIGH
    assert f.category == FindingCategory.SECURITY_PATTERN


def test_jv001_read_unshared_positive():
    diff = _make_java_diff([
        (" ", "public class UnsharedHandler {", 1, 1),
        ("+", "    public Object read(ObjectInputStream stream) throws Exception {", None, 2),
        ("+", "        return stream.readUnshared();", None, 3),
        (" ", "    }", 2, 4),
    ])
    findings = analyze_java_file_diff(diff)
    assert len(findings) == 1
    assert findings[0].rule_id == "JV001"
    assert findings[0].start_line == 3


def test_jv001_safe_stream_negative():
    diff = _make_java_diff([
        (" ", "public class SafeReader {", 1, 1),
        ("+", "    public String read(BufferedReader reader) throws Exception {", None, 2),
        ("+", "        return reader.readLine();", None, 3),
        (" ", "    }", 2, 4),
    ])
    findings = analyze_java_file_diff(diff)
    assert len(findings) == 0


# --- JV002: Shell Command Injection Tests ---

def test_jv002_runtime_exec_concatenation_positive():
    diff = _make_java_diff([
        (" ", "public class CmdService {", 1, 1),
        (" ", "    public void run(String target) throws Exception {", 2, 2),
        ("+", '        Runtime.getRuntime().exec("ping -c 1 " + target);', None, 3),
        (" ", "    }", 3, 4),
    ])
    findings = analyze_java_file_diff(diff)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "JV002"
    assert f.start_line == 3
    assert f.source == FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS
    assert f.severity == FindingSeverity.HIGH


def test_jv002_process_builder_dynamic_positive():
    diff = _make_java_diff([
        (" ", "public class ProcessRunner {", 1, 1),
        ("+", "    public void start(String scriptName) throws Exception {", None, 2),
        ("+", '        ProcessBuilder pb = new ProcessBuilder("sh", "-c", "run.sh " + scriptName);', None, 3),
        ("+", "        pb.start();", None, 4),
        (" ", "    }", 2, 5),
    ])
    findings = analyze_java_file_diff(diff)
    assert len(findings) == 1
    assert findings[0].rule_id == "JV002"
    assert findings[0].start_line == 3


def test_jv002_safe_literal_exec_negative():
    diff = _make_java_diff([
        (" ", "public class SafeCmd {", 1, 1),
        ("+", '    public void runStatic() throws Exception {', None, 2),
        ("+", '        Runtime.getRuntime().exec("uptime");', None, 3),
        ("+", '        ProcessBuilder pb = new ProcessBuilder("ls", "-la");', None, 4),
        (" ", "    }", 2, 5),
    ])
    findings = analyze_java_file_diff(diff)
    assert len(findings) == 0


# --- JV003: SQL Injection Tests ---

def test_jv003_jdbc_execute_query_concatenation_positive():
    diff = _make_java_diff([
        (" ", "public class UserRepository {", 1, 1),
        (" ", "    public void findUser(Statement stmt, String userId) throws Exception {", 2, 2),
        ("+", '        ResultSet rs = stmt.executeQuery("SELECT * FROM users WHERE id = " + userId);', None, 3),
        (" ", "    }", 3, 4),
    ])
    findings = analyze_java_file_diff(diff)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "JV003"
    assert f.start_line == 3
    assert f.source == FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS
    assert f.severity == FindingSeverity.HIGH


def test_jv003_prepare_statement_string_format_positive():
    diff = _make_java_diff([
        (" ", "public class OrderService {", 1, 1),
        ("+", "    public void query(Connection conn, String status) throws Exception {", None, 2),
        ("+", '        String sql = String.format("SELECT * FROM orders WHERE status = \'%s\'", status);', None, 3),
        ("+", "        PreparedStatement ps = conn.prepareStatement(sql);", None, 4),
        (" ", "    }", 2, 5),
    ])
    findings = analyze_java_file_diff(diff)
    assert any(f.rule_id == "JV003" for f in findings)


def test_jv003_parameterized_query_negative():
    diff = _make_java_diff([
        (" ", "public class SafeRepo {", 1, 1),
        ("+", "    public void query(Connection conn, String id) throws Exception {", None, 2),
        ("+", '        PreparedStatement ps = conn.prepareStatement("SELECT * FROM users WHERE id = ?");', None, 3),
        ("+", "        ps.setString(1, id);", None, 4),
        ("+", "        ResultSet rs = ps.executeQuery();", None, 5),
        (" ", "    }", 2, 6),
    ])
    findings = analyze_java_file_diff(diff)
    assert len(findings) == 0


def test_jv003_non_sql_execute_negative():
    diff = _make_java_diff([
        (" ", "public class TaskManager {", 1, 1),
        ("+", "    public void dispatch(Executor executor, Runnable task) {", None, 2),
        ("+", "        executor.execute(task);", None, 3),
        (" ", "    }", 2, 4),
    ])
    findings = analyze_java_file_diff(diff)
    assert len(findings) == 0


# --- JV004: Path Traversal Tests ---

def test_jv004_new_file_concatenation_positive():
    diff = _make_java_diff([
        (" ", "public class FileUploadService {", 1, 1),
        (" ", "    public void save(String baseDir, String userFilename) {", 2, 2),
        ("+", '        File targetFile = new File(baseDir + "/" + userFilename);', None, 3),
        (" ", "    }", 3, 4),
    ])
    findings = analyze_java_file_diff(diff)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "JV004"
    assert f.start_line == 3
    assert f.source == FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS
    assert f.severity == FindingSeverity.MEDIUM


def test_jv004_paths_get_dynamic_positive():
    diff = _make_java_diff([
        (" ", "public class DocumentManager {", 1, 1),
        ("+", "    public Path resolvePath(String baseDir, String userPath) {", None, 2),
        ("+", "        return Paths.get(baseDir, userPath);", None, 3),
        (" ", "    }", 2, 4),
    ])
    findings = analyze_java_file_diff(diff)
    assert len(findings) == 1
    assert findings[0].rule_id == "JV004"
    assert findings[0].start_line == 3


def test_jv004_safe_constant_file_negative():
    diff = _make_java_diff([
        (" ", "public class LoggerSetup {", 1, 1),
        ("+", '    public void init() {', None, 2),
        ("+", '        File logFile = new File("/var/log/application.log");', None, 3),
        ("+", '        Path configPath = Paths.get("/etc/app/config.json");', None, 4),
        (" ", "    }", 2, 5),
    ])
    findings = analyze_java_file_diff(diff)
    assert len(findings) == 0


# --- Line Mapping, Multi-Hunk, Edge Cases ---

def test_java_multi_hunk_line_mapping():
    """Verify exact line numbers are preserved across multiple diff hunks."""
    hunk1_lines = [
        DiffLine(type=LineType.CONTEXT, content="public class Multi {", old_line_number=1, new_line_number=1),
        DiffLine(type=LineType.ADDED, content="    Object o = ois.readObject();", old_line_number=None, new_line_number=2),
    ]
    hunk1 = ParsedHunk(
        old_start=1, old_length=1, new_start=1, new_length=2,
        header="@@ -1,1 +1,2 @@",
        lines=hunk1_lines, added_lines=[2], deleted_lines=[], context_lines=[1],
    )

    hunk2_lines = [
        DiffLine(type=LineType.CONTEXT, content="    public void cmd(String s) throws Exception {", old_line_number=20, new_line_number=21),
        DiffLine(type=LineType.ADDED, content='        Runtime.getRuntime().exec("sh -c " + s);', old_line_number=None, new_line_number=22),
    ]
    hunk2 = ParsedHunk(
        old_start=20, old_length=1, new_start=21, new_length=2,
        header="@@ -20,1 +21,2 @@",
        lines=hunk2_lines, added_lines=[22], deleted_lines=[], context_lines=[21],
    )

    diff = ParsedFileDiff(
        file_path="src/Multi.java",
        status=FileChangeStatus.MODIFIED,
        is_binary=False,
        hunks=[hunk1, hunk2],
        added_lines=[2, 22],
        deleted_lines=[],
    )

    findings = analyze_java_file_diff(diff)
    assert len(findings) == 2
    rule_lines = {f.rule_id: f.start_line for f in findings}
    assert rule_lines == {"JV001": 2, "JV002": 22}


def test_empty_java_diff_handling():
    diff = ParsedFileDiff(
        file_path="src/Empty.java",
        status=FileChangeStatus.MODIFIED,
        is_binary=False,
        hunks=[],
        added_lines=[],
        deleted_lines=[],
    )
    assert analyze_java_file_diff(diff) == []


def test_binary_java_diff_handling():
    diff = ParsedFileDiff(
        file_path="bin/App.class",
        status=FileChangeStatus.MODIFIED,
        is_binary=True,
        hunks=[],
        added_lines=[],
        deleted_lines=[],
    )
    assert analyze_java_file_diff(diff) == []


def test_java_syntax_error_tolerance():
    """Unparseable or broken Java syntax fragments must not crash the analyzer."""
    diff = _make_java_diff([
        ("+", "public void broken( { @@@ !!! &&&", None, 1),
        ("+", "    int x = ;;;", None, 2),
    ])
    findings = analyze_java_file_diff(diff)
    assert findings == []
