'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  GitPullRequest,
  RefreshCw,
  Search,
  Filter,
  ArrowRight,
  AlertTriangle,
} from 'lucide-react';
import { api } from '../../lib/api';
import { Review } from '../../types';
import { ReviewStatusBadge } from '../../components/StatusBadge';

export default function ReviewsListPage() {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const handleReload = () => {
    setLoading(true);
    setError(null);
    api.getReviews(100)
      .then((data) => setReviews(data))
      .catch((err: unknown) => setError((err as Error)?.message || 'Failed to load reviews'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    let active = true;
    api.getReviews(100)
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

  const filteredReviews = reviews.filter((r) => {
    const matchesSearch =
      r.repository.toLowerCase().includes(search.toLowerCase()) ||
      r.pr_title?.toLowerCase().includes(search.toLowerCase()) ||
      String(r.pr_number).includes(search);
    const matchesStatus =
      statusFilter === 'all' ? true : r.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white sm:text-2xl">
            Pull Request Reviews
          </h1>
          <p className="mt-1 text-xs text-[#8b949e]">
            Browse all analyzed pull requests, inspect unified diffs, and review flagged findings.
          </p>
        </div>

        <button
          onClick={handleReload}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-md border border-[#262c36] bg-[#14171d] px-3 py-1.5 text-xs font-medium text-[#8b949e] hover:bg-[#1a1e26] hover:text-white transition disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[240px]">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-[#6e7681]" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search repository, PR title, or number..."
            className="w-full rounded-md border border-[#262c36] bg-[#14171d] pl-9 pr-3 py-2 text-xs text-white placeholder-[#6e7681] focus:border-blue-500 focus:outline-none"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="h-3.5 w-3.5 text-[#6e7681]" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-md border border-[#262c36] bg-[#14171d] px-3 py-2 text-xs text-white focus:border-blue-500 focus:outline-none"
          >
            <option value="all">All Statuses</option>
            <option value="completed">Completed</option>
            <option value="in_progress">In Progress</option>
            <option value="failed">Failed</option>
            <option value="queued">Queued</option>
          </select>
        </div>
      </div>

      {/* Reviews Table */}
      <div className="rounded-lg border border-[#262c36] bg-[#14171d] overflow-hidden">
        {loading && (
          <div className="p-12 text-center text-xs text-[#8b949e]">
            <RefreshCw className="mx-auto h-5 w-5 animate-spin mb-2 text-blue-400" />
            Loading reviews...
          </div>
        )}

        {!loading && error && (
          <div className="p-8 text-center text-xs text-red-400">
            <AlertTriangle className="mx-auto h-6 w-6 mb-2" />
            <p className="font-medium">{error}</p>
          </div>
        )}

        {!loading && !error && filteredReviews.length === 0 && (
          <div className="p-12 text-center text-xs text-[#8b949e]">
            <GitPullRequest className="mx-auto h-8 w-8 mb-2 text-[#484f58]" />
            <p className="font-medium text-white text-sm">No matching reviews</p>
            <p className="text-[#6e7681] mt-1 mb-4">
              Database currently has no completed reviews recorded. You can inspect our full demo fixture to evaluate the diff inspector and feedback tools.
            </p>
            <Link
              href="/reviews/demo"
              className="inline-flex items-center gap-1.5 rounded-md border border-blue-500/30 bg-blue-950/20 px-3.5 py-1.5 text-xs font-medium text-blue-400 hover:bg-blue-900/30 transition"
            >
              <span>Inspect Demo Pull Request (#42)</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        )}

        {!loading && !error && filteredReviews.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-[#20252e] bg-[#101217] text-[11px] font-semibold text-[#8b949e]">
                <tr>
                  <th className="px-5 py-2.5">Repository & PR</th>
                  <th className="px-5 py-2.5">Status</th>
                  <th className="px-5 py-2.5">Findings</th>
                  <th className="px-5 py-2.5">Engine</th>
                  <th className="px-5 py-2.5">Duration</th>
                  <th className="px-5 py-2.5">Timestamp</th>
                  <th className="px-5 py-2.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e232b]">
                {filteredReviews.map((r) => (
                  <tr key={r.id} className="hover:bg-[#181c24] transition">
                    <td className="px-5 py-3">
                      <div className="font-medium text-white">
                        {r.repository} #{r.pr_number}
                      </div>
                      <div className="text-[11px] text-[#6e7681] truncate max-w-sm">
                        {r.pr_title || 'No PR description'}
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
                          ({r.summary.critical_count} critical)
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3 font-mono text-[11px] text-[#8b949e]">
                      {r.engine_version}
                    </td>
                    <td className="px-5 py-3 font-mono text-[11px] text-[#8b949e]">
                      {r.duration_ms ? `${r.duration_ms} ms` : '—'}
                    </td>
                    <td className="px-5 py-3 text-[#8b949e] text-[11px]">
                      {new Date(r.started_at).toLocaleString()}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <Link
                        href={`/reviews/${r.id}`}
                        className="inline-flex items-center gap-1 rounded bg-blue-600/10 border border-blue-500/20 px-2.5 py-1 text-xs font-medium text-blue-400 hover:bg-blue-600/20 hover:text-blue-300 transition"
                      >
                        Inspect Diff
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
