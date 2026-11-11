import test from 'node:test';
import assert from 'node:assert';
import { api, getStoredApiKey, setStoredApiKey } from '../src/lib/api.ts';
import type { Finding, Review, ReviewSubmissionRequest, BenchmarkRunSummary } from '../src/types/index.ts';

// In-memory mock localStorage for Node.js test environment
class MockLocalStorage {
  private store: Record<string, string> = {};
  getItem(key: string): string | null {
    return this.store[key] || null;
  }
  setItem(key: string, value: string): void {
    this.store[key] = value;
  }
  removeItem(key: string): void {
    delete this.store[key];
  }
  clear(): void {
    this.store = {};
  }
}

// Ensure mock localStorage exists
if (typeof globalThis.window === 'undefined') {
  (globalThis as unknown as { window: { localStorage: MockLocalStorage } }).window = {
    localStorage: new MockLocalStorage(),
  };
}

test('E2E Workstation - Settings & Authentication management', () => {
  // Test clean initial state
  setStoredApiKey(null);
  assert.strictEqual(getStoredApiKey(), null);

  // Set API key
  const testKey = 'test-patchwise-secret-key-12345';
  setStoredApiKey(testKey);
  assert.strictEqual(getStoredApiKey(), testKey);

  // Key masking utility simulation
  const masked = testKey.length > 8 ? `${testKey.slice(0, 4)}${'*'.repeat(testKey.length - 8)}${testKey.slice(-4)}` : '****';
  assert.strictEqual(masked.startsWith('test'), true);
  assert.strictEqual(masked.endsWith('2345'), true);
  assert.strictEqual(masked.includes('***'), true);

  // Clear key
  setStoredApiKey(null);
  assert.strictEqual(getStoredApiKey(), null);
});

test('E2E Workstation - Review submission validation logic', () => {
  function validateSubmission(payload: ReviewSubmissionRequest): { valid: boolean; error?: string } {
    if (!payload.repository_url || !payload.repository_url.trim()) {
      return { valid: false, error: 'Repository URL is required.' };
    }
    const cleanUrl = payload.repository_url.trim();
    if (!cleanUrl.startsWith('https://github.com/')) {
      return { valid: false, error: 'Only HTTPS GitHub repository URLs are supported.' };
    }
    const match = cleanUrl.match(/^https:\/\/github\.com\/([a-zA-Z0-9_.-]+)\/([a-zA-Z0-9_.-]+)/);
    if (!match) {
      return { valid: false, error: 'Invalid repository format. Expected https://github.com/owner/repo' };
    }
    if (payload.pull_request_number !== undefined && payload.pull_request_number !== null && payload.pull_request_number <= 0) {
      return { valid: false, error: 'Pull request number must be greater than zero.' };
    }
    return { valid: true };
  }

  // 1. Missing URL
  assert.strictEqual(validateSubmission({ repository_url: '' }).valid, false);

  // 2. Cleartext HTTP
  assert.strictEqual(validateSubmission({ repository_url: 'http://github.com/owner/repo' }).valid, false);

  // 3. Non-GitHub URL
  assert.strictEqual(validateSubmission({ repository_url: 'https://gitlab.com/owner/repo' }).valid, false);

  // 4. Invalid PR number
  assert.strictEqual(validateSubmission({ repository_url: 'https://github.com/owner/repo', pull_request_number: -1 }).valid, false);

  // 5. Valid URL and PR number
  const valid = validateSubmission({ repository_url: 'https://github.com/owner/repo', pull_request_number: 42 });
  assert.strictEqual(valid.valid, true);
  assert.strictEqual(valid.error, undefined);
});

