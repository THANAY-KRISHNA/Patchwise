import React from 'react';
import { ReviewSummary } from '../types';

interface SeverityBarProps {
  summary: ReviewSummary;
  showLegend?: boolean;
}

export const SeverityBar: React.FC<SeverityBarProps> = ({
  summary,
  showLegend = true,
}) => {
  const total = summary.total_findings;

  if (total === 0) {
    return (
      <div className="flex flex-col gap-1.5">
        <div className="h-2 w-full rounded-full bg-[#1e232b]" />
        {showLegend && (
          <span className="text-xs text-[#6e7681]">Zero findings flagged</span>
        )}
      </div>
    );
  }

  const critPct = (summary.critical_count / total) * 100;
  const highPct = (summary.high_count / total) * 100;
  const medPct = (summary.medium_count / total) * 100;
  const lowPct = (summary.low_count / total) * 100;
  const infoPct = (summary.info_count / total) * 100;

  return (
    <div className="flex flex-col gap-2">
      <div className="flex h-2 w-full overflow-hidden rounded-full bg-[#1e232b]">
        {critPct > 0 && (
          <div
            style={{ width: `${critPct}%` }}
            className="bg-red-500 transition-all"
            title={`Critical: ${summary.critical_count}`}
          />
        )}
        {highPct > 0 && (
          <div
            style={{ width: `${highPct}%` }}
            className="bg-orange-500 transition-all"
            title={`High: ${summary.high_count}`}
          />
        )}
        {medPct > 0 && (
          <div
            style={{ width: `${medPct}%` }}
            className="bg-amber-400 transition-all"
            title={`Medium: ${summary.medium_count}`}
          />
        )}
        {lowPct > 0 && (
          <div
            style={{ width: `${lowPct}%` }}
            className="bg-blue-400 transition-all"
            title={`Low: ${summary.low_count}`}
          />
        )}
        {infoPct > 0 && (
          <div
            style={{ width: `${infoPct}%` }}
            className="bg-zinc-500 transition-all"
            title={`Info: ${summary.info_count}`}
          />
        )}
      </div>

      {showLegend && (
        <div className="flex flex-wrap items-center gap-3 text-xs text-[#8b949e]">
          {summary.critical_count > 0 && (
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-red-500" />
              <span>Critical: {summary.critical_count}</span>
            </span>
          )}
          {summary.high_count > 0 && (
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-orange-500" />
              <span>High: {summary.high_count}</span>
            </span>
          )}
          {summary.medium_count > 0 && (
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-amber-400" />
              <span>Medium: {summary.medium_count}</span>
            </span>
          )}
          {summary.low_count > 0 && (
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-blue-400" />
              <span>Low: {summary.low_count}</span>
            </span>
          )}
          {summary.info_count > 0 && (
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-zinc-500" />
              <span>Info: {summary.info_count}</span>
            </span>
          )}
        </div>
      )}
    </div>
  );
};
