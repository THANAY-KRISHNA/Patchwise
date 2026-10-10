"""Git Unified Diff Parser with Exact Line Mapping and Resource Limits."""
import re
from typing import List, Optional, Tuple
from ..core.config import settings
from ..core.errors import ErrorCode, PatchwiseAPIException
from .models import (
    DiffLine,
    FileChangeStatus,
    LineType,
    ParsedDiffResult,
    ParsedFileDiff,
    ParsedHunk,
)

# Regular expression to match standard unified diff hunk headers
HUNK_HEADER_REGEX = re.compile(
    r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@(.*)$"
)


def _determine_status(
    header_block: str, old_path: Optional[str], new_path: Optional[str]
) -> FileChangeStatus:
    if "new file mode" in header_block or old_path == "/dev/null":
        return FileChangeStatus.ADDED
    if "deleted file mode" in header_block or new_path == "/dev/null":
        return FileChangeStatus.DELETED
    if "rename from" in header_block or "similarity index" in header_block:
        return FileChangeStatus.RENAMED
    if "Binary files" in header_block or "GIT binary patch" in header_block:
        return FileChangeStatus.BINARY
    return FileChangeStatus.MODIFIED


def parse_hunks(patch_text: str) -> Tuple[List[ParsedHunk], List[str]]:
    """
    Parse hunk text into structured ParsedHunk objects with exact old and new line tracking.
    Returns (hunks, warnings).
    """
    hunks: List[ParsedHunk] = []
    warnings: List[str] = []

    lines = patch_text.splitlines()
    current_hunk_header = None
    current_hunk_info: Optional[Tuple[int, int, int, int, str]] = None
    current_lines: List[str] = []

    def flush_hunk():
        nonlocal current_hunk_header, current_hunk_info, current_lines
        if not current_hunk_header or not current_hunk_info:
            return

        old_start, old_len, new_start, new_len, header_suffix = current_hunk_info
        parsed_lines: List[DiffLine] = []
        added_lines: List[int] = []
        deleted_lines: List[int] = []
        context_lines: List[int] = []

        curr_old = old_start
        curr_new = new_start

        for raw_line in current_lines:
            if not raw_line:
                # Empty line inside hunk treated as empty context
                parsed_lines.append(
                    DiffLine(type=LineType.CONTEXT, content="", old_line_number=curr_old, new_line_number=curr_new)
                )
                context_lines.append(curr_new)
                curr_old += 1
                curr_new += 1
                continue

            prefix = raw_line[0]
            content = raw_line[1:]

            if prefix == "+":
                parsed_lines.append(
                    DiffLine(type=LineType.ADDED, content=content, old_line_number=None, new_line_number=curr_new)
                )
                added_lines.append(curr_new)
                curr_new += 1
            elif prefix == "-":
                parsed_lines.append(
                    DiffLine(type=LineType.DELETED, content=content, old_line_number=curr_old, new_line_number=None)
                )
                deleted_lines.append(curr_old)
                curr_old += 1
            elif prefix == " ":
                parsed_lines.append(
                    DiffLine(type=LineType.CONTEXT, content=content, old_line_number=curr_old, new_line_number=curr_new)
                )
                context_lines.append(curr_new)
                curr_old += 1
                curr_new += 1
            elif prefix == "\\":
                # Metadata line (e.g. "\ No newline at end of file")
                continue
            else:
                # Malformed line or unexpected prefix; treat as context to avoid losing lines
                parsed_lines.append(
                    DiffLine(type=LineType.CONTEXT, content=raw_line, old_line_number=curr_old, new_line_number=curr_new)
                )
                context_lines.append(curr_new)
                curr_old += 1
                curr_new += 1

        hunk = ParsedHunk(
            old_start=old_start,
            old_length=old_len,
            new_start=new_start,
            new_length=new_len,
            header=current_hunk_header,
            lines=parsed_lines,
            added_lines=added_lines,
            deleted_lines=deleted_lines,
            context_lines=context_lines,
        )
        hunks.append(hunk)

    for line in lines:
        if line.startswith("@@"):
            match = HUNK_HEADER_REGEX.match(line)
            if match:
                flush_hunk()
                try:
                    old_start = int(match.group(1))
                    old_len = int(match.group(2)) if match.group(2) is not None else 1
                    new_start = int(match.group(3))
                    new_len = int(match.group(4)) if match.group(4) is not None else 1
                    header_suffix = match.group(5)
                    current_hunk_header = line
                    current_hunk_info = (old_start, old_len, new_start, new_len, header_suffix)
                    current_lines = []
                except Exception as e:
                    warnings.append(f"Failed to parse hunk header '{line}': {e}")
                    current_hunk_header = None
                    current_hunk_info = None
            else:
                flush_hunk()
                warnings.append(f"Malformed or unsupported hunk header: '{line}'")
                current_hunk_header = None
                current_hunk_info = None
        elif current_hunk_header:
            current_lines.append(line)

    flush_hunk()
    return hunks, warnings


