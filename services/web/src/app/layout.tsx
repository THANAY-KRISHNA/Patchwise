import React, { Suspense } from 'react';
import type { Metadata } from 'next';
import './globals.css';
import { Navbar } from '../components/Navbar';

export const metadata: Metadata = {
  title: 'Patchwise — Pull Request Review & Testing Assistant',
  description:
    'AI-powered and deterministic multi-language pull request review engine with strict diff line grounding.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full bg-[#0d0f12]">
      <body className="flex min-h-screen flex-col bg-[#0d0f12] text-[#e6edf3]">
        <Suspense fallback={<div className="h-14 bg-[#0d0f12] border-b border-[#262c36]" />}>
          <Navbar />
        </Suspense>
        <main className="flex-1">
          {children}
        </main>
        <footer className="border-t border-[#262c36] bg-[#0d0f12] py-4 text-center text-xs text-[#6e7681]">
          <div className="mx-auto max-w-7xl px-4 flex flex-wrap items-center justify-between gap-2">
            <span>Patchwise v0.1.0 • Multi-Language PR Review & Static Analyzer</span>
            <span>Zero untrusted code execution • Provenance-isolated findings</span>
          </div>
        </footer>
      </body>
    </html>
  );
}
