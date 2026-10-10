# Patchwise — Pull Request Review & Testing Assistant

> **Deterministic AST Analysis · Line-Grounded AI Hypotheses · Human-in-the-Loop Review Dashboard**

[![Backend Tests](https://img.shields.io/badge/Backend%20Tests-125%20Passing-brightgreen?style=flat-square)](services/api/tests/)
[![Frontend Tests](https://img.shields.io/badge/Frontend%20Tests-8%20Passing-brightgreen?style=flat-square)](services/web/tests/)
[![Benchmark F1](https://img.shields.io/badge/Benchmark%20F1-1.0000%20(v1.0.0)-blue?style=flat-square)](benchmark/)
[![Engine Version](https://img.shields.io/badge/Engine%20Version-v0.1.0-orange?style=flat-square)](#)
[![Python Version](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](services/api/)
[![Next.js](https://img.shields.io/badge/Next.js-16%2B%20App%20Router-black?style=flat-square&logo=next.js)](services/web/)

---

## 1. Project Overview

**Patchwise** is an AI-powered, multi-language pull request review and testing assistant. It analyzes GitHub PR diffs, extracts structured code changes, applies deterministic static AST rules and bounded AI analysis, strictly validates candidate findings against exact diff line mappings, and presents findings in a human-in-the-loop developer dashboard.

### Core Architecture & Operating Principles

1. **Human-in-the-Loop:** Patchwise does not merge PRs, push commits, or autonomously alter repository code. All findings serve as decision-support suggestions for human code reviewers.
2. **Three-Tier Provenance Separation:**
   - **Tier 1 — Deterministic Static Analysis (`DETERMINISTIC_STATIC_ANALYSIS`):** High-confidence, reproducible findings produced by AST rules and syntax checkers with zero hallucination risk.
   - **Tier 2 — AI-Generated Hypotheses (`AI_GENERATED_HYPOTHESIS`):** Potential vulnerabilities and anti-patterns flagged by LLMs. Grounded in changed lines, but explicitly badged as *Unverified Hypotheses* (never presented as confirmed bugs).
   - **Tier 3 — Verified Test Results (`VERIFIED_TEST_RESULT`):** Actionable test coverage gaps and regression test recommendations.
3. **Strict Line Grounding:** Every line-level finding must reference a valid line within the parsed diff hunk line set. Ungrounded line references are automatically discarded or downgraded to file scope.
4. **Zero Untrusted Code Execution:** The server strictly acts as a static text and AST analyzer. It never executes arbitrary repository code, user-submitted build scripts, or external tests on the host system.
5. **Prompt Injection Defense:** Diff chunks, commit messages, and PR titles are treated as untrusted user input, structurally isolated within XML boundaries.
6. **Reproducible Evaluation Benchmark:** Quantitative regression testing using a frozen, ground-truth dataset (`v1.0.0`) of 20 code-diff fixtures measuring True Positives, False Positives, Precision, Recall, F1, and Latency percentiles.

---

## 2. System Architecture

```text
                               ┌──────────────────────────────────────────────┐
                               │           GitHub Pull Request                │
                               └──────────────────────┬───────────────────────┘
                                                      │ REST API
                                                      ▼
                               ┌──────────────────────────────────────────────┐
                               │          Patchwise FastAPI Backend           │
                               │                                              │
                               │  1. GitHub Client & Pagination              │
                               │  2. Unified Diff Parser & Line Mapper        │
                               │  3. Rule Engine (Python AST: PY001–PY005)   │
                               │  4. LLM Adapter (OpenAI/Anthropic/None)      │
                               │  5. Line-Grounding & Schema Validator        │
                               │  6. PostgreSQL Persistence & Benchmark API   │
                               └──────────────────────┬───────────────────────┘
                                                      │ REST JSON API
                                                      ▼
                               ┌──────────────────────────────────────────────┐
                               │           Next.js 16+ Web Dashboard          │
                               │                                              │
                               │  Screen A: System Overview & Telemetry       │
                               │  Screen B: Unified Diff Inspector & Feedback │
                               │  Screen C: Benchmark Quality Scorecard       │
                               │  Screen D: Settings & Language Readiness     │
                               └──────────────────────────────────────────────┘
```

---

## 3. Language Analyzer Readiness Board

In accordance with our strict **Truth-in-Advertising Policy**, only language analyzers with fully implemented rule suites and verified test coverage are marked as active.

| Language | Extensions | Readiness Status | Operational Rules | Version |
| :--- | :--- | :---: | :--- | :---: |
| **Python** | `.py` | **Active & Tested** | `PY001` (Input Validation), `PY002` (Bare Except), `PY003` (Mutable Defaults), `PY004` (Unsafe Eval/Pickle/SQL), `PY005` (Test Suggestion) | `v1.0.0` |
| **TypeScript / JavaScript** | `.ts`, `.tsx`, `.js`, `.jsx` | *Planned (Milestone 7)* | `TS001`–`TS005` (Framework Ready) | — |
| **Java** | `.java` | *Planned (Milestone 7)* | `JV001`–`JV005` (Framework Ready) | — |
| **C / C++** | `.c`, `.cpp`, `.h` | *Planned (Milestone 7)* | `CP001`–`CP005` (Framework Ready) | — |
| **SQL / HiveQL** | `.sql`, `.hql` | *Planned (Milestone 7)* | `SQ001`–`SQ005` (Framework Ready) | — |
| **PySpark & Scala** | `.py`, `.scala` | *Planned (Milestone 7)* | `SP001`–`SP005` (Framework Ready) | — |

---

## 4. Implementation & Deployment Status

| Feature / Component | Implemented Locally | Committed to Git | Tested | Deployed Publicly |
| :--- | :---: | :---: | :---: | :---: |
| **FastAPI Backend Core** | Yes | Yes | Yes (125 tests) | Local Dev Server |
| **Diff Parser & Grounding Validator** | Yes | Yes | Yes (38 tests) | Local Dev Server |
| **Python AST Analyzer (`PY001`–`PY005`)** | Yes | Yes | Yes (19 tests) | Local Dev Server |
| **LLM Provider & Injection Guardrails** | Yes | Yes | Yes (29 tests) | Local Dev Server |
| **Benchmark Runner & v1.0.0 Dataset** | Yes | Yes | Yes (26 tests) | Local Dev Server |
| **Next.js Web Dashboard (4 Screens)** | Yes | Yes | Yes (8 tests + Build) | Local Dev Server |
| **PostgreSQL Persistence** | Yes | Yes | Yes (Alembic models) | Requires local DB |
| **Cloud / External Deployment** | No | No | No | *Pending Approval* |

---

## 5. Getting Started & Setup

### Prerequisites
- **Python 3.11+**
- **Node.js v20+** (Tested with Node.js v24.12.0 and npm 11.6.2)
- *(Optional)* **PostgreSQL 14+** (for persistent review history)

### 5.1 Backend Setup (`services/api`)

```pwsh
# 1. Navigate to backend directory
cd services/api

# 2. Activate virtual environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment configuration
cp .env.example .env

# 5. Start the FastAPI development server
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
```
The backend API is now running at `http://127.0.0.1:8000` (Swagger docs: `http://127.0.0.1:8000/docs`).

### 5.2 Frontend Setup (`services/web`)

```pwsh
# 1. Navigate to frontend directory
cd services/web

# 2. Install dependencies
npm install

# 3. Start the Next.js development server
npm run dev -- -p 3000
```
The dashboard is now accessible at `http://localhost:3000/`.

---

## 6. Verification & Test Commands

### 6.1 Run Backend Test Suite

```pwsh
cd services/api
.\.venv\Scripts\pytest.exe -v
```
**Actual Result:** `125 passed in 0.84s` (100% pass rate).

### 6.2 Run Frontend Quality Gates

```pwsh
cd services/web

# Run unit tests (Node.js test runner)
npm test

# Run ESLint
npm run lint

# Run Next.js production build
npm run build
```
**Actual Results:**
- `npm test`: 8/8 tests passed.
- `npm run lint`: 0 errors, 0 warnings (Exit code 0).
- `npm run build`: Compiled successfully with Turbopack (Exit code 0).

### 6.3 Run the Evaluation Benchmark

```pwsh
cd services/api
.\.venv\Scripts\python.exe -m src.benchmark.runner --provider none
```
**Actual Measured Performance (Frozen v1.0.0 Ground-Truth Dataset):**
- **Fixtures Evaluated:** 20 (10 positive, 5 clean negatives, 5 edge cases)
- **Pass Rate:** 100.0% (20/20)
- **Precision:** 1.0000 (Finding level)
- **Recall:** 1.0000 (Finding level)
- **F1 Score:** 1.0000 (Finding level)
- **False Positive Rate:** 0.0000 (Case level)
- **Mean Latency per Fixture:** 2.43 ms (Median: 1.98 ms, p95: 2.47 ms)

---

## 7. Known Limitations & Scope Boundaries

1. **Curated Fixture Scope:** The current benchmark measures performance against versioned synthetic and curated code-diff fixtures. It validates parser correctness, AST matching, and grounding validation, but does not prove real-world bug-detection accuracy across arbitrary unseen repositories.
2. **Local PostgreSQL Dependency:** When running without an active PostgreSQL daemon on port 5432, read endpoints (`GET /api/v1/reviews`) gracefully degrade to returning empty review sets. The dashboard handles this with an empty state and a demo inspection mode rather than crashing.
3. **Pluggable Language Scope:** Only Python (`PY001`–`PY005`) is currently implemented and tested. Multi-language expansions (TypeScript, Java, C/C++, SQL, PySpark) are scheduled for Milestone 7.
4. **Cloud Deployment:** In accordance with project safety guidelines, Patchwise has not been deployed to external cloud providers without explicit human confirmation.

---

## 8. License & Authors

- **Author:** Thanay Krishna
- **Repository:** [https://github.com/THANAY-KRISHNA/Patchwise](https://github.com/THANAY-KRISHNA/Patchwise)
- **Documentation Reference:** [`docs/REQUIREMENTS_AND_IMPLEMENTATION_PLAN.md`](docs/REQUIREMENTS_AND_IMPLEMENTATION_PLAN.md)
