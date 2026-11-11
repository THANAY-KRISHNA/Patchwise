'use client';

import React, { useState } from 'react';
import {
  ThumbsUp,
  ThumbsDown,
  HelpCircle,
  FileCode,
  CheckCircle2,
  Wrench,
  Loader2,
  Copy,
  Check,
} from 'lucide-react';
import { FeedbackVerdict, Finding } from '../types';
import { ProvenanceBadge, SeverityBadge } from './StatusBadge';
import { api } from '../lib/api';

interface FindingCardProps {
  finding: Finding;
  reviewId: string;
  isAnchoredInDiff?: boolean;
}

export const FindingCard: React.FC<FindingCardProps> = ({
  finding,
  reviewId,
  isAnchoredInDiff = true,
}) => {
  const [feedback, setFeedback] = useState<FeedbackVerdict | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [copiedFix, setCopiedFix] = useState(false);

  async function handleFeedback(verdict: FeedbackVerdict) {
    if (submitting) return;
    setSubmitting(true);

    try {
      await api.submitFeedback(reviewId, finding.id, { verdict });
      setFeedback(verdict);
    } catch {
      // Allow user to retry
    } finally {
      setSubmitting(false);
    }
  }

  const handleCopyFix = () => {
    if (!finding.suggested_fix) return;
    navigator.clipboard.writeText(finding.suggested_fix);
    setCopiedFix(true);
    setTimeout(() => setCopiedFix(false), 2000);
  };

  const lineRangeDisplay =
    finding.start_line !== null
      ? finding.end_line && finding.end_line !== finding.start_line
        ? `L${finding.start_line}–L${finding.end_line}`
        : `L${finding.start_line}`
      : 'File-level';

  return (
    <div className="flex flex-col rounded border border-[#1e222b] bg-[#101217] p-4 text-[#f0f3f6] transition hover:border-[#282e3c]">
      {/* Header: Rule ID, File Path & Line, Provenance & Severity */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-[#1e222b]">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-[#161820] text-amber-400 border border-[#262c37]">
            {finding.rule_id}
          </span>
          <div className="flex items-center gap-1.5 text-xs text-[#949da8]">
            <FileCode className="h-3.5 w-3.5 text-[#656e7b]" />
            <span className="font-mono text-xs text-white">{finding.file_path}</span>
            <span className="text-[#656e7b]">:</span>
            <span className="font-mono text-xs text-amber-400 font-medium">
              {lineRangeDisplay}
            </span>
          </div>

          {!isAnchoredInDiff && (
            <span className="rounded bg-amber-500/10 border border-amber-500/30 px-1.5 py-0.5 font-mono text-[10px] text-amber-400">
              Unanchored Hunk
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <ProvenanceBadge source={finding.source} />
          <SeverityBadge severity={finding.severity} size="sm" />
        </div>
      </div>

      {/* Title & Explanation */}
      <div className="pt-3 pb-2">
        <h4 className="text-sm font-semibold text-white mb-1">{finding.title}</h4>
        <p className="text-xs text-[#949da8] leading-relaxed whitespace-pre-wrap">
          {finding.explanation}
        </p>
      </div>

      {/* Suggested Fix Code Block */}
      {finding.suggested_fix && (
        <div className="mt-2.5 rounded border border-[#1e222b] bg-[#090a0d] p-3 text-xs">
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-1.5 text-emerald-400 font-medium font-mono text-[11px]">
              <Wrench className="h-3.5 w-3.5" />
              <span>Suggested Remediation</span>
            </div>
            <button
              onClick={handleCopyFix}
              className="flex items-center gap-1 text-[10px] font-mono text-[#656e7b] hover:text-[#949da8] transition"
              title="Copy remediation code"
            >
              {copiedFix ? (
                <>
                  <Check className="h-3 w-3 text-emerald-400" />
                  <span className="text-emerald-400">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="h-3 w-3" />
                  <span>Copy</span>
                </>
              )}
            </button>
          </div>
          <pre className="font-mono text-[11px] text-emerald-300/90 whitespace-pre-wrap overflow-x-auto p-2 rounded bg-[#101217] border border-[#1e222b]">
            {finding.suggested_fix}
          </pre>
        </div>
      )}

      {/* Reviewer Feedback Bar */}
      <div className="mt-3.5 pt-3 border-t border-[#1e222b] flex flex-wrap items-center justify-between gap-2">
        <span className="text-[11px] text-[#656e7b] font-mono">Reviewer Verification:</span>

        {feedback ? (
          <div className="flex items-center gap-1.5 rounded bg-emerald-500/10 border border-emerald-500/30 px-2.5 py-1 text-xs text-emerald-400 font-mono">
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span>Marked as <strong className="capitalize">{feedback}</strong></span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 font-mono text-xs">
            {submitting && <Loader2 className="h-3.5 w-3.5 animate-spin text-[#949da8]" />}
            <button
              onClick={() => handleFeedback('useful')}
              disabled={submitting}
              className="flex items-center gap-1 rounded border border-[#1e222b] bg-[#161820] px-2.5 py-1 text-[#949da8] hover:bg-emerald-500/10 hover:text-emerald-400 hover:border-emerald-500/30 transition disabled:opacity-50"
              title="Mark finding as accurate and helpful"
            >
              <ThumbsUp className="h-3 w-3" />
              <span>Useful</span>
            </button>
            <button
              onClick={() => handleFeedback('incorrect')}
              disabled={submitting}
              className="flex items-center gap-1 rounded border border-[#1e222b] bg-[#161820] px-2.5 py-1 text-[#949da8] hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/30 transition disabled:opacity-50"
              title="Mark finding as a false positive or hallucination"
            >
              <ThumbsDown className="h-3 w-3" />
              <span>Incorrect</span>
            </button>
            <button
              onClick={() => handleFeedback('irrelevant')}
              disabled={submitting}
              className="flex items-center gap-1 rounded border border-[#1e222b] bg-[#161820] px-2.5 py-1 text-[#949da8] hover:bg-[#1f232d] hover:text-white transition disabled:opacity-50"
              title="Mark finding as non-actionable or irrelevant"
            >
              <HelpCircle className="h-3 w-3" />
              <span>Irrelevant</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
