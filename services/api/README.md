# Patchwise API — Backend Service

The Patchwise API service is built with **FastAPI**, **SQLAlchemy 2.0 (async)**, and **PostgreSQL**. It orchestrates GitHub diff ingestion, static deterministic checks, optional AI analysis, and evaluation benchmarks.

---

## 1. Prerequisites

- **Python 3.11+** (Tested on Python 3.13)
- **PostgreSQL 14+** (or Docker for running PostgreSQL locally)
- Git

---

## 2. Local Setup

### Step A: Initialize Virtual Environment
From the repository root or `services/api` directory:

```bash
# Navigate to the backend directory
cd services/api

# Create a virtual environment
py -3.13 -m venv .venv
# On macOS / Linux:
# python3 -m venv .venv

# Activate the virtual environment
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Windows (CMD):
.\.venv\Scripts\activate.bat
# Linux/macOS:
source .venv/bin/activate
```

### Step B: Install Pinned Dependencies

```bash
pip install -r requirements.txt
```

### Step C: Configure Environment Variables

```bash
# Copy the example configuration template
cp .env.example .env
```

Adjust `.env` as needed:
- `DATABASE_URL`: Set to your PostgreSQL connection string (`postgresql+asyncpg://postgres:postgres@localhost:5432/patchwise`).
- `LLM_PROVIDER`: Set to `none` for 100% offline rule-only mode (0 cost, no API keys needed).
- `GITHUB_TOKEN`: Optional for public repositories (provides up to 5,000 req/hr vs 60 unauthenticated).

---

## 3. Database Migrations

Patchwise manages schema evolution with **Alembic**:

```bash
# Apply migrations to the database
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

---

## 4. Running the Backend Service

Start the Uvicorn development server:

```bash
uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

