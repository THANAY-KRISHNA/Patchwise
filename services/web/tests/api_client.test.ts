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
        status: 'recorded',
        feedback_id: 'fb-123',
        finding_id: 'f-456',
        verdict: 'useful',
        recorded_at: '2026-10-10T12:00:00Z',
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
    assert.strictEqual(result.status, 'recorded');
    assert.strictEqual(result.feedback_id, 'fb-123');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('API Client loads benchmark data', async () => {
  const originalFetch = globalThis.fetch;
  const mockBenchmark = {
    dataset_name: 'patchwise-python-deterministic-benchmark',
    dataset_version: 'v1.0.0',
    metrics: {
      finding_level: { precision: 1.0, recall: 0.85, f1: 0.91, fpr: 0.0, true_positives: 17, false_positives: 0, false_negatives: 3 },
      case_level: { true_negatives: 4, evaluated_cases: 20 },
      latency_ms: { mean: 2.1, p50: 1.9, p95: 4.2 },
    },
    total_cases: 20,
    generated_at: '2026-10-10T12:00:00Z',
    reproducible: true,
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
    assert.strictEqual(res.dataset_version, 'v1.0.0');
    assert.strictEqual(res.metrics.finding_level.precision, 1.0);
    assert.strictEqual(res.metrics.case_level.true_negatives, 4);
    assert.strictEqual(res.reproducible, true);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
