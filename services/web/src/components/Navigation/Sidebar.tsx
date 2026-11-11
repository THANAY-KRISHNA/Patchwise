'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  GitPullRequest,
  BarChart3,
  Settings,
  Shield,
  Code2,
} from 'lucide-react';

interface SidebarProps {
  onCloseMobile?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ onCloseMobile }) => {
  const pathname = usePathname();

  const navItems = [
    { label: 'Overview', href: '/', icon: LayoutDashboard },
    { label: 'Pull Requests', href: '/reviews', icon: GitPullRequest },
    { label: 'Benchmarks', href: '/benchmark', icon: BarChart3 },
    { label: 'Settings', href: '/settings', icon: Settings },
  ];

  const activeLanguages = [
    { id: 'python', label: 'Python', rules: 'PY001–005' },
    { id: 'javascript', label: 'JS / TS', rules: 'JS001–004' },
    { id: 'java', label: 'Java', rules: 'JV001–004' },
    { id: 'cpp', label: 'C / C++', rules: 'CC001–004' },
    { id: 'sql', label: 'SQL / Hive', rules: 'SQL001–005' },
  ];

  return (
    <aside className="flex h-full w-64 flex-col border-r border-[#1e222b] bg-[#101217] text-[#949da8]">
      {/* Brand & Workspace ID */}
      <div className="flex h-14 items-center justify-between border-b border-[#1e222b] px-4">
        <Link
          href="/"
          onClick={onCloseMobile}
          className="flex items-center gap-2.5 font-semibold text-white transition hover:opacity-95"
        >
          <div className="flex h-7 w-7 items-center justify-center rounded border border-amber-500/40 bg-amber-500/10 font-mono text-xs font-bold text-amber-400">
            PW
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold tracking-tight text-[#f0f3f6]">Patchwise</span>
            <span className="font-mono text-[10px] text-[#656e7b]">Developer Workstation</span>
          </div>
        </Link>
        <span className="rounded border border-[#1e222b] bg-[#161820] px-1.5 py-0.5 font-mono text-[10px] text-[#656e7b]">
          v0.1.0
        </span>
      </div>

      {/* Primary Navigation Rail */}
      <nav className="flex-1 space-y-1 p-3">
        <div className="px-2 py-1 text-[10px] font-mono uppercase tracking-wider text-[#656e7b]">
          Navigation
        </div>
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
              onClick={onCloseMobile}
              className={`flex items-center justify-between rounded px-2.5 py-2 text-xs font-medium transition ${
                isActive
                  ? 'border border-[#262c37] bg-[#161820] text-white shadow-sm'
                  : 'hover:bg-[#161820] hover:text-[#f0f3f6]'
              }`}
            >
              <div className="flex items-center gap-2.5">
                <Icon
                  className={`h-4 w-4 ${
                    isActive ? 'text-amber-400' : 'text-[#656e7b]'
                  }`}
                />
                <span>{item.label}</span>
              </div>
              {isActive && (
                <div className="h-1.5 w-1.5 rounded-full bg-amber-400" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Language Analyzers Status Drawer */}
      <div className="border-t border-[#1e222b] p-3 bg-[#0d0e12]">
        <div className="flex items-center justify-between px-2 mb-2 text-[10px] font-mono uppercase tracking-wider text-[#656e7b]">
          <span className="flex items-center gap-1">
            <Code2 className="h-3 w-3 text-amber-400" />
            Analyzers Active
          </span>
          <span className="text-emerald-400 font-semibold">5 / 5</span>
        </div>

        <div className="space-y-1">
          {activeLanguages.map((lang) => (
            <div
              key={lang.id}
              className="flex items-center justify-between rounded px-2 py-1 text-[11px] font-mono bg-[#111318] border border-[#1e222b]/60 text-[#949da8]"
            >
              <span className="text-[#f0f3f6]">{lang.label}</span>
              <span className="text-[10px] text-[#656e7b]">{lang.rules}</span>
            </div>
          ))}
        </div>

        <div className="mt-3 flex items-center gap-1.5 px-2 text-[10px] font-mono text-emerald-400">
          <Shield className="h-3 w-3" />
          <span>Deterministic AST Grounding</span>
        </div>
      </div>
    </aside>
  );
};

