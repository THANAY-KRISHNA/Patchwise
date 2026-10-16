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