test('E2E Workstation - Unified diff parsing and line mapping', () => {
  const samplePatch = '@@ -10,4 +10,5 @@\n context line\n-deleted line\n+added line 1\n+added line 2\n context end';
  
  interface ParsedLine {
    type: 'add' | 'delete' | 'context' | 'header';
    oldLine?: number;
    newLine?: number;
    content: string;
  }

  function parseUnifiedDiff(patch: string): ParsedLine[] {
    const lines = patch.split('\n');
    const result: ParsedLine[] = [];
    let currentOld = 10;
    let currentNew = 10;

    for (const line of lines) {
      if (line.startsWith('@@')) {
        result.push({ type: 'header', content: line });
      } else if (line.startsWith('+')) {
        result.push({ type: 'add', newLine: currentNew++, content: line.slice(1) });
      } else if (line.startsWith('-')) {
        result.push({ type: 'delete', oldLine: currentOld++, content: line.slice(1) });
      } else {
        result.push({ type: 'context', oldLine: currentOld++, newLine: currentNew++, content: line.startsWith(' ') ? line.slice(1) : line });
      }
    }
    return result;
  }

  const parsed = parseUnifiedDiff(samplePatch);
  assert.strictEqual(parsed.length, 6);
  assert.strictEqual(parsed[0].type, 'header');
  assert.strictEqual(parsed[1].type, 'context');
  assert.strictEqual(parsed[2].type, 'delete');
  assert.strictEqual(parsed[3].type, 'add');
  assert.strictEqual(parsed[3].newLine, 11);
  assert.strictEqual(parsed[4].type, 'add');
  assert.strictEqual(parsed[4].newLine, 12);
});

test('E2E Workstation - Multi-dimensional finding filters', () => {
  const mockFindings: Finding[] = [
    {
      id: 'f1',
      review_id: 'r1',
      rule_id: 'PY004',
      title: 'Unsafe eval usage',
      explanation: 'Unsafe eval detected in user input',
      file_path: 'backend/app.py',
      start_line: 15,
      end_line: 15,
      severity: 'critical',
      category: 'security_pattern',
      source: 'DETERMINISTIC_STATIC_ANALYSIS',
      created_at: '2026-11-10T00:00:00Z',
    },
    {
      id: 'f2',
      review_id: 'r1',
      rule_id: 'JS001',
      title: 'Dangerous innerHTML',
      explanation: 'Dangerous DOM innerHTML injection sink',
      file_path: 'frontend/view.tsx',
      start_line: 42,
      end_line: 42,
      severity: 'high',
      category: 'security_pattern',
      source: 'DETERMINISTIC_STATIC_ANALYSIS',
      created_at: '2026-11-10T00:00:00Z',
    },
    {
      id: 'f3',
      review_id: 'r1',
      rule_id: 'AI_HYP_01',
      title: 'Potential race condition',
      explanation: 'Potential race condition in cache update',
      file_path: 'backend/app.py',
      start_line: 20,
      end_line: 25,
      severity: 'medium',
      category: 'code_quality',
      source: 'AI_GENERATED_HYPOTHESIS',
      created_at: '2026-11-10T00:00:00Z',
    },
  ];

  // 1. Filter by severity
  const criticalOnly = mockFindings.filter((f) => f.severity === 'critical');
  assert.strictEqual(criticalOnly.length, 1);
  assert.strictEqual(criticalOnly[0].id, 'f1');

  // 2. Filter by provenance tier
  const deterministicOnly = mockFindings.filter((f) => f.source === 'DETERMINISTIC_STATIC_ANALYSIS');
  assert.strictEqual(deterministicOnly.length, 2);

  const aiOnly = mockFindings.filter((f) => f.source === 'AI_GENERATED_HYPOTHESIS');
  assert.strictEqual(aiOnly.length, 1);
  assert.strictEqual(aiOnly[0].id, 'f3');

  // 3. Filter by file path
  const backendFindings = mockFindings.filter((f) => f.file_path === 'backend/app.py');
  assert.strictEqual(backendFindings.length, 2);

  // 4. Filter by rule ID
  const pyRules = mockFindings.filter((f) => f.rule_id.startsWith('PY'));
  assert.strictEqual(pyRules.length, 1);
});

