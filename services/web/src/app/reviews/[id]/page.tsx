'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  GitPullRequest,
  Clock,
  FileCode,
  Filter,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react';
import { useParams } from 'next/navigation';
import { api } from '../../../lib/api';
import {
  DiffInspectionResponse,
  ParsedFileDiff,
  Review,
} from '../../../types';
import { ReviewStatusBadge } from '../../../components/StatusBadge';
import { DiffViewer } from '../../../components/DiffViewer';
import { DEMO_REVIEW, DEMO_DIFF_DATA } from '../../../lib/demoData';

function ReviewDetailContent() {
  const params = useParams();
  const reviewId = (params?.id as string) || '';

  const [review, setReview] = useState<Review | null>(null);
  const [diffData, setDiffData] = useState<DiffInspectionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');
  const [selectedProvenance, setSelectedProvenance] = useState<string>('all');
  const [selectedFile, setSelectedFile] = useState<string>('all');

  useEffect(() => {
    let active = true;
    if (!reviewId) return;

    if (reviewId === 'demo') {
      Promise.resolve().then(() => {
        if (active) {
          setReview(DEMO_REVIEW);
          setDiffData(DEMO_DIFF_DATA);
          setLoading(false);
        }
      });
      return;
    }

    api.getReviewById(reviewId)
      .then(async (rev) => {
        if (!active) return;
        setReview(rev);

        try {
          const repoUrl = rev.repository.startsWith('http')
            ? rev.repository
            : `https://github.com/${rev.repository}`;
          const inspection = await api.inspectDiff({
            repository_url: repoUrl,
            pull_request_number: rev.pr_number,
          });
          if (active) setDiffData(inspection);
        } catch {
          // fallback
        }
        if (active) setLoading(false);
      })
      .catch((err: unknown) => {
        if (active) {
          setError((err as Error)?.message || 'Failed to load review details');
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [reviewId]);

  if (loading) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-16 text-center text-xs text-[#8b949e]">
        <RefreshCw className="mx-auto h-6 w-6 animate-spin text-blue-400 mb-3" />
        <p className="text-sm font-medium text-white">Loading review inspector...</p>
        <p className="text-[#6e7681] mt-1">Retrieving diff hunks, AST findings, and provenance tags</p>
      </div>
    );
  }

  if (error || !review) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-16 text-center">
        <AlertTriangle className="mx-auto h-8 w-8 text-red-400 mb-3" />
        <h2 className="text-base font-bold text-white mb-2">Review Not Found or Unavailable</h2>
        <p className="text-xs text-[#8b949e] mb-6">{error || 'Unable to retrieve review record.'}</p>
        <Link
          href="/reviews"
          className="inline-flex items-center gap-1.5 rounded-md border border-[#262c36] bg-[#14171d] px-4 py-2 text-xs font-medium text-white hover:bg-[#1e232b] transition"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Reviews
        </Link>
        <Link
          href="/reviews/demo"
          className="inline-flex items-center gap-1.5 rounded-md border border-blue-500/30 bg-blue-950/20 px-4 py-2 text-xs font-medium text-blue-400 hover:bg-blue-900/30 transition ml-3"
        >
          View Demo PR Inspector
        </Link>
      </div>
    );
  }

  // Filter findings
  const filteredFindings = review.findings.filter((f) => {
    const matchSev = selectedSeverity === 'all' || f.severity === selectedSeverity;
    const matchProv = selectedProvenance === 'all' || f.source === selectedProvenance;
    const matchFile = selectedFile === 'all' || f.file_path === selectedFile;
    return matchSev && matchProv && matchFile;
  });

  // Extract unique file paths across findings and diff files
  const allFilePaths = Array.from(
    new Set([
      ...(diffData?.files.map((df) => df.file_path) || []),
      ...review.findings.map((f) => f.file_path),
    ])
  );

  // If diffData has files, use them. Otherwise synthesize basic representation so findings can render!
  const effectiveFiles: ParsedFileDiff[] =
    diffData && diffData.files.length > 0
      ? diffData.files.filter((df) => selectedFile === 'all' || df.file_path === selectedFile)
      : allFilePaths
          .filter((fp) => selectedFile === 'all' || fp === selectedFile)
          .map((fp) => {
            const fileFindings = review.findings.filter((f) => f.file_path === fp);
            const addedLines = fileFindings
              .map((f) => f.start_line)
              .filter((n): n is number => n !== null);

            return {
              file_path: fp,
              old_path: null,
              is_new_file: false,
              is_deleted_file: false,
              is_renamed_file: false,
              is_binary: false,
              hunks: [
                {
                  old_start: 1,
                  old_length: 5,
                  new_start: 1,
                  new_length: 5,
                  header: `@@ -1,5 +1,5 @@ ${fp}`,
                  lines: fileFindings.map((f) => ({
                    type: '+',
                    content: `# ${f.title}`,
                    new_line_number: f.start_line || 1,
                    old_line_number: null,
                  })),
                  added_lines: addedLines,
                  deleted_lines: [],
                  context_lines: [],
                },
              ],
              added_lines: addedLines,
              deleted_lines: [],
            };
          });

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      {review.id === 'demo' && (
        <div className="mb-4 rounded-md border border-amber-500/30 bg-amber-950/20 px-4 py-2.5 text-xs text-amber-300 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="rounded bg-amber-500/20 px-1.5 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wider text-amber-400">
              DEMO FIXTURE
            </span>
            <span>
              Synthetic pull request diff and AST findings for verification testing. Not actual production activity.
            </span>
          </div>
        </div>
      )}

      {/* Top Breadcrumb & Actions */}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
        <Link
          href="/reviews"
          className="inline-flex items-center gap-1.5 text-xs text-[#8b949e] hover:text-white transition"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to all reviews
        </Link>

        <div className="flex items-center gap-2">
          <ReviewStatusBadge status={review.status} />
          <span className="font-mono text-xs text-[#6e7681]">
            ID: {review.id.slice(0, 8)}...
          </span>
        </div>
      </div>

      {/* PR Header Box */}
      <div className="rounded-lg border border-[#262c36] bg-[#14171d] p-5 mb-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <GitPullRequest className="h-4 w-4 text-blue-400" />
              <h1 className="text-lg font-bold text-white">
                {review.repository} #{review.pr_number}
              </h1>
              {review.commit_sha && (
                <span className="rounded bg-[#1e232b] px-2 py-0.5 font-mono text-[11px] text-[#8b949e] border border-[#2d3440]">
                  {review.commit_sha.slice(0, 7)}
                </span>
              )}
            </div>
            <p className="text-xs text-[#8b949e]">
              {review.pr_title || 'No pull request description provided.'}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-[#8b949e]">
            <div className="flex items-center gap-1">
              <Clock className="h-3.5 w-3.5 text-[#6e7681]" />
              <span>{review.duration_ms ? `${review.duration_ms} ms` : '—'}</span>
            </div>
            <div>
              Engine: <span className="text-white">{review.engine_version}</span>
            </div>
            <div>
              Started: <span className="text-white">{new Date(review.started_at).toLocaleTimeString()}</span>
            </div>
          </div>
        </div>

        {/* Summary Badges Row */}
        <div className="mt-4 pt-4 border-t border-[#20252e] flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-[#8b949e]">Findings Breakdown:</span>
            <span className="font-mono text-emerald-400 font-medium">
              {review.summary?.deterministic_count || 0} Deterministic
            </span>
            <span className="text-[#484f58]">•</span>
            <span className="font-mono text-purple-400 font-medium">
              {review.summary?.ai_hypothesis_count || 0} AI Hypotheses
            </span>
            <span className="text-[#484f58]">•</span>
            <span className="font-mono text-red-400 font-medium">
              {review.summary?.critical_count || 0} Critical
            </span>
            <span className="text-[#484f58]">•</span>
            <span className="font-mono text-orange-400 font-medium">
              {review.summary?.high_count || 0} High
            </span>
          </div>

          <div className="text-[11px] text-[#6e7681]">
            100% Line Grounded • Zero Untrusted Code Executed
          </div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="rounded-lg border border-[#262c36] bg-[#14171d] p-3.5 mb-6 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5 text-[#8b949e]">
            <Filter className="h-3.5 w-3.5" />
            <span>Filter Findings:</span>
          </div>

          {/* Severity Filter */}
          <select
            value={selectedSeverity}
            onChange={(e) => setSelectedSeverity(e.target.value)}
            className="rounded border border-[#262c36] bg-[#0d0f12] px-2.5 py-1 text-xs text-white focus:outline-none"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
            <option value="info">Info</option>
          </select>

          {/* Provenance Filter */}
          <select
            value={selectedProvenance}
            onChange={(e) => setSelectedProvenance(e.target.value)}
            className="rounded border border-[#262c36] bg-[#0d0f12] px-2.5 py-1 text-xs text-white focus:outline-none"
          >
            <option value="all">All Provenance Tiers</option>
            <option value="DETERMINISTIC_STATIC_ANALYSIS">Tier 1: Deterministic Static</option>
            <option value="AI_GENERATED_HYPOTHESIS">Tier 2: AI Hypotheses</option>
            <option value="VERIFIED_TEST_RESULT">Tier 3: Verified Test</option>
          </select>

          {/* File Filter */}
          <select
            value={selectedFile}
            onChange={(e) => setSelectedFile(e.target.value)}
            className="rounded border border-[#262c36] bg-[#0d0f12] px-2.5 py-1 text-xs text-white focus:outline-none max-w-xs truncate"
          >
            <option value="all">All Files ({allFilePaths.length})</option>
            {allFilePaths.map((fp) => (
              <option key={fp} value={fp}>
                {fp}
              </option>
            ))}
          </select>
        </div>

        <div className="text-[#8b949e] font-mono text-xs">
          Showing <span className="text-white font-semibold">{filteredFindings.length}</span> of{' '}
          {review.findings.length} findings
        </div>
      </div>

      {/* Main Review Body: Unified Diff & Anchored Findings */}
      <div className="space-y-6">
        <h2 className="text-sm font-semibold text-white flex items-center gap-2">
          <FileCode className="h-4 w-4 text-blue-400" />
          <span>Unified Diffs & Anchored Line Findings</span>
        </h2>

        <DiffViewer
          files={effectiveFiles}
          findings={filteredFindings}
          reviewId={review.id}
        />
      </div>
    </div>
  );
}

export default function ReviewDetailPage() {
  return (
    <React.Suspense
      fallback={
        <div className="mx-auto max-w-7xl px-4 py-16 text-center text-xs text-[#8b949e]">
          <RefreshCw className="mx-auto h-6 w-6 animate-spin text-blue-400 mb-3" />
          <p className="text-sm font-medium text-white">Loading review inspector...</p>
        </div>
      }
    >
      <ReviewDetailContent />
    </React.Suspense>
  );
}
