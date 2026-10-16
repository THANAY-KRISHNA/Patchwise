"""Unit tests for the BaseLanguageAnalyzer plugin architecture."""
from typing import List
from src.analyzer.base import (
    BaseLanguageAnalyzer,
    CandidateFinding,
    DiffHunk,
    LanguageReadiness,
    TestRecommendation,
)
from src.analyzer.registry import LanguagePluginRegistry
from src.schemas.findings import FindingCategory, FindingProvenance, FindingSeverity


class MockPythonAnalyzer(BaseLanguageAnalyzer):
    @property
    def language_id(self) -> str:
        return "python"

    @property
    def name(self) -> str:
        return "Python"

    @property
    def supported_extensions(self) -> List[str]:
        return [".py"]

    @property
    def readiness_status(self) -> LanguageReadiness:
        return LanguageReadiness.IMPLEMENTED_AND_TESTED

    def run_deterministic_checks(
        self, file_path: str, diff_hunks: List[DiffHunk]
    ) -> List[CandidateFinding]:
        return [
            CandidateFinding(
                rule_id="PY001",
                source=FindingProvenance.DETERMINISTIC_STATIC_ANALYSIS,
                severity=FindingSeverity.MEDIUM,
                category=FindingCategory.INPUT_VALIDATION,
                file_path=file_path,
                start_line=10,
                end_line=10,
                title="Mock check",
                explanation="Mock explanation",
            )
        ]

    def get_language_prompt_context(self) -> str:
        return "Python security rules."

    def suggest_tests(
        self, file_path: str, diff_hunks: List[DiffHunk]
    ) -> List[TestRecommendation]:
        return [TestRecommendation(rationale="Check boundary values")]


def test_plugin_registration_and_lookup():
    registry = LanguagePluginRegistry()
    mock_plugin = MockPythonAnalyzer()

    # Register plugin
    registry.register(mock_plugin)

    # Lookup by extension
    analyzer = registry.get_analyzer_for_file("app/main.py")
    assert analyzer is not None
    assert analyzer.language_id == "python"
    assert analyzer.readiness_status == LanguageReadiness.IMPLEMENTED_AND_TESTED

    # Unknown extension returns None
    assert registry.get_analyzer_for_file("app/main.rs") is None

    # Status overview accurately reports declared status
    overview = registry.get_status_overview()
    assert len(overview) == 1
    assert overview[0]["readiness_status"] == "IMPLEMENTED_AND_TESTED"


def test_global_plugin_registry_has_python_and_javascript():
    from src.analyzer.registry import plugin_registry

    # Python
    py_analyzer = plugin_registry.get_analyzer_for_file("server/main.py")
    assert py_analyzer is not None
    assert py_analyzer.language_id == "python"
    assert py_analyzer.readiness_status == LanguageReadiness.IMPLEMENTED_AND_TESTED

    # JavaScript / TypeScript extensions
    for path in ["src/index.js", "src/Component.jsx", "src/service.ts", "src/App.tsx"]:
        js_analyzer = plugin_registry.get_analyzer_for_file(path)
        assert js_analyzer is not None
        assert js_analyzer.language_id == "javascript"
        assert js_analyzer.readiness_status == LanguageReadiness.IMPLEMENTED_AND_TESTED

    # Java extension
    java_analyzer = plugin_registry.get_analyzer_for_file("src/main/java/com/example/App.java")
    assert java_analyzer is not None
    assert java_analyzer.language_id == "java"
    assert java_analyzer.readiness_status == LanguageReadiness.IMPLEMENTED_AND_TESTED

    # C and C++ extensions
    for path in ["src/main.c", "include/header.h", "src/core.cc", "src/engine.cpp", "src/util.cxx", "include/core.hh", "include/app.hpp", "include/types.hxx"]:
        cpp_analyzer = plugin_registry.get_analyzer_for_file(path)
        assert cpp_analyzer is not None
        assert cpp_analyzer.language_id == "cpp"
        assert cpp_analyzer.readiness_status == LanguageReadiness.IMPLEMENTED_AND_TESTED

    # SQL and HiveQL extensions
    for path in ["migrations/001.sql", "etl/pipeline.hql", "analytics/metrics.hive", "queries/report.q"]:
        sql_analyzer = plugin_registry.get_analyzer_for_file(path)
        assert sql_analyzer is not None
        assert sql_analyzer.language_id == "sql"
        assert sql_analyzer.readiness_status == LanguageReadiness.IMPLEMENTED_AND_TESTED

