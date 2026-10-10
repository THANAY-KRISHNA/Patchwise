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
    <header className="sticky top-0 z-50 border-b border-[#262c36] bg-[#0d0f12]/95 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
        {/* Brand */}
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2.5 font-semibold tracking-tight text-white transition hover:opacity-90">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-blue-600 font-mono text-sm font-bold text-white shadow-sm">
              PW
            </div>
            <span className="text-base font-bold tracking-tight">Patchwise</span>
            <span className="rounded border border-[#303642] bg-[#161920] px-1.5 py-0.5 text-[10px] font-medium text-[#8b949e]">
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
                  className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-xs font-medium transition ${
                    isActive
                      ? 'bg-[#20252e] text-white shadow-sm'
                      : 'text-[#8b949e] hover:bg-[#161920] hover:text-[#e6edf3]'
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Backend Connectivity Status Pill */}
        <div className="flex items-center gap-3">
          <div
            className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium transition ${
              connected === true
                ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
                : connected === false
                ? 'border-amber-500/30 bg-amber-500/10 text-amber-400'
                : 'border-[#262c36] bg-[#161920] text-[#8b949e]'
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
              <div className="h-2 w-2 animate-pulse rounded-full bg-[#8b949e]" />
            )}
            <span>
              {connected === true
                ? 'API Connected'
                : connected === false
                ? 'API Disconnected'
                : 'Connecting...'}
            </span>
          </div>

          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden sm:flex items-center gap-1 text-xs text-[#8b949e] hover:text-white transition"
          >
            GitHub
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      </div>
    </header>
  );
};
