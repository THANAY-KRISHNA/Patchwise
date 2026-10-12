/**
 * Centralized typed API client for Patchwise FastAPI backend.
 */

import type {
  BenchmarkRunSummary,
  DiffInspectionResponse,
  FeedbackCreate,
  FeedbackRead,
  Finding,
  HealthResponse,
  PluginsOverviewResponse,
  Review,
  ReviewSubmissionRequest,
} from '../types';

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const API_V1 = `${API_BASE_URL}/api/v1`;

export class ApiError extends Error {
  code?: string;
  statusCode: number;
  details?: unknown;

  constructor(message: string, statusCode: number, code?: string, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.code = code;
    this.details = details;
  }
}

async function request<T>(
  url: string,
  options: RequestInit = {},
  timeoutMs: number = 15000
): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      let errorData: { error?: { message?: string; code?: string; details?: unknown } } = {};
      try {
        errorData = await res.json();
      } catch {
        // Non-JSON response
      }

      const message =
        errorData.error?.message ||
        `Request to ${url} failed with HTTP ${res.status} (${res.statusText})`;
      const code = errorData.error?.code;
      const details = errorData.error?.details;

      throw new ApiError(message, res.status, code, details);
    }

    return (await res.json()) as T;
  } catch (err: unknown) {
    clearTimeout(timeoutId);
    if (err instanceof ApiError) {
      throw err;
    }
    if ((err as Error)?.name === 'AbortError') {
      throw new ApiError(`Request timeout after ${timeoutMs}ms`, 408, 'REQUEST_TIMEOUT');
    }
    throw new ApiError(
      (err as Error)?.message || 'Failed to communicate with Patchwise backend',
      503,
      'NETWORK_ERROR'
    );
  }
}

export const api = {
  /**
   * Health probe verifying backend and database connectivity.
   */
  async getHealth(): Promise<HealthResponse> {
    return request<HealthResponse>(`${API_V1}/health`);
  },

  /**
   * Get language plugin readiness overview.
   */
  async getPlugins(): Promise<PluginsOverviewResponse> {
    return request<PluginsOverviewResponse>(`${API_V1}/plugins`);
  },

  /**
   * List recent PR reviews.
   */
  async getReviews(limit: number = 50, offset: number = 0): Promise<Review[]> {
    return request<Review[]>(`${API_V1}/reviews?limit=${limit}&offset=${offset}`);
  },

  /**
   * Get full details for a single PR review.
   */
  async getReviewById(reviewId: string): Promise<Review> {
    return request<Review>(`${API_V1}/reviews/${reviewId}`);
  },

  /**
   * Get findings for a review with optional filters.
   */
  async getReviewFindings(
    reviewId: string,
    filters?: { severity?: string; category?: string; source?: string }
  ): Promise<Finding[]> {
    const params = new URLSearchParams();
    if (filters?.severity) params.set('severity', filters.severity);
    if (filters?.category) params.set('category', filters.category);
    if (filters?.source) params.set('source', filters.source);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return request<Finding[]>(`${API_V1}/reviews/${reviewId}/findings${qs}`);
  },

  /**
   * Initiate and execute a new PR review.
   */
  async createReview(payload: ReviewSubmissionRequest): Promise<Review> {
    return request<Review>(`${API_V1}/reviews`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Fetch and parse PR diff without executing analysis rules.
   */
  async inspectDiff(payload: ReviewSubmissionRequest): Promise<DiffInspectionResponse> {
    return request<DiffInspectionResponse>(`${API_V1}/reviews/inspect`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Submit reviewer feedback (useful, incorrect, irrelevant) on a finding.
   */
  async submitFeedback(
    reviewId: string,
    findingId: string,
    payload: FeedbackCreate
  ): Promise<FeedbackRead> {
    return request<FeedbackRead>(
      `${API_V1}/reviews/${reviewId}/findings/${findingId}/feedback`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    );
  },

  /**
   * Fetch the latest benchmark evaluation report.
   */
  async getLatestBenchmark(dataset?: string): Promise<BenchmarkRunSummary | null> {
    try {
      const url = dataset ? `${API_V1}/benchmarks/latest?dataset=${encodeURIComponent(dataset)}` : `${API_V1}/benchmarks/latest`;
      const data = await request<BenchmarkRunSummary>(url);
      return data;
    } catch {
      return null;
    }
  },
};
