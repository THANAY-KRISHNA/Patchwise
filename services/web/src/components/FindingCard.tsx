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
  const [feedbackError, setFeedbackError] = useState<string | null>(null);

  async function handleFeedback(verdict: FeedbackVerdict) {
    if (submitting) return;
    setSubmitting(true);
    setFeedbackError(null);

    try {
      await api.submitFeedback(reviewId, finding.id, { verdict });
      setFeedback(verdict);
    } catch (err: unknown) {
      setFeedbackError((err as Error)?.message || 'Failed to submit feedback');
    } finally {
      setSubmitting(false);
    }
  }

  const lineRangeDisplay =
    finding.start_line !== null
      ? finding.end_line && finding.end_line !== finding.start_line
        ? `L${finding.start_line}–L${finding.end_line}`
        : `L${finding.start_line}`
      : 'File-level';

  return (
    <div className="flex flex-col rounded-lg border border-[#262c36] bg-[#14171d] p-4 text-[#e6edf3] transition hover:border-[#384150]">
      {/* Top Header: Rule ID, Line Reference, Badges */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-[#20252e]">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-[#1e232b] text-blue-400 border border-[#2d3440]">
            {finding.rule_id}
          </span>
          <div className="flex items-center gap-1.5 text-xs text-[#8b949e]">
            <FileCode className="h-3.5 w-3.5 text-[#6e7681]" />
            <span className="font-mono text-xs text-white">{finding.file_path}</span>
            <span className="text-[#6e7681]">:</span>
            <span className="font-mono text-xs text-amber-300 font-medium">
              {lineRangeDisplay}
            </span>
          </div>

          {!isAnchoredInDiff && (
            <span className="rounded bg-amber-500/10 border border-amber-500/30 px-1.5 py-0.5 text-[10px] text-amber-400">
              Unanchored in Diff Hunk
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
        <h4 className="text-sm font-semibold text-white mb-1.5">{finding.title}</h4>
        <p className="text-xs text-[#8b949e] leading-relaxed whitespace-pre-wrap">
          {finding.explanation}
        </p>
      </div>

      {/* Suggested Fix */}
      {finding.suggested_fix && (
        <div className="mt-2.5 rounded-md border border-[#2a303c] bg-[#101217] p-3 text-xs">
          <div className="flex items-center gap-1.5 text-[#e6edf3] font-medium mb-1">
            <Wrench className="h-3.5 w-3.5 text-emerald-400" />
            <span>Suggested Remediation</span>
          </div>
          <p className="font-mono text-[11px] text-emerald-300/90 whitespace-pre-wrap">
            {finding.suggested_fix}
          </p>
        </div>
      )}

      {/* Human-in-the-loop Feedback Bar */}
      <div className="mt-3.5 pt-3 border-t border-[#20252e] flex flex-wrap items-center justify-between gap-2">
        <span className="text-[11px] text-[#6e7681]">Human Reviewer Feedback:</span>

        {feedback ? (
          <div className="flex items-center gap-1.5 rounded bg-emerald-500/10 border border-emerald-500/30 px-2.5 py-1 text-xs text-emerald-400">
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span>Marked as <strong className="capitalize">{feedback}</strong></span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5">
            {submitting && <Loader2 className="h-3.5 w-3.5 animate-spin text-[#8b949e]" />}
            <button
              onClick={() => handleFeedback('useful')}
              disabled={submitting}
              className="flex items-center gap-1 rounded border border-[#2d3440] bg-[#161920] px-2.5 py-1 text-xs text-[#8b949e] hover:bg-emerald-500/10 hover:text-emerald-400 hover:border-emerald-500/30 transition disabled:opacity-50"
              title="Mark finding as accurate and helpful"
            >
              <ThumbsUp className="h-3 w-3" />
              Useful
            </button>
            <button
              onClick={() => handleFeedback('incorrect')}
              disabled={submitting}
              className="flex items-center gap-1 rounded border border-[#2d3440] bg-[#161920] px-2.5 py-1 text-xs text-[#8b949e] hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/30 transition disabled:opacity-50"
              title="Mark finding as a false positive or hallucination"
            >
              <ThumbsDown className="h-3 w-3" />
              Incorrect
            </button>
            <button
              onClick={() => handleFeedback('irrelevant')}
              disabled={submitting}
              className="flex items-center gap-1 rounded border border-[#2d3440] bg-[#161920] px-2.5 py-1 text-xs text-[#8b949e] hover:bg-zinc-500/10 hover:text-zinc-300 hover:border-zinc-500/30 transition disabled:opacity-50"
              title="Mark finding as technically true but not applicable or low value"
            >
              <HelpCircle className="h-3 w-3" />
              Irrelevant
            </button>
          </div>
        )}

        {feedbackError && (
          <span className="w-full text-right text-[11px] text-red-400">
            {feedbackError}
          </span>
        )}
      </div>
    </div>
  );
};
