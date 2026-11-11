'use client';

import React, { useEffect, useState } from 'react';
import {
  Layers,
  CheckCircle2,
  RefreshCw,
  Cpu,
  Database,
  Key,
  ShieldCheck,
  Eye,
  EyeOff,
} from 'lucide-react';
import { api, API_BASE_URL, getStoredApiKey, setStoredApiKey } from '../../lib/api';
import { HealthResponse, LanguagePluginMetadata } from '../../types';

export default function SettingsPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [plugins, setPlugins] = useState<LanguagePluginMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      return getStoredApiKey() || '';
    }
    return '';
  });
  const [showKey, setShowKey] = useState<boolean>(false);
  const [keySaved, setKeySaved] = useState<boolean>(false);

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

  const handleSaveKey = (e: React.FormEvent) => {
    e.preventDefault();
    setStoredApiKey(apiKey.trim() || null);
    setKeySaved(true);
    setTimeout(() => setKeySaved(false), 3000);
  };

  const handleClearKey = () => {
    setApiKey('');
    setStoredApiKey(null);
    setKeySaved(true);
    setTimeout(() => setKeySaved(false), 3000);
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
      {/* Header */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-[#f0f3f6] sm:text-2xl font-mono">
            Settings &amp; Workstation Configuration
          </h1>
          <p className="mt-1 text-xs text-[#949da8]">
            Engine telemetry, API authentication, and multi-language analyzer registry ({plugins.length} active plugins).
          </p>
        </div>

        <button
          onClick={handleRefresh}
          disabled={loading}
          className="flex items-center gap-1.5 rounded border border-[#1e222b] bg-[#101217] px-3 py-1.5 font-mono text-xs text-[#949da8] hover:bg-[#161820] hover:text-white transition disabled:opacity-50"
        >
          <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Backend Health & Telemetry Card */}
      <div className="rounded border border-[#1e222b] bg-[#101217] p-5 mb-6 font-mono text-xs">
        <h2 className="text-xs font-semibold text-white mb-1 flex items-center gap-2">
          <Database className="h-4 w-4 text-amber-400" />
          <span>FastAPI Backend Telemetry</span>
        </h2>
        <p className="text-xs text-[#949da8] mb-4 font-sans">
          Connected API instance details and database connectivity status.
        </p>

        {error && (
          <div className="rounded border border-red-500/30 bg-red-500/10 p-3 text-red-400 mb-4">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded border border-[#1e222b] bg-[#0c0d11] p-3">
            <span className="text-[#656e7b] block text-[11px] mb-1">API Endpoint</span>
            <span className="text-white font-medium">{API_BASE_URL}</span>
          </div>

          <div className="rounded border border-[#1e222b] bg-[#0c0d11] p-3">
            <span className="text-[#656e7b] block text-[11px] mb-1">Environment</span>
            <span className="text-amber-400 font-medium">
              {health?.environment || 'development'} (v{health?.version || '0.1.0'})
            </span>
          </div>

          <div className="rounded border border-[#1e222b] bg-[#0c0d11] p-3">
            <span className="text-[#656e7b] block text-[11px] mb-1">Database Dialect</span>
            <span className="text-white flex items-center gap-1.5">
              <span className={`h-2 w-2 rounded-full ${health?.database.connected ? 'bg-emerald-400' : 'bg-red-400'}`} />
              <span>{health?.database.dialect || 'postgresql'} ({health?.database.connected ? 'connected' : 'offline'})</span>
            </span>
          </div>

          <div className="rounded border border-[#1e222b] bg-[#0c0d11] p-3">
            <span className="text-[#656e7b] block text-[11px] mb-1">Review Engine Provider</span>
            <span className="text-emerald-400 font-medium flex items-center gap-1.5">
              <Cpu className="h-3.5 w-3.5" />
              <span>{health?.llm_provider || 'none'} (AST rule engine)</span>
            </span>
          </div>
        </div>
      </div>

      {/* API Authentication & Secret Key Management */}
      <div className="rounded border border-[#1e222b] bg-[#101217] p-5 mb-6">
        <h2 className="text-xs font-semibold text-white mb-1 flex items-center gap-2 font-mono">
          <Key className="h-4 w-4 text-amber-400" />
          <span>API Key Authentication (Production Mode)</span>
        </h2>
        <p className="text-xs text-[#949da8] mb-4">
          When the Patchwise backend runs in production mode, requests require an API key matching <code className="text-amber-400 font-mono">API_SECRET_KEY</code>.
          Stored keys are securely preserved in local browser storage and dispatched via the <code className="text-amber-400 font-mono">X-API-Key</code> request header.
        </p>

        <form onSubmit={handleSaveKey} className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[280px]">
            <input
              type={showKey ? 'text' : 'password'}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Enter server API_SECRET_KEY..."
              className="w-full rounded border border-[#1e222b] bg-[#090a0d] px-3 py-2 pr-10 font-mono text-xs text-white placeholder-[#656e7b] focus:border-amber-500 focus:outline-none"
            />
            <button
              type="button"
              onClick={() => setShowKey(!showKey)}
              className="absolute right-2.5 top-2.5 text-[#656e7b] hover:text-[#949da8] transition"
              title={showKey ? 'Hide key' : 'Show key'}
            >
              {showKey ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
            </button>
          </div>
          <button
            type="submit"
            className="rounded bg-amber-500 px-3.5 py-2 font-mono text-xs font-semibold text-black hover:bg-amber-400 transition"
          >
            Save Key
          </button>
          {apiKey && (
            <button
              type="button"
              onClick={handleClearKey}
              className="rounded border border-[#1e222b] bg-[#161820] px-3.5 py-2 font-mono text-xs text-[#949da8] hover:text-white hover:bg-[#1a1e26] transition"
            >
              Clear
            </button>
          )}
          {keySaved && (
            <span className="text-xs text-emerald-400 flex items-center gap-1 font-mono font-medium">
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>Authentication updated</span>
            </span>
          )}
        </form>
      </div>

      {/* Language Analyzers Status Board */}
      <div className="rounded border border-[#1e222b] bg-[#101217] overflow-hidden mb-6">
        <div className="border-b border-[#1e222b] px-5 py-3.5">
          <h2 className="text-xs font-semibold text-white flex items-center gap-2 font-mono">
            <Layers className="h-4 w-4 text-emerald-400" />
            <span>Language Plugin Readiness Board</span>
          </h2>
          <p className="text-xs text-[#949da8] mt-0.5">
            Strict truth-in-advertising policy: Analyzers are classified as &apos;Active &amp; Tested&apos; only after deterministic AST rules, test fixtures, and benchmarks are verified.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="border-b border-[#1e222b] bg-[#0c0e12] text-[11px] font-semibold text-[#949da8]">
              <tr>
                <th className="px-5 py-2.5">Language</th>
                <th className="px-5 py-2.5">File Extensions</th>
                <th className="px-5 py-2.5">Readiness Status</th>
                <th className="px-5 py-2.5">Rule Count</th>
                <th className="px-5 py-2.5">Version</th>
                <th className="px-5 py-2.5">Verification</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e222b]">
              {/* Python */}
              <tr className="hover:bg-[#14161f] transition">
                <td className="px-5 py-3 font-semibold text-white flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-400" />
                  <span>Python</span>
                </td>
                <td className="px-5 py-3 text-[#949da8]">.py</td>
                <td className="px-5 py-3">
                  <span className="inline-flex items-center gap-1 rounded bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 text-[11px] font-medium text-emerald-400">
                    <CheckCircle2 className="h-3 w-3" />
                    <span>Active &amp; Tested</span>
                  </span>
                </td>
                <td className="px-5 py-3 text-white">5 rules (PY001–PY005)</td>
                <td className="px-5 py-3 text-[#656e7b]">1.0.0</td>
                <td className="px-5 py-3 text-emerald-300 text-[11px] font-sans">
                  AST checks with diff line grounding.
                </td>
              </tr>

              {/* TypeScript & JavaScript */}
              <tr className="hover:bg-[#14161f] transition">
                <td className="px-5 py-3 font-semibold text-white flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-400" />
                  <span>TypeScript / JavaScript</span>
                </td>
                <td className="px-5 py-3 text-[#949da8]">.js, .jsx, .ts, .tsx</td>
                <td className="px-5 py-3">
                  <span className="inline-flex items-center gap-1 rounded bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 text-[11px] font-medium text-emerald-400">
                    <CheckCircle2 className="h-3 w-3" />
                    <span>Active &amp; Tested</span>
                  </span>
                </td>
                <td className="px-5 py-3 text-white">4 rules (JS001–JS004)</td>
                <td className="px-5 py-3 text-[#656e7b]">1.0.0</td>
                <td className="px-5 py-3 text-emerald-300 text-[11px] font-sans">
                  ESTree AST checks with diff line grounding.
                </td>
              </tr>

              {/* Java */}
              <tr className="hover:bg-[#14161f] transition">
                <td className="px-5 py-3 font-semibold text-white flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-400" />
                  <span>Java</span>
                </td>
                <td className="px-5 py-3 text-[#949da8]">.java</td>
                <td className="px-5 py-3">
                  <span className="inline-flex items-center gap-1 rounded bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 text-[11px] font-medium text-emerald-400">
                    <CheckCircle2 className="h-3 w-3" />
                    <span>Active &amp; Tested</span>
                  </span>
                </td>
                <td className="px-5 py-3 text-white">4 rules (JV001–JV004)</td>
                <td className="px-5 py-3 text-[#656e7b]">1.0.0</td>
                <td className="px-5 py-3 text-emerald-300 text-[11px] font-sans">
                  Lexical token &amp; syntax checks with diff line grounding.
                </td>
              </tr>

              {/* C / C++ */}
              <tr className="hover:bg-[#14161f] transition">
                <td className="px-5 py-3 font-semibold text-white flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-400" />
                  <span>C / C++</span>
                </td>
                <td className="px-5 py-3 text-[#949da8]">.c, .h, .cc, .cpp, .cxx, .hh, .hpp</td>
                <td className="px-5 py-3">
                  <span className="inline-flex items-center gap-1 rounded bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 text-[11px] font-medium text-emerald-400">
                    <CheckCircle2 className="h-3 w-3" />
                    <span>Active &amp; Tested</span>
                  </span>
                </td>
                <td className="px-5 py-3 text-white">4 rules (CC001–CC004)</td>
                <td className="px-5 py-3 text-[#656e7b]">1.0.0</td>
                <td className="px-5 py-3 text-emerald-300 text-[11px] font-sans">
                  Lexical token &amp; memory safety checks.
                </td>
              </tr>

              {/* SQL / HiveQL */}
              <tr className="hover:bg-[#14161f] transition">
                <td className="px-5 py-3 font-semibold text-white flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-400" />
                  <span>SQL / HiveQL</span>
                </td>
                <td className="px-5 py-3 text-[#949da8]">.sql, .hql, .hive, .q</td>
                <td className="px-5 py-3">
                  <span className="inline-flex items-center gap-1 rounded bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 text-[11px] font-medium text-emerald-400">
                    <CheckCircle2 className="h-3 w-3" />
                    <span>Active &amp; Tested</span>
                  </span>
                </td>
                <td className="px-5 py-3 text-white">5 rules (SQL001–SQL005)</td>
                <td className="px-5 py-3 text-[#656e7b]">1.0.0</td>
                <td className="px-5 py-3 text-emerald-300 text-[11px] font-sans">
                  Query safety &amp; schema pattern checks.
                </td>
              </tr>

              {/* Planned */}
              <tr className="hover:bg-[#14161f] transition">
                <td className="px-5 py-3 text-[#949da8] flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-[#656e7b]" />
                  <span>PySpark &amp; Scala</span>
                </td>
                <td className="px-5 py-3 text-[#656e7b]">.py, .scala</td>
                <td className="px-5 py-3">
                  <span className="inline-flex items-center gap-1 rounded bg-zinc-500/10 border border-zinc-500/30 px-2 py-0.5 text-[11px] font-medium text-zinc-400">
                    Planned
                  </span>
                </td>
                <td className="px-5 py-3 text-[#656e7b]">Scheduled (0)</td>
                <td className="px-5 py-3 text-[#656e7b]">Milestone 7E</td>
                <td className="px-5 py-3 text-[#656e7b] text-[11px] font-sans">
                  Scheduled on future roadmap.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Security & Operational Policy */}
      <div className="rounded border border-[#1e222b] bg-[#101217] p-5">
        <h2 className="text-xs font-semibold text-white mb-2 flex items-center gap-2 font-mono">
          <ShieldCheck className="h-4 w-4 text-emerald-400" />
          <span>Security &amp; Operational Integrity Policy</span>
        </h2>
        <div className="space-y-2.5 text-xs text-[#949da8] font-sans">
          <p className="leading-relaxed">
            • <strong>Zero Code Execution:</strong> Patchwise is strictly a static text and AST analyzer. It never executes user repository code, unvetted test harnesses, or shell scripts on the host server.
          </p>
          <p className="leading-relaxed">
            • <strong>Secret Scrubbing &amp; Redaction:</strong> Credentials (<code className="text-white font-mono">GITHUB_TOKEN</code>, database passwords, API keys) are redacted from logs, exception traces, and client responses before serialization.
          </p>
          <p className="leading-relaxed">
            • <strong>SSRF Prevention:</strong> Outbound GitHub requests strictly enforce HTTPS and prohibit localhost, link-local metadata addresses (`169.254.169.254`), and raw IP addresses.
          </p>
        </div>
      </div>
    </div>
  );
}
