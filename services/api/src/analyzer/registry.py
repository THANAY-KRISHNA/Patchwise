"""Plugin Registry for Multi-Language Analyzers."""
import os
from typing import Dict, List, Optional
from .base import BaseLanguageAnalyzer, CandidateFinding, DiffHunk, LanguageReadiness, TestRecommendation
from .plugins.javascript.analyzer import JavaScriptLanguageAnalyzer
from .plugins.python.analyzer import PythonLanguageAnalyzer


class PlannedLanguageAnalyzerPlaceholder(BaseLanguageAnalyzer):
    """Placeholder analyzer representing planned languages in the plugin architecture."""

    def __init__(self, language_id: str, name: str, extensions: List[str]):
        self._language_id = language_id
        self._name = name
        self._extensions = extensions

    @property
    def language_id(self) -> str:
        return self._language_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def supported_extensions(self) -> List[str]:
        return self._extensions

    @property
    def readiness_status(self) -> LanguageReadiness:
        return LanguageReadiness.PLANNED_FRAMEWORK_READY

    def run_deterministic_checks(
        self, file_path: str, diff_hunks: List[DiffHunk]
    ) -> List[CandidateFinding]:
        return []

    def get_language_prompt_context(self) -> str:
        return f"{self._name} static analysis rules currently in development."

    def suggest_tests(
        self, file_path: str, diff_hunks: List[DiffHunk]
    ) -> List[TestRecommendation]:
        return []


class LanguagePluginRegistry:
    """Central registry for discovering and dispatching language analyzers."""

    def __init__(self):
        self._plugins: Dict[str, BaseLanguageAnalyzer] = {}
        self._extension_map: Dict[str, BaseLanguageAnalyzer] = {}

    def register(self, plugin: BaseLanguageAnalyzer) -> None:
        """Register a new language analyzer plugin."""
        self._plugins[plugin.language_id] = plugin
        for ext in plugin.supported_extensions:
            self._extension_map[ext.lower()] = plugin

    def get_analyzer_for_file(self, file_path: str) -> Optional[BaseLanguageAnalyzer]:
        """Look up the appropriate analyzer by file extension."""
        _, ext = os.path.splitext(file_path)
        return self._extension_map.get(ext.lower())

    def get_analyzer(self, language_id: str) -> Optional[BaseLanguageAnalyzer]:
        """Look up analyzer by language ID."""
        lid = language_id.lower()
        if lid in ("typescript", "ts", "javascript", "js"):
            return self._plugins.get("javascript") or self._plugins.get("typescript")
        return self._plugins.get(lid)

    def list_all(self) -> List[BaseLanguageAnalyzer]:
        """Return all registered plugins."""
        return list(self._plugins.values())

    def get_status_overview(self) -> List[Dict[str, str]]:
        """
        Return public status report of all plugins, strictly enforcing truth-in-advertising.
        """
        return [
            {
                "language_id": p.language_id,
                "name": p.name,
                "supported_extensions": ", ".join(p.supported_extensions),
                "readiness_status": p.readiness_status.value,
            }
            for p in self._plugins.values()
        ]


# Singleton global registry instance
plugin_registry = LanguagePluginRegistry()

# Register Active & Tested Plugins (Python in Milestone 3, JavaScript/TypeScript in Milestone 7A)
plugin_registry.register(PythonLanguageAnalyzer())
plugin_registry.register(JavaScriptLanguageAnalyzer())

# Register Planned / Framework-Ready Plugins
plugin_registry.register(
    PlannedLanguageAnalyzerPlaceholder(
        language_id="java",
        name="Java",
        extensions=[".java"],
    )
)
plugin_registry.register(
    PlannedLanguageAnalyzerPlaceholder(
        language_id="cpp",
        name="C / C++",
        extensions=[".c", ".cpp", ".h", ".hpp"],
    )
)
plugin_registry.register(
    PlannedLanguageAnalyzerPlaceholder(
        language_id="sql",
        name="SQL / HiveQL",
        extensions=[".sql", ".hql"],
    )
)
plugin_registry.register(
    PlannedLanguageAnalyzerPlaceholder(
        language_id="spark",
        name="PySpark / Scala",
        extensions=[".scala"],
    )
)