def parse_single_file_patch(
    patch_text: Optional[str],
    filename: str,
    status: Optional[str] = None,
    previous_filename: Optional[str] = None,
) -> ParsedFileDiff:
    """
    Parse a single file patch (as returned by the GitHub pull request files API).
    """
    if not patch_text or not patch_text.strip():
        # Empty patch (binary file, permission change, empty file, or large diff omitted by GitHub)
        is_binary = status == "binary"
        calc_status = FileChangeStatus.BINARY if is_binary else (
            FileChangeStatus(status) if status in [s.value for s in FileChangeStatus] else FileChangeStatus.MODIFIED
        )
        return ParsedFileDiff(
            file_path=filename,
            old_path=previous_filename or filename,
            new_path=filename,
            status=calc_status,
            is_binary=is_binary,
            hunks=[],
            added_lines=[],
            deleted_lines=[],
            context_lines=[],
            patch_chars=0,
        )

    # Check for binary indicator
    is_binary = "Binary files" in patch_text or "GIT binary patch" in patch_text
    if is_binary:
        return ParsedFileDiff(
            file_path=filename,
            old_path=previous_filename or filename,
            new_path=filename,
            status=FileChangeStatus.BINARY,
            is_binary=True,
            hunks=[],
            added_lines=[],
            deleted_lines=[],
            context_lines=[],
            patch_chars=len(patch_text),
        )

    hunks, _ = parse_hunks(patch_text)

    # Aggregate lines across all hunks for easy lookup
    added_lines: List[int] = []
    deleted_lines: List[int] = []
    context_lines: List[int] = []

    for hunk in hunks:
        added_lines.extend(hunk.added_lines)
        deleted_lines.extend(hunk.deleted_lines)
        context_lines.extend(hunk.context_lines)

    calc_status = FileChangeStatus(status) if status in [s.value for s in FileChangeStatus] else FileChangeStatus.MODIFIED

    return ParsedFileDiff(
        file_path=filename,
        old_path=previous_filename or filename,
        new_path=filename,
        status=calc_status,
        is_binary=False,
        hunks=hunks,
        added_lines=sorted(list(set(added_lines))),
        deleted_lines=sorted(list(set(deleted_lines))),
        context_lines=sorted(list(set(context_lines))),
        patch_chars=len(patch_text),
    )


