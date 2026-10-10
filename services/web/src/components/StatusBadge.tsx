import React from 'react';
import {
  Shield,
  Sparkles,
  CheckCircle,
  AlertOctagon,
  AlertTriangle,
  Info,
  Clock,
  Loader2,
  XCircle,
} from 'lucide-react';
import { FindingProvenance, FindingSeverity, ReviewStatus } from '../types';

interface SeverityBadgeProps {
  severity: FindingSeverity;
  size?: 'sm' | 'md';
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({
  severity,
  size = 'md',
}) => {
  const configs: Record<
    FindingSeverity,
    { label: string; bg: string; text: string; border: string; icon: React.ComponentType<{ className?: string }> }
  > = {
    critical: {
      label: 'Critical',
      bg: 'bg-red-500/10',
      text: 'text-red-400',
      border: 'border-red-500/30',
      icon: AlertOctagon,
    },
    high: {
      label: 'High',
      bg: 'bg-orange-500/10',
      text: 'text-orange-400',
      border: 'border-orange-500/30',
      icon: AlertTriangle,
    },
    medium: {
      label: 'Medium',
      bg: 'bg-amber-500/10',
      text: 'text-amber-400',
      border: 'border-amber-500/30',
      icon: AlertTriangle,
    },
    low: {
      label: 'Low',
      bg: 'bg-blue-500/10',
      text: 'text-blue-400',
      border: 'border-blue-500/30',
      icon: Info,
    },
    info: {
      label: 'Info',
      bg: 'bg-zinc-500/10',
      text: 'text-zinc-400',
      border: 'border-zinc-500/30',
      icon: Info,
    },
  };

  const config = configs[severity] || configs.info;
  const Icon = config.icon;
  const sizeClasses =
    size === 'sm' ? 'px-1.5 py-0.5 text-[10px]' : 'px-2 py-0.5 text-xs';

  return (
    <span
      className={`inline-flex items-center gap-1 font-medium rounded border ${config.bg} ${config.text} ${config.border} ${sizeClasses}`}
    >
      <Icon className={size === 'sm' ? 'h-2.5 w-2.5' : 'h-3 w-3'} />
      {config.label}
    </span>
  );
};

interface ProvenanceBadgeProps {
  source: FindingProvenance;
  showDetails?: boolean;
}

export const ProvenanceBadge: React.FC<ProvenanceBadgeProps> = ({
  source,
  showDetails = false,
}) => {
  if (source === 'DETERMINISTIC_STATIC_ANALYSIS') {
    return (
      <span
        className="inline-flex items-center gap-1.5 rounded border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[11px] font-medium text-emerald-400"
        title="Tier 1: High-confidence deterministic rule backed by AST verification (0% hallucination risk)."
      >
        <Shield className="h-3 w-3" />
        Deterministic Static Rule
        {showDetails && <span className="opacity-75">(Tier 1)</span>}
      </span>
    );
  }

  if (source === 'AI_GENERATED_HYPOTHESIS') {
    return (
      <span
        className="inline-flex items-center gap-1.5 rounded border border-purple-500/30 bg-purple-500/10 px-2 py-0.5 text-[11px] font-medium text-purple-300"
        title="Tier 2: AI-generated suggestion grounded to diff lines. Explicitly unverified hypothesis."
      >
        <Sparkles className="h-3 w-3" />
        AI Hypothesis
        <span className="rounded bg-purple-500/20 px-1 py-0.2 text-[9px] uppercase tracking-wider text-purple-300">
          Unverified
        </span>
      </span>
    );
  }

  return (
    <span
      className="inline-flex items-center gap-1.5 rounded border border-cyan-500/30 bg-cyan-500/10 px-2 py-0.5 text-[11px] font-medium text-cyan-300"
      title="Tier 3: Verified test result or concrete test execution heuristic."
    >
      <CheckCircle className="h-3 w-3" />
      Verified Test Result
      {showDetails && <span className="opacity-75">(Tier 3)</span>}
    </span>
  );
};

interface ReviewStatusBadgeProps {
  status: ReviewStatus;
}

export const ReviewStatusBadge: React.FC<ReviewStatusBadgeProps> = ({ status }) => {
  const configs: Record<
    ReviewStatus,
    { label: string; bg: string; text: string; border: string; icon: React.ComponentType<{ className?: string }> }
  > = {
    completed: {
      label: 'Completed',
      bg: 'bg-emerald-500/10',
      text: 'text-emerald-400',
      border: 'border-emerald-500/30',
      icon: CheckCircle,
    },
    in_progress: {
      label: 'Analyzing',
      bg: 'bg-blue-500/10',
      text: 'text-blue-400',
      border: 'border-blue-500/30',
      icon: Loader2,
    },
    queued: {
      label: 'Queued',
      bg: 'bg-zinc-500/10',
      text: 'text-zinc-400',
      border: 'border-zinc-500/30',
      icon: Clock,
    },
    failed: {
      label: 'Failed',
      bg: 'bg-red-500/10',
      text: 'text-red-400',
      border: 'border-red-500/30',
      icon: XCircle,
    },
  };

  const config = configs[status] || configs.queued;
  const Icon = config.icon;

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${config.bg} ${config.text} ${config.border}`}
    >
      <Icon className={`h-3 w-3 ${status === 'in_progress' ? 'animate-spin' : ''}`} />
      {config.label}
    </span>
  );
};
