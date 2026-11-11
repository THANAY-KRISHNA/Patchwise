'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  GitPullRequest,
  ArrowRight,
  Plus,
  RefreshCw,
  AlertTriangle,
  Terminal,
} from 'lucide-react';
import { api } from '../lib/api';
import { Review, ReviewSummary } from '../types';
import { ReviewStatusBadge } from '../components/StatusBadge';
import { SeverityBar } from '../components/SeverityBar';

const PRESET_PRS = [
  { label: 'React #1234', repo: 'https://github.com/facebook/react', pr: 1234 },
  { label: 'Linux #84', repo: 'https://github.com/torvalds/linux', pr: 84 },
  { label: 'CPython #992', repo: 'https://github.com/python/cpython', pr: 992 },
];

export default function OverviewPage() {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New review form state
  const [repoUrl, setRepoUrl] = useState('https://github.com/facebook/react');
  const [prNumber, setPrNumber] = useState<number | ''>(1234);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleReload = () => {
    setLoading(true);
    setError(null);
    api.getReviews(50)
      .then((data) => setReviews(data))
      .catch((err: unknown) => setError((err as Error)?.message || 'Failed to load reviews'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    let active = true;
    api.getReviews(50)
      .then((data) => {
        if (active) {
          setReviews(data);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setError((err as Error)?.message || 'Failed to load reviews');
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  async function handleStartReview(e: React.FormEvent) {
    e.preventDefault();
    if (!repoUrl) return;

    setSubmitting(true);
    setSubmitError(null);

    try {
      const newReview = await api.createReview({
        repository_url: repoUrl,
        pull_request_number: prNumber ? Number(prNumber) : null,
      });
      setReviews((prev) => [newReview, ...prev]);
    } catch (err: unknown) {
      setSubmitError((err as Error)?.message || 'Failed to initiate PR review');
    } finally {
      setSubmitting(false);
    }
  }

  // Aggregate metrics
  const totalReviews = reviews.length;
  const completedReviews = reviews.filter((r) => r.status === 'completed').length;
  const totalFindings = reviews.reduce((acc, r) => acc + (r.summary?.total_findings || 0), 0);
  const totalCritical = reviews.reduce((acc, r) => acc + (r.summary?.critical_count || 0), 0);
  const totalHigh = reviews.reduce((acc, r) => acc + (r.summary?.high_count || 0), 0);

  const aggregatedSummary: ReviewSummary = {
    total_findings: totalFindings,
    critical_count: totalCritical,
    high_count: totalHigh,
    medium: reviews.reduce((acc, r) => acc + (r.summary?.medium_count || 0), 0),
    low_count: reviews.reduce((acc, r) => acc + (r.summary?.low_count || 0), 0),
    info_count: reviews.reduce((acc, r) => acc + (r.summary?.info_count || 0), 0),
    deterministic_count: reviews.reduce((acc, r) => acc + (r.summary?.deterministic_count || 0), 0),
    ai_hypothesis_count: reviews.reduce((acc, r) => acc + (r.summary?.ai_hypothesis_count || 0), 0),
    verified_test_count: reviews.reduce((acc, r) => acc + (r.summary?.verified_test_count || 0), 0),
  } as unknown as ReviewSummary;

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      {/* Hero & Workspace Header */}
      <div className="mb-8 border-b border-[#1e222b] pb-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-[#f0f3f6] sm:text-2xl">
              Pull Request Integrity Inspector
            </h1>
            <p className="mt-1 text-xs text-[#949da8] max-w-2xl leading-relaxed">
              Deterministic AST defect triage and strict diff-line grounding across Python, TypeScript, Java, C++, and SQL patches.
            </p>
          </div>
          <button
            onClick={handleReload}
            disabled={loading}
            className="flex items-center gap-1.5 rounded border border-[#1e222b] bg-[#101217] px-3 py-1.5 font-mono text-xs text-[#949da8] hover:bg-[#161820] hover:text-white transition disabled:opacity-50"
          >
            <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>

        {/* Integrated Telemetry HUD Bar */}
        <div className="mt-6 grid grid-cols-2 gap-px bg-[#1e222b] rounded overflow-hidden border border-[#1e222b] sm:grid-cols-4">
          <div className="bg-[#101217] p-3.5">
            <span className="text-[11px] font-mono text-[#949da8] block">Review Dispatches</span>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="font-mono text-xl font-bold text-white">{totalReviews}</span>
              <span className="font-mono text-[10px] text-[#656e7b]">{completedReviews} completed</span>
            </div>
          </div>

          <div className="bg-[#101217] p-3.5">
            <span className="text-[11px] font-mono text-[#949da8] block">Line-Grounded Findings</span>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="font-mono text-xl font-bold text-emerald-400">{totalFindings}</span>
              <span className="font-mono text-[10px] text-emerald-500/80">100% grounded</span>
            </div>
          </div>

          <div className="bg-[#101217] p-3.5">
            <span className="text-[11px] font-mono text-[#949da8] block">Critical & High Defects</span>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="font-mono text-xl font-bold text-red-400">{totalCritical + totalHigh}</span>
              <span className="font-mono text-[10px] text-[#656e7b]">{totalCritical} crit / {totalHigh} high</span>
            </div>
          </div>

          <div className="bg-[#101217] p-3.5">
            <span className="text-[11px] font-mono text-[#949da8] block">Active Language Plugins</span>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="font-mono text-xs font-semibold text-amber-400">5 Active</span>
              <span className="font-mono text-[10px] text-[#656e7b]">Py • TS • Java • C++ • SQL</span>
            </div>
          </div>
        </div>
      </div>

      {/* Command Deck: Review Dispatcher & Severity Profile */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3 mb-8">
        {/* Review Dispatch Terminal */}
        <div className="rounded border border-[#1e222b] bg-[#101217] p-5 lg:col-span-2">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-xs font-semibold text-white flex items-center gap-1.5 font-mono">
              <Terminal className="h-3.5 w-3.5 text-amber-400" />
              <span>Dispatch Review</span>
            </h2>
            {/* Quick Presets */}
            <div className="flex items-center gap-1.5 text-[11px]">
              <span className="text-[#656e7b] font-mono">Presets:</span>
              {PRESET_PRS.map((p) => (
                <button
                  key={p.label}
                  type="button"
                  onClick={() => {
                    setRepoUrl(p.repo);
                    setPrNumber(p.pr);
                  }}
                  className="rounded border border-[#1e222b] bg-[#161820] px-1.5 py-0.5 font-mono text-[10px] text-[#949da8] hover:text-white hover:border-[#282e3c] transition"
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
          <p className="text-xs text-[#949da8] mb-4">
            Submits a repository URL for unified diff extraction, multi-language parser dispatch, and line-grounded defect validation.
          </p>

          <form onSubmit={handleStartReview} className="space-y-4">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="sm:col-span-2">
                <label className="block text-[11px] font-medium text-[#949da8] mb-1 font-mono">
                  GitHub Repository URL
                </label>
                <input
                  type="text"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  placeholder="https://github.com/owner/repo"
                  className="w-full rounded border border-[#1e222b] bg-[#090a0d] px-3 py-1.5 font-mono text-xs text-white placeholder-[#656e7b] focus:border-amber-500 focus:outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-[11px] font-medium text-[#949da8] mb-1 font-mono">
                  PR Number
                </label>
                <input
                  type="number"
                  value={prNumber}
                  onChange={(e) =>
                    setPrNumber(e.target.value ? parseInt(e.target.value) : '')
                  }
                  placeholder="1234"
                  className="w-full rounded border border-[#1e222b] bg-[#090a0d] px-3 py-1.5 font-mono text-xs text-white placeholder-[#656e7b] focus:border-amber-500 focus:outline-none"
                />
              </div>
            </div>

            {submitError && (
              <div className="rounded border border-red-500/30 bg-red-500/10 p-2.5 text-xs text-red-400 font-mono">
                {submitError}
              </div>
            )}

            <div className="flex items-center justify-between pt-1">
              <span className="text-[11px] text-[#656e7b] font-mono">
                Uses offline deterministic fixtures if no upstream token is configured.
              </span>
              <button
                type="submit"
                disabled={submitting}
                className="flex items-center gap-1.5 rounded bg-amber-500 px-3.5 py-1.5 text-xs font-semibold text-black hover:bg-amber-400 transition disabled:opacity-50"
              >
                {submitting ? (
                  <>
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                    <span>Analyzing Diff...</span>
                  </>
                ) : (
                  <>
                    <Plus className="h-3.5 w-3.5" />
                    <span>Analyze Pull Request</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Severity Profile */}
        <div className="rounded border border-[#1e222b] bg-[#101217] p-5">
          <h2 className="text-xs font-semibold text-white mb-1 font-mono">
            Severity Profile
          </h2>
          <p className="text-xs text-[#949da8] mb-4">
            Aggregated findings distribution across pull request diffs.
          </p>

          <SeverityBar summary={aggregatedSummary} />

          <div className="mt-5 pt-4 border-t border-[#1e222b] space-y-2.5 text-xs">
            <div className="flex justify-between items-center text-[#949da8]">
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
                <span>Deterministic Static Rules (Tier 1):</span>
              </span>
              <span className="font-mono text-emerald-400 font-semibold">
                {aggregatedSummary.deterministic_count}
              </span>
            </div>
            <div className="flex justify-between items-center text-[#949da8]">
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-purple-400" />
                <span>AI Hypotheses (Tier 2, unverified):</span>
              </span>
              <span className="font-mono text-purple-400 font-semibold">
                {aggregatedSummary.ai_hypothesis_count}
              </span>
            </div>
            <div className="flex justify-between items-center text-[#949da8]">
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-cyan-400" />
                <span>Verified Test Results (Tier 3):</span>
              </span>
              <span className="font-mono text-cyan-400 font-semibold">
                {aggregatedSummary.verified_test_count}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Reviews Table */}
      <div className="rounded border border-[#1e222b] bg-[#101217] overflow-hidden">
        <div className="flex items-center justify-between border-b border-[#1e222b] px-5 py-3">
          <div className="flex items-center gap-2">
            <h2 className="text-xs font-semibold text-white font-mono">Recent Pull Request Reviews</h2>
            <span className="rounded bg-[#161820] border border-[#1e222b] px-1.5 py-0.2 text-[10px] font-mono text-[#949da8]">
              {reviews.length}
            </span>
          </div>

          <Link
            href="/reviews"
            className="flex items-center gap-1 text-xs font-mono text-amber-400 hover:text-amber-300 transition"
          >
            <span>All Reviews</span>
            <ArrowRight className="h-3 w-3" />
          </Link>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="p-8 text-center text-xs text-[#949da8]">
            <RefreshCw className="mx-auto h-5 w-5 animate-spin mb-2 text-amber-400" />
            <span>Loading review history from backend...</span>
          </div>
        )}

        {/* Error State */}
        {!loading && error && (
          <div className="p-8 text-center text-xs text-red-400 font-mono">
            <AlertTriangle className="mx-auto h-6 w-6 mb-2 text-red-400" />
            <p className="font-medium">{error}</p>
            <p className="text-[#656e7b] mt-1">Ensure FastAPI server is running at http://localhost:8000.</p>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && reviews.length === 0 && (
          <div className="p-12 text-center text-xs text-[#949da8]">
            <GitPullRequest className="mx-auto h-8 w-8 mb-2 text-[#656e7b]" />
            <p className="font-medium text-white text-sm">No reviews conducted yet</p>
            <p className="text-[#656e7b] mt-1 max-w-sm mx-auto font-mono">
              Submit your first pull request URL above to analyze AST rules, input validation, and diff line grounding.
            </p>
          </div>
        )}

        {/* Reviews Table */}
        {!loading && !error && reviews.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-[#1e222b] bg-[#0c0e12] text-[11px] font-semibold text-[#949da8] font-mono">
                <tr>
                  <th className="px-5 py-2.5">Repository & PR</th>
                  <th className="px-5 py-2.5">Status</th>
                  <th className="px-5 py-2.5">Findings</th>
                  <th className="px-5 py-2.5">Latency</th>
                  <th className="px-5 py-2.5">Started</th>
                  <th className="px-5 py-2.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e222b]">
                {reviews.map((r) => (
                  <tr key={r.id} className="hover:bg-[#14161f] transition">
                    <td className="px-5 py-3">
                      <div className="font-mono font-medium text-white">
                        {r.repository} #{r.pr_number}
                      </div>
                      <div className="text-[11px] text-[#656e7b] truncate max-w-xs mt-0.5">
                        {r.pr_title || 'Unified diff review'}
                      </div>
                    </td>
                    <td className="px-5 py-3">
                      <ReviewStatusBadge status={r.status} />
                    </td>
                    <td className="px-5 py-3 font-mono">
                      <span className="font-semibold text-white">
                        {r.summary?.total_findings || 0}
                      </span>
                      {r.summary?.critical_count > 0 && (
                        <span className="ml-1 text-red-400 text-[10px]">
                          ({r.summary.critical_count} crit)
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-[#949da8] font-mono text-[11px]">
                      {r.duration_ms ? `${r.duration_ms} ms` : '—'}
                    </td>
                    <td className="px-5 py-3 text-[#949da8] text-[11px] font-mono">
                      {new Date(r.started_at).toLocaleString()}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <Link
                        href={`/reviews/${r.id}`}
                        className="inline-flex items-center gap-1 font-mono text-xs text-amber-400 hover:text-amber-300 transition"
                      >
                        <span>Inspect</span>
                        <ArrowRight className="h-3 w-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}