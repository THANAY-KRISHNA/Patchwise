"""Typed Data Models for Parsed Diff Hunks and Lines."""
from enum import Enum
from typing import List, Optional, Set
from pydantic import BaseModel, Field


class LineType(str, Enum):
    ADDED = "+"
    DELETED = "-"
    CONTEXT = " "


class DiffLine(BaseModel):
    """Represents a single parsed line in a diff hunk."""
    type: LineType
    content: str
    old_line_number: Optional[int] = Field(
        None, description="Line number in the base/old file (None if added line)"
    )
    new_line_number: Optional[int] = Field(
        None, description="Line number in the head/new file (None if deleted line)"
    )


class ParsedHunk(BaseModel):
    """Represents a contiguous diff hunk with old/new coordinate bounds."""
    old_start: int
    old_length: int
    new_start: int
    new_length: int
    header: str
    lines: List[DiffLine]
    added_lines: List[int] = Field(
        default_factory=list,
        description="List of 1-indexed line numbers added or modified in the new file",
    )
    deleted_lines: List[int] = Field(
        default_factory=list,
        description="List of 1-indexed line numbers deleted from the old file",
    )
    context_lines: List[int] = Field(
        default_factory=list,
        description="List of 1-indexed line numbers appearing as unchanged context in the new file",
    )


class FileChangeStatus(str, Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"
    BINARY = "binary"
    UNCHANGED = "unchanged"


class ParsedFileDiff(BaseModel):
    """Represents the parsed diff and line mapping for a single file."""
    file_path: str
    old_path: Optional[str] = None
    new_path: Optional[str] = None
    status: FileChangeStatus
    is_binary: bool = False
    hunks: List[ParsedHunk] = Field(default_factory=list)
    added_lines: List[int] = Field(
        default_factory=list,
        description="All added or modified line numbers in the new file",
    )
    deleted_lines: List[int] = Field(
        default_factory=list,
        description="All deleted line numbers in the old file",
    )
    context_lines: List[int] = Field(
        default_factory=list,
        description="All context line numbers visible in the new file",
    )
    patch_chars: int = 0


class ParsedDiffResult(BaseModel):
    """Aggregated parsed result across all changed files in a pull request."""
    files: List[ParsedFileDiff]
    total_files: int
    total_patch_chars: int
    is_truncated: bool = False
    warnings: List[str] = Field(default_factory=list)
