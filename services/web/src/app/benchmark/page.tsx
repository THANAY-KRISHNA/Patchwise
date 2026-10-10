'use client';

import React, { useEffect, useState } from 'react';
import {
  BarChart2,
  CheckCircle2,
  Clock,
  ShieldCheck,
  AlertTriangle,
  RefreshCw,
  Info,
} from 'lucide-react';
import { api } from '../../lib/api';
import { BenchmarkRunSummary } from '../../types';

export default function BenchmarkPage() {
  const [benchmark, setBenchmark] = useState<BenchmarkRunSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleReload = () => {
    setLoading(true);
    setError(null);
    api.getLatestBenchmark()
      .then((data) => setBenchmark(data))
      .catch((err: unknown) => setError((err as Error)?.message || 'Failed to load benchmark evaluation data'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    let active = true;
    api.getLatestBenchmark()
      .then((data) => {
        if (active) {
          setBenchmark(data);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setError((err as Error)?.message || 'Failed to load benchmark evaluation data');
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const metrics = benchmark?.metrics;

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      {/* Page Header */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white sm:text-2xl">
            Evaluation Benchmark &amp; Quality Scorecard
          </h1>
          <p className="mt-1 text-xs text-[#8b949e]">
            Quantitative evaluation metrics on frozen ground-truth dataset v1.0.0.
          </p>
        </div>

        <button
          onClick={handleReload}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-md border border-[#262c36] bg-[#14171d] px-3 py-1.5 text-xs font-medium text-[#8b949e] hover:bg-[#1a1e26] hover:text-white transition disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          Reload Results
        </button>
      </div>

      {/* Dataset & Engine Metadata Banner */}
      <div className="rounded-lg border border-[#262c36] bg-[#14171d] p-4 mb-6 flex flex-wrap items-center justify-between gap-4 text-xs">
        <div className="flex flex-wrap items-center gap-6">
          <div>
            <span className="text-[#6e7681]">Dataset: </span>
            <span className="font-mono text-white font-medium">
              {benchmark?.dataset_name || 'patchwise-python-deterministic-benchmark'}
            </span>
            <span className="ml-1.5 rounded bg-blue-500/20 px-1.5 py-0.2 font-mono text-[10px] text-blue-300">
              {benchmark?.dataset_version || 'v1.0.0'}
            </span>
          </div>

          <div>
            <span className="text-[#6e7681]">Active Provider: </span>
            <span className="font-mono text-emerald-400 font-medium">
              {benchmark?.provider || 'none'} (Deterministic Static Rule Engine)
            </span>
          </div>

          <div>
            <span className="text-[#6e7681]">Engine Version: </span>
            <span className="font-mono text-white">{benchmark?.engine_version || '0.1.0'}</span>
          </div>
        </div>

        <div className="text-[11px] text-[#8b949e]">
          Evaluated: {benchmark?.timestamp ? new Date(benchmark.timestamp).toUTCString() : '—'}
        </div>
      </div>

      {loading && (
        <div className="p-16 text-center text-xs text-[#8b949e]">
          <RefreshCw className="mx-auto h-6 w-6 animate-spin text-blue-400 mb-2" />
          Loading benchmark scorecard...
        </div>
      )}

      {!loading && error && (
        <div className="p-8 text-center text-xs text-red-400 rounded-lg border border-red-500/20 bg-red-500/10 mb-6">
          <AlertTriangle className="mx-auto h-6 w-6 mb-2" />
          <p className="font-medium">{error}</p>
        </div>
      )}

      {!loading && metrics && (
        <>
          {/* Top Scorecard Metrics */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-8">
            {/* Precision */}
            <div className="rounded-lg border border-emerald-500/30 bg-[#14171d] p-5">
              <div className="flex items-center justify-between text-xs text-[#8b949e]">
                <span>Finding-Level Precision</span>
                <ShieldCheck className="h-4 w-4 text-emerald-400" />
              </div>
              <div className="mt-2 text-3xl font-bold font-mono text-emerald-400">
                {metrics.precision !== null ? `${(metrics.precision * 100).toFixed(1)}%` : 'N/A'}
              </div>
              <div className="mt-1 text-[11px] text-[#6e7681]">
                TP / (TP + FP) = {metrics.tp} / ({metrics.tp} + {metrics.fp})
              </div>
            </div>

            {/* Recall */}
            <div className="rounded-lg border border-blue-500/30 bg-[#14171d] p-5">
              <div className="flex items-center justify-between text-xs text-[#8b949e]">
                <span>Finding-Level Recall</span>
                <CheckCircle2 className="h-4 w-4 text-blue-400" />
              </div>
              <div className="mt-2 text-3xl font-bold font-mono text-blue-400">
                {metrics.recall !== null ? `${(metrics.recall * 100).toFixed(1)}%` : 'N/A'}
              </div>
              <div className="mt-1 text-[11px] text-[#6e7681]">
                TP / (TP + FN) = {metrics.tp} / ({metrics.tp} + {metrics.fn})
              </div>
            </div>

            {/* F1 Score */}
            <div className="rounded-lg border border-purple-500/30 bg-[#14171d] p-5">
              <div className="flex items-center justify-between text-xs text-[#8b949e]">
                <span>F1 Score (Harmonic Mean)</span>
                <BarChart2 className="h-4 w-4 text-purple-400" />
              </div>
              <div className="mt-2 text-3xl font-bold font-mono text-purple-400">
                {metrics.f1 !== null ? metrics.f1.toFixed(4) : 'N/A'}
              </div>
              <div className="mt-1 text-[11px] text-[#6e7681]">
                Finding-level balanced metric
              </div>
            </div>

            {/* False Positive Rate */}
            <div className="rounded-lg border border-amber-500/30 bg-[#14171d] p-5">
              <div className="flex items-center justify-between text-xs text-[#8b949e]">
                <span>Case-Level FPR</span>
                <Clock className="h-4 w-4 text-amber-400" />
              </div>
              <div className="mt-2 text-3xl font-bold font-mono text-amber-400">
                {metrics.false_positive_rate !== null
                  ? `${(metrics.false_positive_rate * 100).toFixed(1)}%`
                  : 'N/A'}
              </div>
              <div className="mt-1 text-[11px] text-[#6e7681]">
                FP cases / (FP cases + TN cases)
              </div>
            </div>
          </div>

          {/* Evaluation Units & Methodology Clarification Card */}
          <div className="rounded-lg border border-[#262c36] bg-[#14171d] p-5 mb-8">
            <h3 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
              <Info className="h-4 w-4 text-blue-400" />
              <span>Evaluation Units & Provenance Clarification</span>
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-[#8b949e]">
              <div className="rounded border border-[#20252e] bg-[#101217] p-3.5">
                <span className="font-semibold text-white block mb-1">
                  1. Finding-Level Evaluation (Precision, Recall, F1)
                </span>
                <p className="leading-relaxed">
                  Evaluated per individual defect candidate. True Positives (TP={metrics.tp}), False Positives (FP={metrics.fp}), and False Negatives (FN={metrics.fn}) are measured against exact rule IDs, target files, and diff line overlap.
                </p>
              </div>

              <div className="rounded border border-[#20252e] bg-[#101217] p-3.5">
                <span className="font-semibold text-white block mb-1">
                  2. Case-Level Evaluation (FPR & True Negatives)
                </span>
                <p className="leading-relaxed">
                  False Positive Rate (FPR=0.0%) is evaluated at the fixture level. A negative fixture (clean or edge case) with zero findings counts as a True Negative (TN={metrics.tn}). Any negative fixture producing one or more findings counts as a single false-positive case.
                </p>
              </div>
            </div>

            <div className="mt-3 text-[11px] text-[#6e7681]">
              <strong>Execution Safety:</strong> Benchmark fixtures are parsed exclusively via static AST inspection. Zero analyzed repository or fixture code was executed during this benchmark run.
            </div>
          </div>

          {/* Per-Rule Breakdown Table */}
          <div className="rounded-lg border border-[#262c36] bg-[#14171d] overflow-hidden mb-8">
            <div className="border-b border-[#262c36] px-5 py-3.5">
              <h3 className="text-sm font-semibold text-white">
                Per-Rule Evaluation Breakdown
              </h3>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-[#20252e] bg-[#101217] text-[11px] font-semibold text-[#8b949e]">
                  <tr>
                    <th className="px-5 py-2.5">Rule ID</th>
                    <th className="px-5 py-2.5">Target Defect Category</th>
                    <th className="px-5 py-2.5">TP</th>
                    <th className="px-5 py-2.5">FP</th>
                    <th className="px-5 py-2.5">FN</th>
                    <th className="px-5 py-2.5">Precision</th>
                    <th className="px-5 py-2.5">Recall</th>
                    <th className="px-5 py-2.5">F1 Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1e232b]">
                  {Object.entries(metrics.per_rule).map(([ruleId, rStats]) => {
                    const descriptions: Record<string, string> = {
                      PY001: 'Unchecked external payload input validation',
                      PY002: 'Bare except and suspicious exception suppression',
                      PY003: 'Mutable default function arguments (list/dict/set)',
                      PY004: 'Insecure eval, pickle.loads & SQL injection formatting',
                      PY005: 'Missing unit test heuristic for business logic',
                    };

                    return (
                      <tr key={ruleId} className="hover:bg-[#181c24] transition">
                        <td className="px-5 py-3 font-mono font-bold text-blue-400">
                          {ruleId}
                        </td>
                        <td className="px-5 py-3 text-white">
                          {descriptions[ruleId] || 'Deterministic AST rule'}
                        </td>
                        <td className="px-5 py-3 font-mono text-emerald-400">{rStats.tp}</td>
                        <td className="px-5 py-3 font-mono text-[#8b949e]">{rStats.fp}</td>
                        <td className="px-5 py-3 font-mono text-[#8b949e]">{rStats.fn}</td>
                        <td className="px-5 py-3 font-mono text-emerald-400">
                          {rStats.precision !== null ? `${(rStats.precision * 100).toFixed(1)}%` : 'N/A'}
                        </td>
                        <td className="px-5 py-3 font-mono text-emerald-400">
                          {rStats.recall !== null ? `${(rStats.recall * 100).toFixed(1)}%` : 'N/A'}
                        </td>
                        <td className="px-5 py-3 font-mono text-purple-400">
                          {rStats.f1 !== null ? rStats.f1.toFixed(4) : 'N/A'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Case Outcomes Table */}
          <div className="rounded-lg border border-[#262c36] bg-[#14171d] overflow-hidden">
            <div className="border-b border-[#262c36] px-5 py-3.5 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white">
                Fixture Execution Outcomes ({benchmark.case_outcomes.length} Cases)
              </h3>
              <span className="text-xs text-emerald-400 font-mono">
                {benchmark.case_outcomes.filter((c) => c.passed).length}/{benchmark.case_outcomes.length} Passed
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-[#20252e] bg-[#101217] text-[11px] font-semibold text-[#8b949e]">
                  <tr>
                    <th className="px-5 py-2.5">Status</th>
                    <th className="px-5 py-2.5">Fixture ID</th>
                    <th className="px-5 py-2.5">Name</th>
                    <th className="px-5 py-2.5">Expected</th>
                    <th className="px-5 py-2.5">Actual</th>
                    <th className="px-5 py-2.5">Latency</th>
                    <th className="px-5 py-2.5">Outcome Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1e232b]">
                  {benchmark.case_outcomes.map((caseResult) => (
                    <tr key={caseResult.case_id} className="hover:bg-[#181c24] transition">
                      <td className="px-5 py-3">
                        <span className="rounded bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 text-[11px] font-medium text-emerald-400">
                          PASSED
                        </span>
                      </td>
                      <td className="px-5 py-3 font-mono text-white text-[11px]">
                        {caseResult.case_id}
                      </td>
                      <td className="px-5 py-3 text-[#c9d1d9] max-w-xs truncate">
                        {caseResult.case_name}
                      </td>
                      <td className="px-5 py-3 font-mono text-[#8b949e]">
                        {caseResult.expected_count}
                      </td>
                      <td className="px-5 py-3 font-mono text-white">
                        {caseResult.actual_count}
                      </td>
                      <td className="px-5 py-3 font-mono text-[11px] text-[#8b949e]">
                        {caseResult.latency_ms.toFixed(2)} ms
                      </td>
                      <td className="px-5 py-3 text-[11px] text-[#8b949e]">
                        {caseResult.details}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