def parse_unified_diff(
    diff_text: str,
    max_patch_chars: Optional[int] = None,
    max_files: Optional[int] = None,
    strict_limits: bool = True,
) -> ParsedDiffResult:
    """
    Parse a full multi-file Git unified diff output.
    Enforces maximum patch character and file count boundaries.
    """
    max_chars = max_patch_chars or settings.MAX_PATCH_CHARS
    max_count = max_files or settings.MAX_FILES_PER_REVIEW

    total_chars = len(diff_text)
    if strict_limits and total_chars > max_chars:
        raise PatchwiseAPIException(
            status_code=400,
            error_code=ErrorCode.PATCH_TOO_LARGE,
            message=f"Diff character size ({total_chars}) exceeds allowed limit ({max_chars}).",
            details={"patch_chars": total_chars, "limit": max_chars},
        )

    warnings: List[str] = []
    if total_chars > max_chars:
        warnings.append(f"Diff character count {total_chars} exceeds limit {max_chars}; partial analysis.")

    # Split diff into per-file chunks
    file_chunks = re.split(r"(^diff --git\s+.+$)", diff_text, flags=re.MULTILINE)
    
    # If no "diff --git" headers, test if it's a single file patch
    if len(file_chunks) <= 1:
        # Check if contains hunk header
        if HUNK_HEADER_REGEX.search(diff_text):
            parsed_file = parse_single_file_patch(diff_text, filename="patch.diff")
            return ParsedDiffResult(
                files=[parsed_file],
                total_files=1,
                total_patch_chars=total_chars,
                is_truncated=False,
                warnings=warnings,
            )
        return ParsedDiffResult(
            files=[],
            total_files=0,
            total_patch_chars=total_chars,
            is_truncated=False,
            warnings=["No diff hunks or file headers found in input."],
        )

    parsed_files: List[ParsedFileDiff] = []
    
    # file_chunks[0] is pre-header text; then alternates [header, content, header, content...]
    i = 1
    while i < len(file_chunks):
        git_header = file_chunks[i].strip()
        body = file_chunks[i + 1] if i + 1 < len(file_chunks) else ""
        i += 2

        # Extract file paths from "diff --git a/path b/path"
        git_match = re.match(r"^diff --git a/(.*?)\s+b/(.*)$", git_header)
        if git_match:
            old_path = git_match.group(1).strip()
            new_path = git_match.group(2).strip()
        else:
            old_path = None
            new_path = None

        full_block = git_header + "\n" + body
        status = _determine_status(full_block, old_path, new_path)
        is_binary = status == FileChangeStatus.BINARY

        active_path = new_path or old_path or "unknown_file"
        if new_path == "/dev/null":
            active_path = old_path or "deleted_file"

        if is_binary:
            parsed_files.append(
                ParsedFileDiff(
                    file_path=active_path,
                    old_path=old_path,
                    new_path=new_path,
                    status=FileChangeStatus.BINARY,
                    is_binary=True,
                    hunks=[],
                    added_lines=[],
                    deleted_lines=[],
                    context_lines=[],
                    patch_chars=len(full_block),
                )
            )
            continue

        hunks, hunk_warns = parse_hunks(body)
        warnings.extend(hunk_warns)

        added_lines: List[int] = []
        deleted_lines: List[int] = []
        context_lines: List[int] = []
        for h in hunks:
            added_lines.extend(h.added_lines)
            deleted_lines.extend(h.deleted_lines)
            context_lines.extend(h.context_lines)

        parsed_files.append(
            ParsedFileDiff(
                file_path=active_path,
                old_path=old_path,
                new_path=new_path,
                status=status,
                is_binary=False,
                hunks=hunks,
                added_lines=sorted(list(set(added_lines))),
                deleted_lines=sorted(list(set(deleted_lines))),
                context_lines=sorted(list(set(context_lines))),
                patch_chars=len(full_block),
            )
        )

    is_truncated = False
    if len(parsed_files) > max_count:
        if strict_limits:
            raise PatchwiseAPIException(
                status_code=400,
                error_code=ErrorCode.PATCH_TOO_LARGE,
                message=f"Diff file count ({len(parsed_files)}) exceeds allowed limit ({max_count}).",
                details={"file_count": len(parsed_files), "limit": max_count},
            )
        else:
            parsed_files = parsed_files[:max_count]
            is_truncated = True
            warnings.append(f"PR contains more than {max_count} files. Truncated to first {max_count} files.")

    return ParsedDiffResult(
        files=parsed_files,
        total_files=len(parsed_files),
        total_patch_chars=total_chars,
        is_truncated=is_truncated,
        warnings=warnings,
    )
