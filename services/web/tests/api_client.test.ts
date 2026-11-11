import test from 'node:test';
import assert from 'node:assert';
import { api, API_BASE_URL } from '../src/lib/api.ts';

test('API Client Base URL is defined', () => {
  assert.ok(API_BASE_URL);
  assert.match(API_BASE_URL, /^https?:\/\//);
});

test('API Client handles custom network error properly', async () => {
  // Mock fetch to simulate failure
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    throw new Error('Network offline');
  };

  try {
    await assert.rejects(
      async () => {
        await api.getHealth();
      },
      (err: Error) => {
        assert.ok(err.message.includes('Network offline') || err.message.includes('API request failed'));
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('API Client parses successful health response correctly', async () => {
  const originalFetch = globalThis.fetch;
  const mockHealth = {
    status: 'healthy',
    version: '0.1.0',
    llm_provider: 'none',
    database: { connected: true, dialect: 'postgresql' },
  };

  globalThis.fetch = async (url: string | URL | Request) => {
    assert.ok(String(url).endsWith('/health'));
    return new Response(JSON.stringify(mockHealth), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  };

  try {
    const res = await api.getHealth();
    assert.strictEqual(res.status, 'healthy');
    assert.strictEqual(res.llm_provider, 'none');
    assert.strictEqual(res.database.connected, true);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('API Client submits feedback payload to correct endpoint', async () => {
  const originalFetch = globalThis.fetch;
  let capturedUrl = '';
  let capturedBody = '';

  globalThis.fetch = async (url: string | URL | Request, init?: RequestInit) => {
    capturedUrl = String(url);
    capturedBody = String(init?.body || '');
    return new Response(
      JSON.stringify({
        id: 'fb-123',
        finding_id: 'f-456',
        verdict: 'useful',
        comment: 'Valid finding',
        created_at: '2026-10-10T12:00:00Z',
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    );
  };

  try {
    const result = await api.submitFeedback('rev-789', 'f-456', {
      verdict: 'useful',
      comment: 'Valid finding',
    });
    assert.ok(capturedUrl.includes('/api/v1/reviews/rev-789/findings/f-456/feedback'));
    const parsedBody = JSON.parse(capturedBody);
    assert.strictEqual(parsedBody.verdict, 'useful');
    assert.strictEqual(parsedBody.comment, 'Valid finding');
    assert.strictEqual(result.id, 'fb-123');
    assert.strictEqual(result.finding_id, 'f-456');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('API Client loads benchmark data', async () => {
  const originalFetch = globalThis.fetch;
  const mockBenchmark = {
    dataset_name: 'patchwise-python-deterministic-benchmark',
    dataset_version: 'v1.0.0',
    engine_version: '0.1.0',
    provider: 'none',
    timestamp: '2026-10-10T12:00:00Z',
    metrics: {
      total_cases: 20,
      passed_cases: 20,
      failed_cases: 0,
      tp: 10,
      fp: 0,
      fn: 0,
      tn: 10,
      fp_cases: 0,
      precision: 1.0,
      recall: 1.0,
      f1: 1.0,
      false_positive_rate: 0.0,
      total_latency_ms: 48.6,
      mean_latency_ms: 2.43,
      median_latency_ms: 1.98,
      p95_latency_ms: 2.47,
      per_rule: {},
    },
    case_outcomes: [],
  };

  globalThis.fetch = async (url: string | URL | Request) => {
    assert.ok(String(url).includes('/benchmarks/latest'));
    return new Response(JSON.stringify(mockBenchmark), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  };

  try {
    const res = await api.getLatestBenchmark();
    assert.ok(res);
    assert.strictEqual(res.dataset_version, 'v1.0.0');
    assert.strictEqual(res.metrics.precision, 1.0);
    assert.strictEqual(res.metrics.tn, 10);
    assert.strictEqual(res.metrics.passed_cases, 20);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('API Client passes dataset query parameter to benchmarks endpoint', async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = '';
  globalThis.fetch = async (url: string | URL | Request) => {
    requestedUrl = String(url);
    return new Response(
      JSON.stringify({ dataset_name: 'patchwise-javascript-deterministic-benchmark' }),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  };

  try {
    const res = await api.getLatestBenchmark('javascript');
    assert.ok(requestedUrl.includes('dataset=javascript'));
    assert.strictEqual(res?.dataset_name, 'patchwise-javascript-deterministic-benchmark');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('API Client attaches X-API-Key header when API key is configured', async () => {
  const originalFetch = globalThis.fetch;
  let capturedHeaders: HeadersInit | undefined;

  globalThis.fetch = async (url: string | URL | Request, init?: RequestInit) => {
    capturedHeaders = init?.headers;
    return new Response(
      JSON.stringify({ status: 'healthy', version: '0.1.0' }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    );
  };

  try {
    // 1. With API key set
    api.setApiKey('test-frontend-secret-token');
    assert.strictEqual(api.getApiKey(), 'test-frontend-secret-token');
    await api.getHealth();
    assert.ok(capturedHeaders);
    const headersObj = capturedHeaders as Record<string, string>;
    assert.strictEqual(headersObj['X-API-Key'], 'test-frontend-secret-token');

    // 2. Clear API key
    api.setApiKey(null);
    assert.strictEqual(api.getApiKey(), null);
    await api.getHealth();
    const headersCleared = capturedHeaders as Record<string, string>;
    assert.strictEqual(headersCleared['X-API-Key'], undefined);
  } finally {
    api.setApiKey(null);
    globalThis.fetch = originalFetch;
  }
});

test('API Client executes end-to-end PR review lifecycle (create, fetch, findings filter, diff inspection)', async () => {
  const originalFetch = globalThis.fetch;

  const mockReview = {
    id: 'rev-beta-001',
    repository: 'acme/service',
    pr_number: 42,
    pr_title: 'Feature implementation',
    status: 'completed',
    engine_version: '0.1.0',
    started_at: '2026-10-18T10:00:00Z',
    summary: {
      total_findings: 5,
      critical_count: 2,
      high_count: 2,
      medium_count: 1,
      low_count: 0,
      info_count: 0,
      deterministic_count: 5,
      ai_hypothesis_count: 0,
      verified_test_count: 0,
    },
    findings: [
      {
        id: 'f-py-1',
        review_id: 'rev-beta-001',
        rule_id: 'PY004',
        source: 'DETERMINISTIC_STATIC_ANALYSIS',
        severity: 'critical',
        category: 'security_pattern',
        file_path: 'backend/handler.py',
        start_line: 4,
        end_line: 4,
        title: 'Dangerous eval()',
        explanation: 'Avoid eval() with dynamic input',
        created_at: '2026-10-18T10:00:01Z',
      },
    ],
  };

  const mockDiff = {
    repository: 'acme/service',
    pr_number: 42,
    title: 'Feature implementation',
    base_commit_sha: 'abc1234',
    head_commit_sha: 'def5678',
    total_files_changed: 1,
    total_added_lines: 5,
    total_deleted_lines: 1,
    files: [],
  };

  globalThis.fetch = async (url: string | URL | Request, init?: RequestInit) => {
    const urlStr = String(url);
    if (urlStr.endsWith('/api/v1/reviews') && init?.method === 'POST') {
      return new Response(JSON.stringify(mockReview), { status: 201, headers: { 'Content-Type': 'application/json' } });
    }
    if (urlStr.endsWith('/api/v1/reviews/rev-beta-001')) {
      return new Response(JSON.stringify(mockReview), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    if (urlStr.includes('/api/v1/reviews/rev-beta-001/findings')) {
      return new Response(JSON.stringify(mockReview.findings), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    if (urlStr.endsWith('/api/v1/reviews/inspect')) {
      return new Response(JSON.stringify(mockDiff), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    throw new Error(`Unexpected URL in test: ${urlStr}`);
  };

  try {
    // 1. Create review
    const created = await api.createReview({ repository_url: 'https://github.com/acme/service', pull_request_number: 42 });
    assert.strictEqual(created.id, 'rev-beta-001');
    assert.strictEqual(created.status, 'completed');
    assert.strictEqual(created.summary.deterministic_count, 5);

    // 2. Fetch review by ID
    const fetched = await api.getReviewById('rev-beta-001');
    assert.strictEqual(fetched.id, 'rev-beta-001');
    assert.strictEqual(fetched.summary.total_findings, 5);

    // 3. Fetch findings with filter
    const findings = await api.getReviewFindings('rev-beta-001', { severity: 'critical' });
    assert.strictEqual(findings.length, 1);
    assert.strictEqual(findings[0].rule_id, 'PY004');
    assert.strictEqual(findings[0].source, 'DETERMINISTIC_STATIC_ANALYSIS');

    // 4. Inspect diff
    const diff = await api.inspectDiff({ repository_url: 'https://github.com/acme/service', pull_request_number: 42 });
    assert.strictEqual(diff.repository, 'acme/service');
    assert.strictEqual(diff.total_files_changed, 1);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('API Client correctly parses and handles empty-diff review without errors', async () => {
  const originalFetch = globalThis.fetch;
  const mockEmptyReview = {
    id: 'rev-empty-002',
    repository: 'acme/empty-repo',
    pr_number: 1,
    status: 'completed',
    engine_version: '0.1.0',
    started_at: '2026-10-18T10:00:00Z',
    summary: {
      total_findings: 0,
      critical_count: 0,
      high_count: 0,
      medium_count: 0,
      low_count: 0,
      info_count: 0,
      deterministic_count: 0,
      ai_hypothesis_count: 0,
      verified_test_count: 0,
    },
    findings: [],
  };

  globalThis.fetch = async () => {
    return new Response(JSON.stringify(mockEmptyReview), { status: 201, headers: { 'Content-Type': 'application/json' } });
  };

  try {
    const res = await api.createReview({ repository_url: 'https://github.com/acme/empty-repo', pull_request_number: 1 });
    assert.strictEqual(res.status, 'completed');
    assert.strictEqual(res.summary.total_findings, 0);
    assert.strictEqual(res.findings.length, 0);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('API Client propagates HTTP 401 Authentication Failure as typed ApiError', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    return new Response(
      JSON.stringify({
        error: {
          code: 'AUTHENTICATION_REQUIRED',
          message: 'Unauthorized: Authentication is required in production.',
        },
      }),
      { status: 401, headers: { 'Content-Type': 'application/json' } }
    );
  };

  try {
    await assert.rejects(
      async () => {
        await api.createReview({ repository_url: 'https://github.com/acme/repo', pull_request_number: 1 });
      },
      (err: unknown) => {
        const apiErr = err as { statusCode?: number; code?: string; message?: string };
        assert.strictEqual(apiErr.statusCode, 401);
        assert.strictEqual(apiErr.code, 'AUTHENTICATION_REQUIRED');
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('API Client propagates HTTP 413 Oversized Request as typed ApiError', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    return new Response(
      JSON.stringify({
        error: {
          code: 'REQUEST_ENTITY_TOO_LARGE',
          message: 'Request payload size exceeds allowed limit (2097152 bytes).',
        },
      }),
      { status: 413, headers: { 'Content-Type': 'application/json' } }
    );
  };

  try {
    await assert.rejects(
      async () => {
        await api.createReview({ repository_url: 'https://github.com/acme/repo', pull_request_number: 1 });
      },
      (err: unknown) => {
        const apiErr = err as { statusCode?: number; code?: string };
        assert.strictEqual(apiErr.statusCode, 413);
        assert.strictEqual(apiErr.code, 'REQUEST_ENTITY_TOO_LARGE');
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('API Client propagates HTTP 404 Upstream/PR Not Found as typed ApiError', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    return new Response(
      JSON.stringify({
        error: {
          code: 'PR_NOT_FOUND',
          message: 'Pull request not found or repository is private.',
        },
      }),
      { status: 404, headers: { 'Content-Type': 'application/json' } }
    );
  };

  try {
    await assert.rejects(
      async () => {
        await api.getReviewById('non-existent-id');
      },
      (err: unknown) => {
        const apiErr = err as { statusCode?: number; code?: string };
        assert.strictEqual(apiErr.statusCode, 404);
        assert.strictEqual(apiErr.code, 'PR_NOT_FOUND');
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('API Client propagates HTTP 400/422 Invalid Input as typed ApiError', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    return new Response(
      JSON.stringify({
        error: {
          code: 'INVALID_REPOSITORY_URL',
          message: 'Insecure HTTP repository URL is prohibited.',
        },
      }),
      { status: 400, headers: { 'Content-Type': 'application/json' } }
    );
  };

  try {
    await assert.rejects(
      async () => {
        await api.createReview({ repository_url: 'http://insecure.url', pull_request_number: 1 });
      },
      (err: unknown) => {
        const apiErr = err as { statusCode?: number; code?: string };
        assert.strictEqual(apiErr.statusCode, 400);
        assert.strictEqual(apiErr.code, 'INVALID_REPOSITORY_URL');
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

