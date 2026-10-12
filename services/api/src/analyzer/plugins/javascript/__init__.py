"""JavaScript and TypeScript analyzer plugin package."""
from .analyzer import JavaScriptLanguageAnalyzer
from .rules import analyze_javascript_file_diff

__all__ = ["JavaScriptLanguageAnalyzer", "analyze_javascript_file_diff"]
