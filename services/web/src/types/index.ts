/**
 * Strict TypeScript types for Patchwise matching FastAPI backend schemas.
 */

export type ReviewStatus = 'queued' | 'in_progress' | 'completed' | 'failed';

export type FindingSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';

export type FindingProvenance =
  | 'DETERMINISTIC_STATIC_ANALYSIS'
  | 'AI_GENERATED_HYPOTHESIS'
  | 'VERIFIED_TEST_RESULT';

export type FindingCategory =
  | 'input_validation'
  | 'exception_handling'
  | 'boundary_condition'
  | 'resource_cleanup'
  | 'security_pattern'
  | 'test_suggestion'
  | 'code_quality';

export type FeedbackVerdict = 'useful' | 'incorrect' | 'irrelevant';

export interface Finding {
  id: string;
  review_id: string;
  rule_id: string;
  source: FindingProvenance;
  severity: FindingSeverity;
  category: FindingCategory;
  file_path: string;
  start_line: number | null;
  end_line: number | null;
  title: string;
  explanation: string;
  suggested_fix?: string | null;
  fingerprint?: string | null;
  created_at: string;
}

export interface ReviewSummary {
  total_findings: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  info_count: number;
  deterministic_count: number;
  ai_hypothesis_count: number;
  verified_test_count: number;
}

export interface Review {
  id: string;
  repository: string;
  pr_number: number;
  pr_title?: string | null;
  commit_sha?: string | null;
  status: ReviewStatus;
  engine_version: string;
  started_at: string;
  completed_at?: string | null;
  duration_ms?: number | null;
  error_code?: string | null;
  summary: ReviewSummary;
  findings: Finding[];
}

export interface ReviewSubmissionRequest {
  repository_url: string;
  pull_request_number?: number | null;
}

export interface FeedbackCreate {
  verdict: FeedbackVerdict;
  comment?: string | null;
}

export interface FeedbackRead {
  id: string;
  finding_id: string;
  verdict: FeedbackVerdict;
  comment?: string | null;
  created_at: string;
}

export interface DiffLine {
  type: '+' | '-' | ' ';
  content: string;
  old_line_number?: number | null;
  new_line_number?: number | null;
}

export interface ParsedHunk {
  old_start: number;
  old_length: number;
  new_start: number;
  new_length: number;
  header: string;
  lines: DiffLine[];
  added_lines: number[];
  deleted_lines: number[];
  context_lines: number[];
}

export interface ParsedFileDiff {
  file_path: string;
  old_path?: string | null;
  is_new_file: boolean;
  is_deleted_file: boolean;
  is_renamed_file: boolean;
  is_binary: boolean;
  hunks: ParsedHunk[];
  added_lines: number[];
  deleted_lines: number[];
}

export interface DiffInspectionResponse {
  repository: string;
  pr_number: number;
  title: string;
  base_commit_sha: string;
  head_commit_sha: string;
  total_files_changed: number;
  total_added_lines: number;
  total_deleted_lines: number;
  files: ParsedFileDiff[];
}

export interface DatabaseHealth {
  connected: boolean;
  dialect: string;
  error?: string | null;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded';
  version: string;
  environment: string;
  timestamp: string;
  database: DatabaseHealth;
  llm_provider: string;
  active_plugins: string[];
}

export interface LanguagePluginMetadata {
  language_id: string;
  display_name: string;
  file_extensions: string[];
  status: 'active' | 'in_development';
  version: string;
  rules_count: number;
}

export interface PluginsOverviewResponse {
  plugins: LanguagePluginMetadata[];
}

export interface RuleMetrics {
  rule_id: string;
  tp: number;
  fp: number;
  fn: number;
  precision: number | null;
  recall: number | null;
  f1: number | null;
}

export interface AggregateMetrics {
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  tp: number;
  fp: number;
  fn: number;
  tn: number;
  fp_cases: number;
  precision: number | null;
  recall: number | null;
  f1: number | null;
  false_positive_rate: number | null;
  total_latency_ms: number;
  mean_latency_ms: number;
  median_latency_ms: number;
  p95_latency_ms: number;
  per_rule: Record<string, RuleMetrics>;
}

export interface CaseOutcome {
  case_id: string;
  case_name: string;
  passed: boolean;
  tp: number;
  fp: number;
  fn: number;
  tn: number;
  case_fp: number;
  latency_ms: number;
  expected_count: number;
  actual_count: number;
  matched_rules: string[];
  unmatched_expected: string[];
  unexpected_actual: string[];
  details: string;
}

export interface BenchmarkRunSummary {
  dataset_name: string;
  dataset_version: string;
  engine_version: string;
  provider: string;
  timestamp: string;
  metrics: AggregateMetrics;
  case_outcomes: CaseOutcome[];
}