Once running:
- **Interactive OpenAPI Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Root Health Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **API v1 Health Check:** [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)
- **Plugin Registry Overview:** [http://127.0.0.1:8000/api/v1/plugins](http://127.0.0.1:8000/api/v1/plugins)
- **Execute Review:** `POST /api/v1/reviews`
- **Query Review:** `GET /api/v1/reviews/{id}`
- **Query Findings:** `GET /api/v1/reviews/{id}/findings`
- **PR Diff Inspection:** `POST /api/v1/reviews/inspect`

Example Pull Request Review Request:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/reviews \
  -H "Content-Type: application/json" \
  -d '{"repository_url": "https://github.com/fastapi/fastapi", "pull_request_number": 12}'
```

---

## 5. Running Automated Tests

Run the complete test suite using `pytest`:

```bash
pytest -v
```

The test suite runs with an in-memory SQLite async engine and offline mock fixtures, requiring 0 external network calls, 0 tokens, and 0 LLM API keys.

---

## 6. Milestone 2 & 3 Components

### Unified Diff Parser (`src/parser/diff_parser.py`)
- Parses unified diff patches and tracks `old_line_number` and `new_line_number` separately.
- Classifies line types (`+`, `-`, ` `) into `added_lines`, `deleted_lines`, and `context_lines`.
- Handles multiple hunks, file renames, new files, deleted files, empty patches, malformed patches, and binary files.
- Enforces patch size (`MAX_PATCH_CHARS`) and file count (`MAX_FILES_PER_REVIEW`) boundaries.

### GitHub REST API Client (`src/github/client.py`)
- Asynchronous client with token authentication and rate-limit tracking (`X-RateLimit-*`).
- Handles pagination, 401 authentication errors, 404 missing PRs, and 429 rate limit exceeded.
- Includes `MockGitHubClient` (`src/github/mock.py`) for offline testing without network access.

### Line-Grounding Validator (`src/validator/grounding.py`)
- Strictly validates candidate finding line ranges against parsed diff hunks.
- Differentiates added/modified lines from unmodified context and deleted lines.
- Rejects ungrounded hallucinations with structured reasons (`OUT_OF_HUNK_RANGE`, `TARGETS_UNMODIFIED_CONTEXT`, `TARGETS_DELETED_LINE`, `FILE_NOT_IN_DIFF`, `FILE_IS_BINARY`).

### Deterministic Python Rules (`src/analyzer/plugins/python/rules.py`)
- **PY001 (Input Validation):** Context-aware checks for unverified dictionary key access on external payloads.
- **PY002 (Exception Handling):** Detects bare `except:`, `except BaseException:`, and broad `except Exception: pass` suppression.
- **PY003 (Mutable Defaults):** Flags functions defining mutable default arguments (`[]`, `{}`, `set()`, `list()`).
- **PY004 (Security Patterns):** Detects calls to `eval()`, `exec()`, `pickle.loads()`, and SQL string concatenation/f-string interpolation in `execute()` queries.
- **PY005 (Test Suggestions):** Clear heuristic recommending unit tests when business logic files are modified without corresponding test file changes in the pull request.

### Offline Rule-Only Review Provider (`src/providers/rule_only.py`)
- Runs 100% offline with zero LLM API calls.
- Enforces `DETERMINISTIC_STATIC_ANALYSIS` provenance on static checks (subject to deterministic rule scope).
- Coordinates with `LineGroundingValidator` to ensure all findings point to modified code lines.

---

## 7. Milestone 4: AI Review Provider, Guardrails, & Composite Orchestrator

### AI Review Provider (`src/providers/llm.py`)
- Supports structured AI review using configured providers:
  - `mock`: In-memory deterministic mock for testing and offline verification.
  - `openai`: OpenAI Chat Completions API with structured JSON output (`gpt-4o`).
  - `anthropic`: Anthropic Messages API (`claude-3-5-sonnet-20241022`).
  - `gemini`: Google Gemini REST API (`gemini-1.5-pro` with `response_mime_type="application/json"`).
  - `ollama`: Local model server (`llama3` on `http://localhost:11434`).
  - `none`: Completely disables LLM calls and operates via `RuleOnlyProvider`.
- Enforces request timeouts (30s), bounded retries (up to 2 retries on 429/503/timeout), response size thresholds (100k chars), and sanitized exception handling.
- **Strict Provenance Enforcement:** Every AI-generated finding is unconditionally tagged as `AI_GENERATED_HYPOTHESIS`. AI suggestions are never presented as confirmed bugs.
- **Line Grounding Validation:** 100% of candidate findings are validated against diff hunks using `LineGroundingValidator`. Hallucinated line numbers and non-existent files are rejected.

### Prompt-Injection Defenses (`src/providers/prompts.py`)
- **Untrusted Input Isolation:** Diff content and pull request metadata are strictly segregated inside structural XML delimiters (`<untrusted_diff_content>`, `<untrusted_pr_metadata>`).
- **Tag Neutralization:** Adversarial attempts to escape structural blocks (e.g., `</untrusted_diff_content>`, `<system>`, `<instructions>`) are neutralized using regex replacements before prompt interpolation.
- **System Directives:** System prompts explicitly instruct models to disregard embedded instructions (`SYSTEM OVERRIDE`, roleplay requests) and produce strictly valid JSON findings.
- **Zero Untrusted Code Execution:** The system never executes, evaluates, or runs tests on untrusted pull request code. Zero function-calling or shell tools are exposed to the LLM.
- **Secret Sanitization:** All error messages and logs are scrubbed via `sanitize_secret_text()` to prevent API key or token leakage.

### Composite Orchestrator (`src/analyzer/orchestrator.py`)
- **Independent Deterministic Checks:** Runs deterministic AST rules first, guaranteeing Tier 1 static findings are always produced.
- **Safe Fallback & Graceful Degradation:** If the AI provider is disabled (`LLM_PROVIDER=none`), unavailable, times out, rate-limited, or encounters bad JSON, the orchestrator continues cleanly and returns all deterministic findings with an `AI_PROVIDER_DEGRADED` status note.
- **Provenance-Preserving Deduplication:** When AI hypotheses overlap with deterministic rules at the same file and line, the high-confidence deterministic static finding takes precedence.

---

## 8. Architecture & Plugin Extensibility

- **Pluggable Analyzers (`src/analyzer/`):** All language analyzers inherit from `BaseLanguageAnalyzer`. New languages (Python, JavaScript/TypeScript, Go) register with `plugin_registry`.
- **Finding Provenance Tiers (`src/schemas/findings.py`):**
  1. `DETERMINISTIC_STATIC_ANALYSIS` (Tier 1): High-confidence, reproducible findings generated by deterministic rules or AST checkers (subject to static rule limitations, not LLM generation).
  2. `AI_GENERATED_HYPOTHESIS` (Tier 2): LLM suggestions, line-grounded, badged as unverified hypotheses.
  3. `VERIFIED_TEST_RESULT` (Tier 3): Findings verified against dynamic test executions. Static test suggestions (e.g. recommending tests when logic changes) are static recommendations and never represented as executed or verified test results.
---

## 9. Milestone 5: Benchmark Runner and Evaluation Framework

The Patchwise evaluation framework provides a reproducible, frozen benchmark suite to evaluate analyzer accuracy and regression resistance.

### Benchmark Components

- **Versioned Evaluation Dataset (`src/benchmark/dataset.py`):**
  - Dataset: `patchwise-python-deterministic-benchmark` (`v1.0.0`).
  - 20 curated and labelled Python code-diff fixtures:
    - **10 Positive Cases:** Covers rules PY001 (input validation), PY002 (bare except, BaseException, silent pass), PY003 (mutable list/dict defaults), PY004 (eval, pickle, SQL injection), and PY005 (missing tests heuristic).
    - **5 Clean Negative Cases:** Safe `.get()` lookups, targeted exception handling, immutable defaults, parameterized SQL bindings, and business logic accompanied by test files.
    - **5 Edge Cases:** Empty diff patch, binary file diff, non-Python Markdown patch, Python syntax error, and renamed files with zero modifications.
  - Each positive case specifies expected rule IDs, target files, line numbers, and documented rationale.

- **Offline Evaluation Runner (`src/benchmark/runner.py` & `benchmark/runner.py`):**
  - Evaluates diff fixtures directly through `AnalysisOrchestrator`.
  - Operates 100% offline with `provider_id="none"` (zero external network requests, zero tokens).
  - Evaluates AI review providers only when explicitly requested via `--provider`.
  - Persists evaluation summaries to the database (`evaluation_runs` table).

- **Metrics Calculation Engine (`src/benchmark/metrics.py`):**
  - **True Positives (TP):** Ground-truth defects correctly detected.
  - **False Positives (FP):** Spurious findings on clean or modified code.
  - **False Negatives (FN):** Ground-truth defects missed by analyzer.
  - **True Negatives (TN):** Clean or edge-case fixtures correctly producing 0 findings (evaluated at the case level).
  - **Precision, Recall, F1 Score:** Harmonic metrics calculated with explicit zero-denominator handling (`None` / `N/A`, never manufactured numbers).
  - **False Positive Rate (FPR):** FP / (FP + TN) across ground-truth negative evaluation fixtures.
  - **Latency Statistics:** Mean, median, and 95th percentile (p95) latency per fixture.

- **Reporting & Export Engine (`src/benchmark/reporter.py`):**
  - Formats human-readable Markdown tables and machine-readable JSON reports.
  - Transparently documents evaluation methodology, run configuration, and known limitations.

### Running the Evaluation Suite

From repository root:
```bash
# Run deterministic offline benchmark with Markdown output
python benchmark/runner.py --provider none

# Export both JSON and Markdown reports
python benchmark/runner.py --provider none --output-json benchmark/results_v1.0.0.json --output-markdown benchmark/results_v1.0.0.md
```

From `services/api`:
```bash
# Run via python module
python -m src.benchmark.runner --provider none
```
