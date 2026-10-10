'use client';

import React, { useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  FileCode,
  AlertCircle,
} from 'lucide-react';
import { Finding, ParsedFileDiff } from '../types';
import { FindingCard } from './FindingCard';

interface DiffViewerProps {
  files: ParsedFileDiff[];
  findings: Finding[];
  reviewId: string;
}

export const DiffViewer: React.FC<DiffViewerProps> = ({
  files,
  findings,
  reviewId,
}) => {
  // Track open/collapsed state of files
  const [collapsedFiles, setCollapsedFiles] = useState<Record<string, boolean>>({});

  const toggleFile = (path: string) => {
    setCollapsedFiles((prev) => ({
      ...prev,
      [path]: !prev[path],
    }));
  };

  if (!files || files.length === 0) {
    return (
      <div className="rounded-lg border border-[#262c36] bg-[#14171d] p-8 text-center text-[#8b949e]">
        <FileCode className="mx-auto h-8 w-8 mb-2 text-[#6e7681]" />
        <p className="text-sm font-medium">No changed files found in this diff.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {files.map((file) => {
        const isCollapsed = !!collapsedFiles[file.file_path];
        // Findings belonging to this file
        const fileFindings = findings.filter((f) => f.file_path === file.file_path);

        // Grounded findings (have a start_line that exists in added_lines or hunks)
        const allNewLinesInHunks = new Set(
          file.hunks.flatMap((h) =>
            h.lines.map((l) => l.new_line_number).filter((n): n is number => n !== null && n !== undefined)
          )
        );

        const ungroundedFindings = fileFindings.filter(
          (f) => f.start_line === null || !allNewLinesInHunks.has(f.start_line)
        );

        return (
          <div
            key={file.file_path}
            className="overflow-hidden rounded-lg border border-[#262c36] bg-[#14171d]"
          >
            {/* File Header */}
            <div
              onClick={() => toggleFile(file.file_path)}
              className="flex cursor-pointer items-center justify-between border-b border-[#262c36] bg-[#1a1e26] px-4 py-2.5 transition hover:bg-[#202530]"
            >
              <div className="flex items-center gap-2">
                {isCollapsed ? (
                  <ChevronRight className="h-4 w-4 text-[#8b949e]" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-[#8b949e]" />
                )}
                <FileCode className="h-4 w-4 text-blue-400" />
                <span className="font-mono text-xs font-semibold text-white">
                  {file.file_path}
                </span>

                {file.is_new_file && (
                  <span className="rounded bg-emerald-500/20 px-1.5 py-0.5 text-[10px] font-medium text-emerald-300">
                    NEW
                  </span>
                )}
                {file.is_deleted_file && (
                  <span className="rounded bg-red-500/20 px-1.5 py-0.5 text-[10px] font-medium text-red-300">
                    DELETED
                  </span>
                )}
                {file.is_renamed_file && (
                  <span className="rounded bg-purple-500/20 px-1.5 py-0.5 text-[10px] font-medium text-purple-300">
                    RENAMED
                  </span>
                )}
                {file.is_binary && (
                  <span className="rounded bg-zinc-500/20 px-1.5 py-0.5 text-[10px] font-medium text-zinc-300">
                    BINARY
                  </span>
                )}
              </div>

              <div className="flex items-center gap-3 text-xs">
                {fileFindings.length > 0 && (
                  <span className="flex items-center gap-1 rounded bg-red-500/10 px-2 py-0.5 text-xs font-medium text-red-400 border border-red-500/20">
                    <AlertCircle className="h-3 w-3" />
                    {fileFindings.length} {fileFindings.length === 1 ? 'Finding' : 'Findings'}
                  </span>
                )}
                <div className="flex items-center gap-2 font-mono text-xs">
                  <span className="text-emerald-400">+{file.added_lines.length}</span>
                  <span className="text-red-400">-{file.deleted_lines.length}</span>
                </div>
              </div>
            </div>

            {/* Uncollapsed File Content */}
            {!isCollapsed && (
              <div className="flex flex-col">
                {/* File-level or ungrounded findings notice */}
                {ungroundedFindings.length > 0 && (
                  <div className="border-b border-[#262c36] bg-[#12141a] p-4">
                    <div className="mb-2 text-xs font-semibold text-amber-400">
                      File-Level / Unanchored Recommendations ({ungroundedFindings.length})
                    </div>
                    <div className="flex flex-col gap-3">
                      {ungroundedFindings.map((f) => (
                        <FindingCard
                          key={f.id}
                          finding={f}
                          reviewId={reviewId}
                          isAnchoredInDiff={false}
                        />
                      ))}
                    </div>
                  </div>
                )}

                {/* Hunk Lines */}
                {file.hunks.map((hunk, hIdx) => (
                  <div key={hIdx} className="border-b border-[#20252e] last:border-b-0">
                    {/* Hunk Header */}
                    <div className="bg-[#12151c] px-4 py-1 font-mono text-[11px] text-[#6e7681] border-y border-[#20252e]">
                      {hunk.header}
                    </div>

                    {/* Diff Lines Table */}
                    <div className="overflow-x-auto font-mono text-xs">
                      {hunk.lines.map((line, lIdx) => {
                        const isAdded = line.type === '+';
                        const isDeleted = line.type === '-';

                        // Find line-level findings matching this new line
                        const matchingFindings = line.new_line_number
                          ? fileFindings.filter(
                              (f) =>
                                f.start_line !== null &&
                                f.start_line === line.new_line_number
                            )
                          : [];

                        return (
                          <React.Fragment key={lIdx}>
                            <div
                              className={`flex items-start transition hover:bg-[#1a202a] ${
                                isAdded
                                  ? 'bg-emerald-950/20 text-emerald-200'
                                  : isDeleted
                                  ? 'bg-red-950/20 text-red-300'
                                  : 'text-[#c9d1d9]'
                              }`}
                            >
                              {/* Old Line # */}
                              <div className="w-12 flex-shrink-0 select-none px-2 py-0.5 text-right text-[11px] text-[#484f58] border-r border-[#20252e]">
                                {line.old_line_number ?? ''}
                              </div>

                              {/* New Line # */}
                              <div className="w-12 flex-shrink-0 select-none px-2 py-0.5 text-right text-[11px] text-[#484f58] border-r border-[#20252e]">
                                {line.new_line_number ?? ''}
                              </div>

                              {/* Sign (+, -, ' ') */}
                              <div className="w-6 flex-shrink-0 select-none text-center py-0.5 text-[#6e7681]">
                                {line.type}
                              </div>

                              {/* Content */}
                              <div className="flex-1 whitespace-pre px-2 py-0.5 overflow-x-auto">
                                {line.content}
                              </div>
                            </div>

                            {/* Inline Anchored Finding Cards */}
                            {matchingFindings.length > 0 && (
                              <div className="bg-[#101217] px-6 py-3 border-y border-amber-500/30">
                                <div className="text-[11px] font-semibold text-amber-400 mb-2">
                                  Anchored Finding on Line {line.new_line_number}:
                                </div>
                                <div className="flex flex-col gap-3">
                                  {matchingFindings.map((f) => (
                                    <FindingCard
                                      key={f.id}
                                      finding={f}
                                      reviewId={reviewId}
                                      isAnchoredInDiff={true}
                                    />
                                  ))}
                                </div>
                              </div>
                            )}
                          </React.Fragment>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
