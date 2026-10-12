'use client';

import React, { useEffect, useState } from 'react';
import {
  Server,
  Layers,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Lock,
  Cpu,
  Database,
} from 'lucide-react';
import { api, API_BASE_URL } from '../../lib/api';
import { HealthResponse, LanguagePluginMetadata } from '../../types';

export default function SettingsPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [plugins, setPlugins] = useState<LanguagePluginMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleRefresh = () => {
    setLoading(true);
    setError(null);
    Promise.all([api.getHealth(), api.getPlugins()])
      .then(([healthData, pluginsData]) => {
        setHealth(healthData);
        setPlugins(pluginsData.plugins);
      })
      .catch((err: unknown) => {
        setError((err as Error)?.message || 'Failed to load system status');
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    let active = true;
    Promise.all([api.getHealth(), api.getPlugins()])
      .then(([healthData, pluginsData]) => {
        if (active) {
          setHealth(healthData);
          setPlugins(pluginsData.plugins);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setError((err as Error)?.message || 'Failed to load system status');
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      {/* Page Header */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white sm:text-2xl">
            Settings &amp; Language Analyzer Readiness
          </h1>
          <p className="mt-1 text-xs text-[#8b949e]">
            Operational configuration, backend telemetry, and multi-language analyzer support status ({plugins.length} plugin registered).
          </p>
        </div>

        <button
          onClick={handleRefresh}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-md border border-[#262c36] bg-[#14171d] px-3 py-1.5 text-xs font-medium text-[#8b949e] hover:bg-[#1a1e26] hover:text-white transition disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh Status
        </button>
      </div>

      {error && (
        <div className="mb-6 rounded-md border border-red-500/30 bg-red-950/20 p-4 text-xs text-red-400 flex items-center gap-2">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Backend & API Connectivity Card */}
      <div className="rounded-lg border border-[#262c36] bg-[#14171d] p-5 mb-8">
        <h2 className="text-sm font-semibold text-white mb-1 flex items-center gap-2">
          <Server className="h-4 w-4 text-blue-400" />
          <span>FastAPI Backend Infrastructure</span>
        </h2>
        <p className="text-xs text-[#8b949e] mb-4">
          Status of connection between the Next.js App Router and the Python FastAPI API service.
        </p>

        {loading && (
          <div className="p-4 text-center text-xs text-[#8b949e]">
            <RefreshCw className="mx-auto h-4 w-4 animate-spin mb-1 text-blue-400" />
            Testing connectivity...
          </div>
        )}

        {!loading && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs font-mono">
            <div className="rounded-md border border-[#20252e] bg-[#101217] p-3">
              <span className="text-[#6e7681] block text-[11px] mb-1">API Endpoint URL</span>
              <span className="text-white truncate block">{API_BASE_URL}</span>
            </div>

            <div className="rounded-md border border-[#20252e] bg-[#101217] p-3">
              <span className="text-[#6e7681] block text-[11px] mb-1">Service Status</span>
              {health?.status === 'healthy' ? (
                <span className="text-emerald-400 font-semibold flex items-center gap-1">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Healthy (Online)
                </span>
              ) : (
                <span className="text-red-400 font-semibold flex items-center gap-1">
                  <AlertCircle className="h-3.5 w-3.5" />
                  Degraded / Offline
                </span>
              )}
            </div>

            <div className="rounded-md border border-[#20252e] bg-[#101217] p-3">
              <span className="text-[#6e7681] block text-[11px] mb-1">Database Dialect</span>
              <span className="text-white flex items-center gap-1">
                <Database className="h-3.5 w-3.5 text-blue-400" />
                {health?.database.dialect || 'postgresql'} (
                {health?.database.connected ? 'Connected' : 'Offline'})
              </span>
            </div>

            <div className="rounded-md border border-[#20252e] bg-[#101217] p-3">
              <span className="text-[#6e7681] block text-[11px] mb-1">Configured Review Provider</span>
              <span className="text-emerald-400 font-semibold flex items-center gap-1">
                <Cpu className="h-3.5 w-3.5" />
                {health?.llm_provider || 'none'}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Language Analyzers Status Board */}
      <div className="rounded-lg border border-[#262c36] bg-[#14171d] overflow-hidden mb-8">
        <div className="border-b border-[#262c36] px-5 py-3.5">
          <h2 className="text-sm font-semibold text-white flex items-center gap-2">
            <Layers className="h-4 w-4 text-emerald-400" />
            <span>Language Plugin Readiness Board</span>
          </h2>
          <p className="text-xs text-[#8b949e] mt-0.5">
            Strict truth-in-advertising policy: Analyzers are marked &apos;Active &amp; Tested&apos; only after operational rule suites and tests are complete.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-[#20252e] bg-[#101217] text-[11px] font-semibold text-[#8b949e]">
              <tr>
                <th className="px-5 py-2.5">Language</th>
                <th className="px-5 py-2.5">File Extensions</th>
                <th className="px-5 py-2.5">Readiness Status</th>
                <th className="px-5 py-2.5">Rule Count</th>
                <th className="px-5 py-2.5">Version</th>
                <th className="px-5 py-2.5">Implementation Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e232b]">
              {/* Python (Active) */}
              <tr className="hover:bg-[#181c24] transition bg-emerald-950/10">
                <td className="px-5 py-3 font-semibold text-white flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-400" />
                  Python
                </td>
                <td className="px-5 py-3 font-mono text-[#8b949e]">.py</td>
                <td className="px-5 py-3">
                  <span className="inline-flex items-center gap-1 rounded bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 text-[11px] font-medium text-emerald-400">
                    <CheckCircle2 className="h-3 w-3" />
                    Active &amp; Tested
                  </span>
                </td>
                <td className="px-5 py-3 font-mono text-white">5 rules (PY001–PY005)</td>
                <td className="px-5 py-3 font-mono text-[#8b949e]">1.0.0</td>
                <td className="px-5 py-3 text-emerald-300 text-[11px]">
                  Fully operational AST checks with diff line grounding.
                </td>
              </tr>

              {/* JavaScript & TypeScript (Active in Milestone 7A) */}
              <tr className="hover:bg-[#181c24] transition bg-emerald-950/10">
                <td className="px-5 py-3 font-semibold text-white flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-400" />
                  TypeScript / JavaScript
                </td>
                <td className="px-5 py-3 font-mono text-[#8b949e]">.js, .jsx, .ts, .tsx</td>
                <td className="px-5 py-3">
                  <span className="inline-flex items-center gap-1 rounded bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 text-[11px] font-medium text-emerald-400">
                    <CheckCircle2 className="h-3 w-3" />
                    Active &amp; Tested
                  </span>
                </td>
                <td className="px-5 py-3 font-mono text-white">4 rules (JS001–JS004)</td>
                <td className="px-5 py-3 font-mono text-[#8b949e]">1.0.0</td>
                <td className="px-5 py-3 text-emerald-300 text-[11px]">
                  Fully operational ESTree AST checks with diff line grounding.
                </td>
              </tr>

              {/* Planned Languages */}
              {[
                { name: 'Java', ext: '.java', plan: 'Milestone 7B' },
                { name: 'C / C++', ext: '.c, .cpp, .h', plan: 'Milestone 7C' },
                { name: 'SQL / HiveQL', ext: '.sql, .hql', plan: 'Milestone 7D' },
                { name: 'PySpark & Scala', ext: '.py, .scala', plan: 'Milestone 7E' },
              ].map((lang) => (
                <tr key={lang.name} className="hover:bg-[#181c24] transition">
                  <td className="px-5 py-3 text-[#c9d1d9] flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-[#484f58]" />
                    {lang.name}
                  </td>
                  <td className="px-5 py-3 font-mono text-[#6e7681]">{lang.ext}</td>
                  <td className="px-5 py-3">
                    <span className="inline-flex items-center gap-1 rounded bg-zinc-500/10 border border-zinc-500/30 px-2 py-0.5 text-[11px] font-medium text-zinc-400">
                      Planned
                    </span>
                  </td>
                  <td className="px-5 py-3 font-mono text-[#6e7681]">Framework Ready (0)</td>
                  <td className="px-5 py-3 font-mono text-[#6e7681]">Planned</td>
                  <td className="px-5 py-3 text-[#6e7681] text-[11px]">
                    Scheduled for {lang.plan} following frontend completion.
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Security & Operational Controls Card */}
      <div className="rounded-lg border border-[#262c36] bg-[#14171d] p-5">
        <h2 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
          <Lock className="h-4 w-4 text-amber-400" />
          <span>Security &amp; Secret Isolation Policy</span>
        </h2>
        <div className="space-y-3 text-xs text-[#8b949e]">
          <p className="leading-relaxed">
            • <strong>Zero Code Execution:</strong> The application server strictly acts as a static text and AST analyzer. It never invokes <code className="text-white">eval()</code>, shell commands, or external build scripts on analyzed repository code.
          </p>
          <p className="leading-relaxed">
            • <strong>Secret Isolation:</strong> Credentials (<code className="text-white">GITHUB_TOKEN</code>, <code className="text-white">DATABASE_URL</code>, and LLM API keys) exist exclusively in backend environment variables. No secrets are rendered, transmitted, or bundled into browser code.
          </p>
          <p className="leading-relaxed">
            • <strong>Diff Bounds:</strong> Oversized pull requests are limited by <code className="text-white">MAX_FILES_PER_REVIEW=20</code> and <code className="text-white">MAX_PATCH_CHARS=80,000</code> to protect system memory and response times.
          </p>
        </div>
      </div>
    </div>
  );
}
