import React, { Suspense } from 'react';
import type { Metadata } from 'next';
import './globals.css';
import { WorkstationShell } from '../components/Layout/WorkstationShell';

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
    <html lang="en" className="h-full bg-[#090a0d]">
      <body className="h-full overflow-hidden bg-[#090a0d] text-[#f0f3f6]">
        <Suspense fallback={<div className="h-screen w-full bg-[#090a0d]" />}>
          <WorkstationShell>
            {children}
          </WorkstationShell>
        </Suspense>
      </body>
    </html>
  );
}
