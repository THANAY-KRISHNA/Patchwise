# Patchwise — Pull Request Review & Testing Assistant

> **Deterministic AST Analysis · Line-Grounded AI Hypotheses · Human-in-the-Loop Review Dashboard**

[![Backend Tests](https://img.shields.io/badge/Backend%20Tests-253%20Passing-brightgreen?style=flat-square)](services/api/tests/)
[![Frontend Tests](https://img.shields.io/badge/Frontend%20Tests-20%20Passing-brightgreen?style=flat-square)](services/web/tests/)
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
   - **Tier 1 — Deterministic Static Analysis (`DETERMINISTIC_STATIC_ANALYSIS`):** High-confidence, reproducible findings produced by deterministic AST rules and syntax checkers. Deterministic rules are subject to inherent static analysis limitations and pattern heuristics; they do not guarantee zero false-positive risk on arbitrary external repositories (the measured 0.0000 False Positive Rate applies strictly to the curated evaluation benchmark dataset).
   - **Tier 2 — AI-Generated Hypotheses (`AI_GENERATED_HYPOTHESIS`):** Potential vulnerabilities and anti-patterns flagged by LLMs. Grounded in changed lines, but explicitly badged as *Unverified Hypotheses* (never presented as confirmed bugs).
   - **Tier 3 — Verified Test Results (`VERIFIED_TEST_RESULT`):** Findings validated strictly by dynamic test runner execution or concrete test suite outcomes. Static test suggestions (such as heuristics recommending tests when business logic changes) are static recommendations categorized under `DETERMINISTIC_STATIC_ANALYSIS` and never represented as executed or verified test results.
3. **Strict Line Grounding:** Every line-level finding must reference a valid line within the parsed diff hunk line set. Ungrounded line references are automatically discarded or downgraded to file scope.
4. **Zero Untrusted Code Execution:** The server strictly acts as a static text and AST analyzer. It never executes arbitrary repository code, user-submitted build scripts, or external tests on the host system.
5. **Prompt Injection Defense:** Diff chunks, commit messages, and PR titles are treated as untrusted user input, structurally isolated within XML boundaries.
6. **Reproducible Evaluation Benchmark:** Quantitative regression testing using frozen, ground-truth datasets (`v1.0.0`) of code-diff fixtures measuring True Positives, False Positives, Precision, Recall, F1, and Latency percentiles.

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
                               │  3. Rule Engines: Python, JS/TS, Java,       │
                               │     C/C++, SQL/HiveQL                        │
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
                               │  Screen C: Benchmark Quality Scorecards      │
                               │  Screen D: Settings & Language Readiness     │
                               └──────────────────────────────────────────────┘
```

---

## 3. Language Analyzer Readiness Board

In accordance with our strict **Truth-in-Advertising Policy**, only language analyzers with fully implemented rule suites and verified test coverage are marked as active.

| Language | Extensions | Readiness Status | Operational Rules | Version |
| :--- | :--- | :---: | :--- | :---: |
| **Python** | `.py` | **Active & Tested** | `PY001` (Input Validation), `PY002` (Bare Except), `PY003` (Mutable Defaults), `PY004` (Unsafe Eval/Pickle/SQL), `PY005` (Test Suggestion) | `v1.0.0` |
| **TypeScript / JavaScript** | `.js`, `.jsx`, `.ts`, `.tsx` | **Active & Tested** | `JS001` (Dynamic Execution), `JS002` (DOM HTML Injection / XSS), `JS003` (Shell Injection), `JS004` (SQL Injection) | `v1.0.0` |
| **Java** | `.java` | **Active & Tested** | `JV001` (Unsafe Deserialization), `JV002` (Command Injection), `JV003` (JDBC SQL Injection), `JV004` (Path Traversal) | `v1.0.0` |
| **C / C++** | `.c`, `.h`, `.cc`, `.cpp`, `.cxx`, `.hh`, `.hpp`, `.hxx` | **Active & Tested** | `CC001` (Unbounded String / Formatting APIs), `CC002` (Format-String Misuse), `CC003` (Command Injection via system/popen), `CC004` (Insecure Temp Filename APIs via tmpnam/mktemp) | `v1.0.0` |
| **SQL / HiveQL** | `.sql`, `.hql`, `.hive`, `.q` | **Active & Tested** | `SQL001` (UPDATE/DELETE without WHERE), `SQL002` (Dynamic SQL Construction), `SQL003` (Overly Broad Privileges), `SQL004` (Hardcoded Credentials), `SQL005` (HiveQL Overwrite / Purge Risks) | `v1.0.0` |
| **PySpark & Scala** | `.py`, `.scala` | *Planned (Milestone 7E)* | `SP001`–`SP005` (Framework Ready) | — |

---

## 4. Implementation & Deployment Status

| Feature / Component | Implemented Locally | Committed to Git | Tested | Deployed Publicly |
| :--- | :---: | :---: | :---: | :---: |
| **FastAPI Backend Core** | Yes | Yes | Yes (253 tests) | Local Dev Server |
| **Diff Parser & Grounding Validator** | Yes | Yes | Yes (38 tests) | Local Dev Server |
| **Python AST Analyzer (`PY001`–`PY005`)** | Yes | Yes | Yes (19 tests) | Local Dev Server |
| **JavaScript/TypeScript Analyzer (`JS001`–`JS004`)** | Yes | Yes | Yes (24 tests) | Local Dev Server |
| **Java Lexical & Syntax Analyzer (`JV001`–`JV004`)** | Yes | Yes | Yes (22 tests) | Local Dev Server |
| **C/C++ Static Analyzer (`CC001`–`CC004`)** | Yes | Yes | Yes (25 tests) | Local Dev Server |
| **SQL / HiveQL Static Analyzer (`SQL001`–`SQL005`)** | Yes | Yes | Yes (31 tests) | Local Dev Server |
| **Security Hardening & Grounding Gate (M8)** | Yes | Staged | Yes (19 tests + E2E suite) | Local Dev Server |
| **End-to-End Beta Acceptance Suite (M9)** | Yes | Staged | Yes (6 backend + 6 frontend E2E) | Local Dev Server |
| **LLM Provider & Injection Guardrails** | Yes | Yes | Yes (29 tests) | Local Dev Server |
| **Python Benchmark Dataset (`v1.0.0`)** | Yes | Yes | Yes (20 fixtures, 100% pass) | Local Dev Server |
| **JavaScript/TypeScript Benchmark (`v1.0.0`)** | Yes | Yes | Yes (20 fixtures, 100% pass) | Local Dev Server |
| **Java Benchmark Dataset (`v1.0.0`)** | Yes | Yes | Yes (20 fixtures, 100% pass) | Local Dev Server |
| **C/C++ Benchmark Dataset (`v1.0.0`)** | Yes | Yes | Yes (20 fixtures, 100% pass) | Local Dev Server |
| **SQL/HiveQL Benchmark Dataset (`v1.0.0`)** | Yes | Yes | Yes (20 fixtures, 100% pass) | Local Dev Server |
| **Next.js Web Dashboard (4 Screens)** | Yes | Yes | Yes (20 tests + Build) | Local Dev Server |
| **PostgreSQL Persistence & Migrations** | Yes | Yes | Yes (Alembic DDL verified) | Offline / Container |
| **Docker Compose & Container Packaging** | Yes | Staged | Yes (Compose & Entrypoint verified) | Configured & Static Tested |
| **GitHub Actions CI Automation** | Yes | Staged | Yes (.github/workflows/ci.yml) | Ready |
| **Cloud / External Deployment** | No | No | No | *Pending Approval* |

---

## 5. Getting Started & Setup

### Prerequisites
- **Python 3.11+** (Tested on Python 3.11 and 3.13)
- **Node.js v20+** (Tested with Node.js v24.12.0 and npm 11.6.2)
- *(Optional)* **Docker & Docker Compose** (for containerized full-stack deployment)
- *(Optional)* **PostgreSQL 14+** (for persistent review history; read endpoints gracefully degrade when offline)

### 5.1 Backend Setup (`services/api`)

```pwsh
# 1. Navigate to backend directory
cd services/api

# 2. Create and activate virtual environment
# Windows PowerShell:
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux / macOS:
# python3 -m venv .venv
# source .venv/bin/activate

# 3. Install backend dependencies
pip install -r requirements.txt

# 4. Configure environment variables (DO NOT commit .env to version control)
cp .env.example .env

# 5. Initialize & migrate database schema
# Option A: When local PostgreSQL is running on port 5432:
python -m alembic upgrade head

# Option B: Offline static DDL generation (no database connection required):
python -m alembic upgrade head --sql

# 6. Start the FastAPI development server
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
```
The backend API is now running at `http://127.0.0.1:8000` (Interactive docs available at `http://127.0.0.1:8000/docs` in development mode).

### 5.2 Frontend Setup (`services/web`)

```pwsh
# 1. Navigate to frontend directory
cd services/web

# 2. Install dependencies
npm install

# 3. Configure optional environment variables
# NEXT_PUBLIC_API_URL defaults to http://localhost:8000 if omitted

# 4. Start the Next.js development server
npm run dev -- -p 3000
```
The developer dashboard is now accessible at `http://localhost:3000/`.

### 5.3 Full-Stack Containerized Setup (Docker Compose)

```bash
# Requires an active Docker daemon (e.g. Docker Desktop running)
docker compose up --build
```
- Web Dashboard: `http://localhost:3000`
- FastAPI Backend: `http://localhost:8000` (Docs: `http://localhost:8000/docs`)
- Database: `localhost:5432`

### 5.4 Troubleshooting & Error Diagnostics

1. **`RuntimeError: Security configuration error: API_SECRET_KEY must be configured...`**
   - **Cause:** Backend was started with `ENVIRONMENT=production` or `staging`, but `API_SECRET_KEY` was left blank or unset.
   - **Resolution:** By design, Patchwise fails closed in production to prevent unauthenticated access. Export a secure random token (`API_SECRET_KEY=your_key`) or run with `ENVIRONMENT=development` for local testing.
2. **`SECURITY WARNING: Production runtime is using a default or placeholder API_SECRET_KEY`**
   - **Cause:** `API_SECRET_KEY` is set to a placeholder (e.g., `patchwise_secret_key_change_me_in_prod`).
   - **Resolution:** Supply a high-entropy secret before exposing the service.
3. **Database Unavailable / Read Endpoint Fallback (`DATABASE_ERROR`)**
   - **Cause:** PostgreSQL is not running on port 5432.
   - **Resolution:** Patchwise gracefully degrades: read endpoints (`GET /api/v1/reviews`) return empty review lists and the frontend displays an empty/demo state rather than crashing. To enable persistence, start PostgreSQL or run `docker compose up postgres`.
4. **`HTTP 413 REQUEST_ENTITY_TOO_LARGE`**
   - **Cause:** Request payload or diff exceeds the 2MB limit (`MAX_REQUEST_BODY_BYTES`).
   - **Resolution:** Submit reviews for focused PRs or increase `MAX_REQUEST_BODY_BYTES` in `.env` if large diffs are intentionally expected.
5. **`HTTP 400 INVALID_REPOSITORY_URL`**
   - **Cause:** Insecure cleartext HTTP (`http://`), non-GitHub domains, loopback/IP addresses, or path-traversal sequences (`..`) in repository input.
   - **Resolution:** Provide valid HTTPS GitHub URLs (e.g., `https://github.com/owner/repo/pull/123`).
6. **Docker Daemon Connection Errors (`npipe:////./pipe/dockerDesktopLinuxEngine`)**
   - **Cause:** Docker Desktop engine is not running on the Windows host.
   - **Resolution:** Start Docker Desktop, or proceed with local native execution (Sections 5.1 & 5.2).

---

## 6. Verification & Test Commands

### 6.1 Run Backend Test Suite

```pwsh
cd services/api
.\.venv\Scripts\pytest.exe -v
```
**Actual Result:** `253 passed in 1.15s` (100% pass rate across 27 test files, including unit, integration, security hardening, and beta acceptance suites).

### 6.2 Run Frontend Quality Gates

```pwsh
cd services/web

# Run unit and end-to-end acceptance tests (Node.js native test runner: node --test)
npm test

# Run TypeScript type check
npx tsc --noEmit

# Run ESLint
npm run lint

# Run Next.js production build
npm run build
```
**Actual Results:**
- `npm test`: 20/20 tests passed (Exit code 0).
- `npx tsc --noEmit`: 0 type errors (Exit code 0).
- `npm run lint`: 0 errors, 0 warnings (Exit code 0).
- `npm run build`: Compiled successfully with Turbopack (Exit code 0).

### 6.3 Run the Evaluation Benchmarks

#### 6.3.1 Python Benchmark (`v1.0.0` Frozen Ground-Truth Dataset)

```pwsh
cd services/api
.\.venv\Scripts\python.exe -m src.benchmark.runner --dataset python --provider none
```
**Actual Measured Performance:**
- **Fixtures Evaluated:** 20 (10 positive, 5 clean negatives, 5 edge cases)
- **Pass Rate:** 100.0% (20/20)
- **Precision:** 1.0000 (Finding level)
- **Recall:** 1.0000 (Finding level)
- **F1 Score:** 1.0000 (Finding level)
- **False Positive Rate:** 0.0000 (Case level)
- **Mean Latency per Fixture:** 3.00 ms (Median: 2.05 ms, p95: 2.80 ms)

#### 6.3.2 JavaScript & TypeScript Benchmark (`v1.0.0` Frozen Ground-Truth Dataset)

```pwsh
cd services/api
.\.venv\Scripts\python.exe -m src.benchmark.runner --dataset javascript --provider none
```
**Actual Measured Performance:**
- **Fixtures Evaluated:** 20 (10 positive, 5 clean negatives, 5 edge cases)
- **Pass Rate:** 100.0% (20/20)
- **Precision:** 1.0000 (Finding level)
- **Recall:** 1.0000 (Finding level)
- **F1 Score:** 1.0000 (Finding level)
- **False Positive Rate:** 0.0000 (Case level)
- **Mean Latency per Fixture:** 4.36 ms (Median: 3.56 ms, p95: 5.47 ms)

#### 6.3.3 Java Benchmark (`v1.0.0` Frozen Ground-Truth Dataset)

```pwsh
cd services/api
.\.venv\Scripts\python.exe -m src.benchmark.runner --dataset java --provider none
```
**Actual Measured Performance:**
- **Fixtures Evaluated:** 20 (10 positive, 5 clean negatives, 5 edge cases)
- **Pass Rate:** 100.0% (20/20)
- **Precision:** 1.0000 (Finding level)
- **Recall:** 1.0000 (Finding level)
- **F1 Score:** 1.0000 (Finding level)
- **False Positive Rate:** 0.0000 (Case level)
- **Mean Latency per Fixture:** 2.83 ms (Median: 2.06 ms, p95: 3.04 ms)

#### 6.3.4 C / C++ Benchmark (`v1.0.0` Frozen Ground-Truth Dataset)

```pwsh
cd services/api
.\.venv\Scripts\python.exe -m src.benchmark.runner --dataset cpp --provider none
```
**Actual Measured Performance:**
- **Fixtures Evaluated:** 20 (10 positive, 5 clean negatives, 5 edge cases)
- **Pass Rate:** 100.0% (20/20)
- **Precision:** 1.0000 (Finding level)
- **Recall:** 1.0000 (Finding level)
- **F1 Score:** 1.0000 (Finding level)
- **False Positive Rate:** 0.0000 (Case level)
- **Mean Latency per Fixture:** 2.91 ms (Median: 2.05 ms, p95: 4.53 ms)

#### 6.3.5 SQL / HiveQL Benchmark (`v1.0.0` Frozen Ground-Truth Dataset)

```pwsh
cd services/api
.\.venv\Scripts\python.exe -m src.benchmark.runner --dataset sql --provider none
```
**Actual Measured Performance:**
- **Fixtures Evaluated:** 20 (10 positive, 5 clean negatives, 5 edge cases)
- **Pass Rate:** 100.0% (20/20)
- **Precision:** 1.0000 (Finding level)
- **Recall:** 1.0000 (Finding level)
- **F1 Score:** 1.0000 (Finding level)
- **False Positive Rate:** 0.0000 (Case level)
- **Mean Latency per Fixture:** 3.02 ms (Median: 2.06 ms, p95: 2.79 ms)

### 6.4 Dependency Vulnerability Audit

- **Frontend Scanner:** `npm audit` (npm v11.6.2) on `services/web`
  - **Production Dependencies (`npm audit --omit=dev`):** **0 vulnerabilities found**.
  - **Development Dependencies:** 5 high-severity vulnerabilities in transitive linter dependency `braces` (via `eslint-config-next` -> `@next/eslint-plugin-next` -> `fast-glob` -> `micromatch` -> `braces`, GHSA-vfj7-8cjw-p6xm: stack exhaustion on deeply nested glob patterns). Note: this code executes strictly at build/lint time and is excluded from the client production bundle.
- **Backend Scanner:** Pinned manifests in `services/api/requirements.txt` with vetted dependencies (FastAPI 0.143.0, SQLAlchemy 2.1.4, Pydantic 2.14.0, Pygments 2.21.0).

---

## 7. Known Limitations & Scope Boundaries

1. **Curated Fixture Scope:** The evaluation benchmarks measure performance against versioned synthetic and curated code-diff fixtures (`v1.0.0`). They validate parser correctness, rule pattern matching, diff line grounding, and provenance enforcement, but do not prove real-world bug-detection accuracy across arbitrary unseen repositories.
2. **Local PostgreSQL Dependency:** When running without an active PostgreSQL daemon on port 5432, read endpoints (`GET /api/v1/reviews`) gracefully degrade to returning empty review sets. The dashboard handles this with an empty state and a demo inspection mode rather than crashing.
3. **Pluggable Language Scope:** Python (`PY001`–`PY005`), TypeScript / JavaScript (`JS001`–`JS004`), Java (`JV001`–`JV004`), C/C++ (`CC001`–`CC004`), and SQL/HiveQL (`SQL001`–`SQL005`) are currently implemented and tested. Additional language expansion (PySpark & Scala) is scheduled for Milestone 7E.
4. **JavaScript/TypeScript Static AST Analysis Boundaries:**
   - **No Cross-File Taint Tracking:** The analyzer performs intra-hunk and intra-file AST inspections. It does not track variables across multiple files or modules.
   - **Type-Erased Preprocessing:** TypeScript type declarations and interface definitions are erased during preprocessing to allow ESTree AST parsing without altering line numbers. Semantic type checking or compiler symbol resolution is not performed.
   - **Dynamic Property & Reflection Limits:** Obfuscated or indirect calls (e.g., `window['ev' + 'al'](...)`) are not resolved dynamically without a full symbolic execution engine.
5. **Java Lexical Token & Syntax Analysis Boundaries:**
   - **Lexical Call Analysis (Not Full Compiler AST):** Analysis operates on raw diff text hunks using Pygments Java lexical token streams and call/constructor expression matching. It does not perform compilation, classpath loading, or full AST resolution.
   - **Intra-Hunk Scope:** Variables defined outside diff hunk boundaries are treated heuristically; cross-method or cross-class interprocedural taint flow is out of scope for lightweight PR diff analysis.
   - **Dynamic Reflection & Method Handle Limits:** Calls invoked via `java.lang.reflect.Method.invoke()` or `MethodHandle` without explicit identifiers are not resolved.
6. **C / C++ Lexical Token & Syntax Analysis Boundaries:**
   - **Lexer-Based Call Extraction (Not Compiler AST):** Operates via Pygments `CLexer` and `CppLexer` token streams and call syntax analysis. It does not rely on heavy native toolchains (e.g., libclang) or full compiler translation units.
   - **Preprocessor Directives & Macros:** Macro expansions (`#define`, `#ifdef`) are not expanded prior to tokenization. Complex macro wrappers around calls may not be parsed as direct function invocations.
   - **Exploitability vs API Detection:** Detection of an API (such as `strcpy` or `sprintf` in `CC001`) flags risky unbounded patterns, but does not prove exploitability in surrounding code.
   - **Intra-Hunk Scope:** Interprocedural pointer aliasing and memory buffer size tracking across functions are out of scope for diff-level static analysis.
7. **SQL / HiveQL Lexical Token & Statement Segmentation Boundaries:**
   - **Tokenization & Statement Boundary Heuristics:** Operates via Pygments `SqlLexer` token streams and semicolon-bounded statement segmentation. It does not connect to a live database or perform full vendor dialect AST parsing.
   - **Dialect Handling:** General SQL applies to standard ANSI SQL, PostgreSQL, MySQL, and SQLite. Dynamic execution patterns support PL/SQL (`EXECUTE IMMEDIATE`) and T-SQL (`EXEC`, `sp_executesql`). HiveQL rules target overwrite semantics (`INSERT OVERWRITE TABLE`) and permanent drops (`PURGE`).
   - **No Dataflow / Taint Engine:** `SQL002` distinguishes between static literals and dynamic expressions (concatenation `||`, `+`, variables). It does not claim full end-to-end dataflow taint analysis.
   - **Credential Masking:** Secret literals detected under `SQL004` are masked as `***` in evidence and descriptions to prevent leaking credentials into review logs or UI displays.
8. **Zero Untrusted Code Execution:** Analyzed repository code and PR diffs are strictly parsed as text, lexical tokens, and ASTs. No database statements are executed, no connections to real databases are opened, and no user code is run on the application server.
9. **Cloud Deployment:** In accordance with project safety guidelines, Patchwise has not been deployed to external cloud providers without explicit human confirmation.
10. **Docker Runtime Verification Boundary:** Container manifests (`Dockerfile` for backend with entrypoint migrations, `Dockerfile` for frontend, `docker-compose.yml`, and healthchecks) have been statically validated (`docker compose config` passing). Live container runtime execution was not conducted during local candidate evaluation because the Docker Desktop engine was inactive on the host system. Live container orchestration requires an active Docker daemon.

---

## 8. License & Authors

- **Author:** Thanay Krishna
- **Repository:** [https://github.com/THANAY-KRISHNA/Patchwise](https://github.com/THANAY-KRISHNA/Patchwise)
- **Documentation Reference:** [`docs/REQUIREMENTS_AND_IMPLEMENTATION_PLAN.md`](docs/REQUIREMENTS_AND_IMPLEMENTATION_PLAN.md)
