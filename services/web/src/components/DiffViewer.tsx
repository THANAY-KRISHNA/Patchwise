'use client';

import React, { useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  FileCode,
  AlertCircle,
  Minimize2,
  Maximize2,
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
  const [collapsedFiles, setCollapsedFiles] = useState<Record<string, boolean>>({});

  const toggleFile = (path: string) => {
    setCollapsedFiles((prev) => ({
      ...prev,
      [path]: !prev[path],
    }));
  };

  const handleCollapseAll = () => {
    const allCollapsed: Record<string, boolean> = {};
    files.forEach((f) => {
      allCollapsed[f.file_path] = true;
    });
    setCollapsedFiles(allCollapsed);
  };

  const handleExpandAll = () => {
    setCollapsedFiles({});
  };

  if (!files || files.length === 0) {
    return (
      <div className="rounded border border-[#1e222b] bg-[#101217] p-8 text-center text-[#949da8]">
        <FileCode className="mx-auto h-8 w-8 mb-2 text-[#656e7b]" />
        <p className="text-xs font-medium font-mono">No changed files found in this diff.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      {/* Diff Controls Header */}
      <div className="flex items-center justify-between text-xs font-mono text-[#656e7b]">
        <span>Showing {files.length} changed {files.length === 1 ? 'file' : 'files'}</span>
        <div className="flex items-center gap-3">
          <button
            onClick={handleExpandAll}
            className="flex items-center gap-1 hover:text-[#f0f3f6] transition"
          >
            <Maximize2 className="h-3 w-3" />
            <span>Expand All</span>
          </button>
          <button
            onClick={handleCollapseAll}
            className="flex items-center gap-1 hover:text-[#f0f3f6] transition"
          >
            <Minimize2 className="h-3 w-3" />
            <span>Collapse All</span>
          </button>
        </div>
      </div>

      {files.map((file) => {
        const isCollapsed = !!collapsedFiles[file.file_path];
        const fileFindings = findings.filter((f) => f.file_path === file.file_path);

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
            className="overflow-hidden rounded border border-[#1e222b] bg-[#101217]"
          >
            {/* File Header */}
            <div
              onClick={() => toggleFile(file.file_path)}
              className="flex cursor-pointer items-center justify-between border-b border-[#1e222b] bg-[#14161f] px-4 py-2.5 transition hover:bg-[#181a24]"
            >
              <div className="flex items-center gap-2">
                {isCollapsed ? (
                  <ChevronRight className="h-4 w-4 text-[#949da8]" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-[#949da8]" />
                )}
                <FileCode className="h-4 w-4 text-amber-400" />
                <span className="font-mono text-xs font-semibold text-[#f0f3f6]">
                  {file.file_path}
                </span>

                {file.is_new_file && (
                  <span className="rounded bg-emerald-500/20 px-1.5 py-0.2 font-mono text-[10px] font-medium text-emerald-300">
                    NEW
                  </span>
                )}
                {file.is_deleted_file && (
                  <span className="rounded bg-red-500/20 px-1.5 py-0.2 font-mono text-[10px] font-medium text-red-300">
                    DELETED
                  </span>
                )}
                {file.is_renamed_file && (
                  <span className="rounded bg-purple-500/20 px-1.5 py-0.2 font-mono text-[10px] font-medium text-purple-300">
                    RENAMED
                  </span>
                )}
                {file.is_binary && (
                  <span className="rounded bg-zinc-500/20 px-1.5 py-0.2 font-mono text-[10px] font-medium text-zinc-300">
                    BINARY
                  </span>
                )}
              </div>

              <div className="flex items-center gap-3 text-xs font-mono">
                {fileFindings.length > 0 && (
                  <span className="flex items-center gap-1 rounded bg-red-500/10 px-2 py-0.5 text-[11px] font-medium text-red-400 border border-red-500/20">
                    <AlertCircle className="h-3 w-3" />
                    {fileFindings.length} {fileFindings.length === 1 ? 'finding' : 'findings'}
                  </span>
                )}
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-emerald-400">+{file.added_lines.length}</span>
                  <span className="text-red-400">-{file.deleted_lines.length}</span>
                </div>
              </div>
            </div>

            {/* Uncollapsed File Content */}
            {!isCollapsed && (
              <div className="flex flex-col">
                {/* File-level / ungrounded findings */}
                {ungroundedFindings.length > 0 && (
                  <div className="border-b border-[#1e222b] bg-[#0c0d11] p-4">
                    <div className="mb-2 text-xs font-semibold text-amber-400 font-mono">
                      File-Level Recommendations ({ungroundedFindings.length})
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
                  <div key={hIdx} className="border-b border-[#1e222b] last:border-b-0">
                    {/* Hunk Header */}
                    <div className="bg-[#0b0c10] px-4 py-1 font-mono text-[11px] text-[#656e7b] border-y border-[#1e222b]">
                      {hunk.header}
                    </div>

                    {/* Diff Lines Table */}
                    <div className="overflow-x-auto font-mono text-xs">
                      {hunk.lines.map((line, lIdx) => {
                        const isAdded = line.type === '+';
                        const isDeleted = line.type === '-';

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
                              className={`flex items-start transition hover:bg-[#161820] ${
                                isAdded
                                  ? 'bg-emerald-950/20 text-emerald-200'
                                  : isDeleted
                                  ? 'bg-red-950/20 text-red-300'
                                  : 'text-[#d0d7de]'
                              }`}
                            >
                              {/* Old Line # */}
                              <div className="w-12 flex-shrink-0 select-none px-2 py-0.5 text-right text-[11px] text-[#484f58] border-r border-[#1e222b]">
                                {line.old_line_number ?? ''}
                              </div>

                              {/* New Line # */}
                              <div className="w-12 flex-shrink-0 select-none px-2 py-0.5 text-right text-[11px] text-[#484f58] border-r border-[#1e222b]">
                                {line.new_line_number ?? ''}
                              </div>

                              {/* Sign (+, -, ' ') */}
                              <div className="w-6 flex-shrink-0 select-none text-center py-0.5 text-[#656e7b]">
                                {line.type}
                              </div>

                              {/* Content */}
                              <div className="flex-1 whitespace-pre px-2 py-0.5 overflow-x-auto">
                                {line.content}
                              </div>
                            </div>

                            {/* Inline Anchored Finding Cards */}
                            {matchingFindings.length > 0 && (
                              <div className="bg-[#0c0e12] px-6 py-3 border-y border-amber-500/40">
                                <div className="text-[11px] font-semibold text-amber-400 mb-2 font-mono">
                                  Anchored Finding on Line {line.new_line_number}:
                                </div>
                                <div className="space-y-3">
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