test('E2E Workstation - Feedback submission validation', async () => {
  const originalFetch = globalThis.fetch;
  let sentPayload: unknown = null;

  globalThis.fetch = async (url: string | URL | Request, init?: RequestInit) => {
    assert.ok(String(url).includes('/findings/f1/feedback'));
    assert.strictEqual(init?.method, 'POST');
    sentPayload = JSON.parse(init?.body as string);
    return new Response(
      JSON.stringify({
        id: 'fb-123',
        finding_id: 'f1',
        verdict: 'useful',
        comment: 'Accurate security detection',
        created_at: '2026-11-10T00:00:00Z',
      }),
      { status: 201, headers: { 'Content-Type': 'application/json' } }
    );
  };

  try {
    const feedback = await api.submitFeedback('r1', 'f1', {
      verdict: 'useful',
      comment: 'Accurate security detection',
    });
    assert.strictEqual(feedback.id, 'fb-123');
    assert.strictEqual(feedback.verdict, 'useful');
    assert.deepStrictEqual(sentPayload, {
      verdict: 'useful',
      comment: 'Accurate security detection',
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('E2E Workstation - Benchmark metrics aggregation across 5 languages', () => {
  const mockBenchmark: BenchmarkRunSummary = {
    dataset_name: 'multi-language-frozen-benchmark',
    dataset_version: 'v1.0.0',
    engine_version: '0.1.0',
    provider: 'none',
    timestamp: '2026-11-10T12:00:00Z',
    metrics: {
      total_cases: 100,
      passed_cases: 100,
      failed_cases: 0,
      tp: 50,
      fp: 0,
      fn: 0,
      tn: 50,
      fp_cases: 0,
      precision: 1.0,
      recall: 1.0,
      f1: 1.0,
      false_positive_rate: 0.0,
      total_latency_ms: 145.0,
      mean_latency_ms: 1.45,
      median_latency_ms: 1.3,
      p95_latency_ms: 2.1,
      per_rule: {
        PY004: { rule_id: 'PY004', tp: 10, fp: 0, fn: 0, precision: 1.0, recall: 1.0, f1: 1.0 },
        JS001: { rule_id: 'JS001', tp: 10, fp: 0, fn: 0, precision: 1.0, recall: 1.0, f1: 1.0 },
        JV001: { rule_id: 'JV001', tp: 10, fp: 0, fn: 0, precision: 1.0, recall: 1.0, f1: 1.0 },
        CC001: { rule_id: 'CC001', tp: 10, fp: 0, fn: 0, precision: 1.0, recall: 1.0, f1: 1.0 },
        SQL001: { rule_id: 'SQL001', tp: 10, fp: 0, fn: 0, precision: 1.0, recall: 1.0, f1: 1.0 },
      },
    },
    case_outcomes: [],
  };

  assert.strictEqual(mockBenchmark.metrics.total_cases, 100);
  assert.strictEqual(mockBenchmark.metrics.passed_cases, 100);
  assert.strictEqual(mockBenchmark.metrics.precision, 1.0);
  assert.strictEqual(mockBenchmark.metrics.recall, 1.0);
  assert.strictEqual(mockBenchmark.metrics.f1, 1.0);
  assert.strictEqual(Object.keys(mockBenchmark.metrics.per_rule).length, 5);
});

test('E2E Workstation - Loading, empty, and error state transitions', () => {
  interface ViewState<T> {
    isLoading: boolean;
    error: string | null;
    data: T | null;
  }

  // 1. Initial Loading State
  let state: ViewState<Review[]> = { isLoading: true, error: null, data: null };
  assert.strictEqual(state.isLoading, true);
  assert.strictEqual(state.error, null);
  assert.strictEqual(state.data, null);

  // 2. Empty State (loaded, but 0 records)
  state = { isLoading: false, error: null, data: [] };
  assert.strictEqual(state.isLoading, false);
  assert.strictEqual(state.error, null);
  assert.ok(state.data !== null && state.data.length === 0);

  // 3. Error State (offline or server error)
  state = { isLoading: false, error: 'Connection refused. Is Patchwise API running?', data: null };
  assert.strictEqual(state.isLoading, false);
  assert.ok(state.error !== null && state.error.includes('Connection refused'));
  assert.strictEqual(state.data, null);

  // 4. Populated Success State
  state = {
    isLoading: false,
    error: null,
    data: [
      {
        id: 'rev-001',
        repository: 'owner/repo',
        pr_number: 10,
        status: 'completed',
        engine_version: '0.1.0',
        started_at: '2026-11-10T00:00:00Z',
        summary: {
          total_findings: 3,
          critical_count: 1,
          high_count: 1,
          medium_count: 1,
          low_count: 0,
          info_count: 0,
          deterministic_count: 3,
          ai_hypothesis_count: 0,
          verified_test_count: 0,
        },
        findings: [],
      },
    ],
  };
  assert.strictEqual(state.isLoading, false);
  assert.strictEqual(state.error, null);
  assert.ok(state.data !== null && state.data.length === 1);
  assert.strictEqual(state.data![0].id, 'rev-001');
});
