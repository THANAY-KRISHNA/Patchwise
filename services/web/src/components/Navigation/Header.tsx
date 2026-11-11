'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Menu,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Key,
  ChevronRight,
} from 'lucide-react';
import { api, getStoredApiKey } from '../../lib/api';
import { HealthResponse } from '../../types';

interface HeaderProps {
  onToggleMobileMenu?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onToggleMobileMenu }) => {
  const pathname = usePathname();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [connected, setConnected] = useState<boolean | null>(null);
  const [hasApiKey, setHasApiKey] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      return !!getStoredApiKey();
    }
    return false;
  });

  useEffect(() => {
    let isMounted = true;

    async function checkHealth() {
      try {
        const data = await api.getHealth();
        if (isMounted) {
          setHealth(data);
          setConnected(data.status === 'healthy');
          setHasApiKey(!!getStoredApiKey());
        }
      } catch {
        if (isMounted) {
          setConnected(false);
          setHasApiKey(!!getStoredApiKey());
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

  // Compute breadcrumbs
  const getBreadcrumbs = () => {
    if (pathname === '/') {
      return [{ label: 'Workstation', href: '/' }, { label: 'Overview' }];
    }
    if (pathname === '/reviews') {
      return [{ label: 'Workstation', href: '/' }, { label: 'Pull Requests' }];
    }
    if (pathname.startsWith('/reviews/')) {
      const reviewId = pathname.split('/')[2];
      const isDemo = reviewId === 'demo';
      return [
        { label: 'Workstation', href: '/' },
        { label: 'Pull Requests', href: '/reviews' },
        { label: isDemo ? 'Demo PR #42' : `Review ${reviewId.slice(0, 8)}...` },
      ];
    }
    if (pathname === '/benchmark') {
      return [{ label: 'Workstation', href: '/' }, { label: 'Benchmarks' }];
    }
    if (pathname === '/settings') {
      return [{ label: 'Workstation', href: '/' }, { label: 'Settings' }];
    }
    return [{ label: 'Workstation', href: '/' }, { label: pathname.slice(1) }];
  };

  const breadcrumbs = getBreadcrumbs();

  return (
    <header className="sticky top-0 z-40 flex h-14 w-full items-center justify-between border-b border-[#1e222b] bg-[#090a0d]/95 px-4 backdrop-blur-sm sm:px-6">
      <div className="flex items-center gap-3">
        {/* Mobile menu button */}
        <button
          onClick={onToggleMobileMenu}
          className="flex h-8 w-8 items-center justify-center rounded border border-[#1e222b] bg-[#101217] text-[#949da8] hover:text-white md:hidden"
          aria-label="Toggle navigation menu"
        >
          <Menu className="h-4 w-4" />
        </button>

        {/* Breadcrumb Trail */}
        <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 font-mono text-xs">
          {breadcrumbs.map((crumb, idx) => {
            const isLast = idx === breadcrumbs.length - 1;
            return (
              <React.Fragment key={idx}>
                {idx > 0 && <ChevronRight className="h-3 w-3 text-[#656e7b]" />}
                {crumb.href && !isLast ? (
                  <Link
                    href={crumb.href}
                    className="text-[#656e7b] hover:text-[#949da8] transition"
                  >
                    {crumb.label}
                  </Link>
                ) : (
                  <span className={isLast ? 'text-[#f0f3f6] font-medium' : 'text-[#656e7b]'}>
                    {crumb.label}
                  </span>
                )}
              </React.Fragment>
            );
          })}
        </nav>
      </div>

      {/* Right Controls & Telemetry Pills */}
      <div className="flex items-center gap-3 font-mono text-xs">
        {/* API Key Status Pill */}
        <Link
          href="/settings"
          className={`hidden sm:flex items-center gap-1.5 rounded border px-2 py-0.5 text-[11px] transition ${
            hasApiKey
              ? 'border-amber-500/30 bg-amber-500/10 text-amber-400'
              : 'border-[#1e222b] bg-[#101217] text-[#656e7b] hover:text-[#949da8]'
          }`}
          title={hasApiKey ? 'Production API Key Configured' : 'No API Key Configured (Development Mode)'}
        >
          <Key className="h-3 w-3" />
          <span>{hasApiKey ? 'API Key Active' : 'Dev Auth'}</span>
        </Link>

        {/* Engine Connectivity Status Pill */}
        <div
          className={`flex items-center gap-1.5 rounded border px-2.5 py-0.5 text-[11px] transition ${
            connected === true
              ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
              : connected === false
              ? 'border-red-500/30 bg-red-500/10 text-red-400'
              : 'border-[#1e222b] bg-[#101217] text-[#949da8]'
          }`}
          title={
            connected === true
              ? `Connected to FastAPI (${health?.environment || 'dev'}, DB: ${health?.database.dialect || 'ok'}, LLM: ${health?.llm_provider || 'none'})`
              : 'Backend unreachable. Check server connection.'
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
              : 'Connecting...'}
          </span>
        </div>

        {/* External GitHub link */}
        <a
          href="https://github.com"
          target="_blank"
          rel="noopener noreferrer"
          className="hidden md:flex items-center gap-1 text-[11px] text-[#656e7b] hover:text-[#f0f3f6] transition"
        >
          <span>GitHub</span>
          <ExternalLink className="h-3 w-3" />
        </a>
      </div>
    </header>
  );
};
