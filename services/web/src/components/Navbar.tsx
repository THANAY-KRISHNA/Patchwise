'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  GitPullRequest,
  BarChart2,
  Settings,
  Activity,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
} from 'lucide-react';
import { api } from '../lib/api';
import { HealthResponse } from '../types';

export const Navbar: React.FC = () => {
  const pathname = usePathname();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [connected, setConnected] = useState<boolean | null>(null);

  useEffect(() => {
    let isMounted = true;
    async function checkHealth() {
      try {
        const data = await api.getHealth();
        if (isMounted) {
          setHealth(data);
          setConnected(data.status === 'healthy');
        }
      } catch {
        if (isMounted) {
          setConnected(false);
        }
      }
    }
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const navItems = [
    { label: 'Overview', href: '/', icon: Activity },
    { label: 'PR Reviews', href: '/reviews', icon: GitPullRequest },
    { label: 'Benchmark', href: '/benchmark', icon: BarChart2 },
    { label: 'Settings', href: '/settings', icon: Settings },
  ];

  return (
    <header className="sticky top-0 z-50 border-b border-[#1e2430] bg-[#08090b]/95 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
        {/* Brand */}
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2.5 font-semibold tracking-tight text-white transition hover:opacity-95">
            <div className="flex h-7 w-7 items-center justify-center rounded border border-amber-500/40 bg-amber-500/10 font-mono text-xs font-bold text-amber-400">
              PW
            </div>
            <span className="text-sm font-semibold tracking-tight text-[#f0f3f6]">Patchwise</span>
            <span className="font-mono text-[10px] text-[#656e7b] border border-[#1e2430] px-1.5 py-0.5 rounded bg-[#0f1217]">
              v0.1.0
            </span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1 pl-4">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive =
                item.href === '/'
                  ? pathname === '/'
                  : pathname?.startsWith(item.href);

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-2 rounded px-2.5 py-1.5 text-xs font-medium transition ${
                    isActive
                      ? 'bg-[#161a22] text-white border border-[#262e3d]'
                      : 'text-[#949da8] hover:bg-[#0f1217] hover:text-[#f0f3f6]'
                  }`}
                >
                  <Icon className="h-3.5 w-3.5 text-[#949da8]" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Backend Connectivity Status Pill */}
        <div className="flex items-center gap-3">
          <div
            className={`flex items-center gap-1.5 rounded border px-2.5 py-1 font-mono text-[11px] transition ${
              connected === true
                ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
                : connected === false
                ? 'border-red-500/30 bg-red-500/10 text-red-400'
                : 'border-[#1e2430] bg-[#0f1217] text-[#949da8]'
            }`}
            title={
              connected === true
                ? `Connected to FastAPI (${health?.environment || 'dev'}, DB: ${health?.database.dialect || 'ok'}, LLM: ${health?.llm_provider || 'none'})`
                : 'Backend unreachable. Click Settings to review API URL.'
            }
          >
            {connected === true ? (
              <CheckCircle2 className="h-3 w-3" />
            ) : connected === false ? (
              <AlertCircle className="h-3 w-3" />
            ) : (
              <div className="h-2 w-2 animate-pulse rounded-full bg-[#949da8]" />
            )}
            <span>
              {connected === true
                ? 'Engine Online'
                : connected === false
                ? 'Engine Offline'
                : 'Checking...'}
            </span>
          </div>

          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden sm:flex items-center gap-1 text-xs text-[#949da8] hover:text-white transition"
          >
            <span>GitHub</span>
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      </div>
    </header>
  );
};
