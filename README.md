# Guarded Autonomous Portfolio Maintenance

> **Activation status (2026-10-28):** the evidence-backed maintenance callers are
> published and active in all seven gallery references, scheduled for **12:00 noon
> Europe/Berlin**. The first complete real pilot passed 27 tests, four integration
> cases and 1,000 serial workflows; the model returned **no safe change**, so no PR
> or improvement was invented. The former three-trigger fixture replay is manual-only.
> **The fixed counts, pentest descriptions, dialogue and telemetry below are legacy
> deterministic demonstration fixtures, NOT evidence that those projects were tested,
> repaired or load-tested by this harness.** Actual maintenance will record source
> SHAs, executed commands, observed JUnit cases, model provenance and outcomes.

## Actual Maintenance

- [Operating policy, limits, stop/recovery and activation evidence](docs/MAINTENANCE_OPERATIONS.md)
- [Real TravelBrain pilot40596897772](https://github.com/Sushant-Nemade/TravelBrain/actions/runs/40596897772)
- [Durable actual report](https://github.com/Sushant-Nemade/TravelBrain/blob/maintenance-reports/latest.json)
- [Independent real CPU-model runtime40589962908](https://github.com/Sushant-Nemade/autonomous-quality-redteam-harness/actions/runs/40589962908)
- [Pinned reusable controller](.github/workflows/portfolio-maintenance.yml)

Scheduled execution, tests, proposals, review loops and report publication are
unattended. **The owner has authorized guarded automatic merging and deployment**
for the approved bounded maintenance scope. Every existing independent CI job,
exact-source check, regression and policy gate must pass; no routine manual PR
approval is needed. Main branches require those checks even for administrators.
See the runbook for reconciliation and stop controls. Pinned offline model
roles run in separate contexts; automated review is not an independent human security
audit. A passing workflow can publish a blocked/no-change report, so inspect its
actual outcome, not only the green Actions badge.

## Legacy Fixture Demonstration

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11 | 3.12 | 3.13](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](pyproject.toml)

An automated **daily 09:00 AM** product-hardening platform (`Python`, `FastAPI`, `SQLite WAL`, `Pydantic v2`, `GitHub Actions Cron`) that rotates through **one portfolio project per day** (Monday $\to$ Sunday) and executes a 5-stage closed-loop engineering pipeline:
1. **Stage 1 — Test-Driven Development (TDD) Unit Gate (`RED -> GREEN -> REFACTOR`)**
2. **Stage 2 — End-to-End Integration Testing Gate**
3. **Stage 3 — Red-Team Security & Pentest Agent (`ATK-01` .. `ATK-08` "Break the App")**
4. **Stage 4 — Improvement Agent Closed-Loop Remediation Dialogue**
5. **Stage 5 — 1,000-Virtual-User Concurrency & Multi-Step Flow Simulator (`3,000` workflow requests)**

## Live Public Console & Documentation
- **Interactive 4-Tab Quality, Pentest & 1,000-User Telemetry Console (GitHub Pages)**: [https://sushant-nemade.github.io/autonomous-quality-redteam-harness/](https://sushant-nemade.github.io/autonomous-quality-redteam-harness/)
- **Daily 09:00 AM GitHub Actions Workflow**: [.github/workflows/daily_9am_improvement.yml](.github/workflows/daily_9am_improvement.yml)
- **Machine-Readable Master Report**: [artifacts/daily_improvement_report.json](artifacts/daily_improvement_report.json)
- **Human-Readable Daily Transcript**: [artifacts/DAILY_SUMMARY.md](artifacts/DAILY_SUMMARY.md)
- **Methodology Card**: [docs/MODEL_CARD.md](docs/MODEL_CARD.md)
- **Release Status**: [docs/RELEASE_STATUS.md](docs/RELEASE_STATUS.md)

---

## 1. What Broke Under Pentest & 1,000 Users — And How the Improvement Agent Fixed It

| Finding ID | Attack Vector | What Broke Pre-Hardening | Improvement Agent Remediation | Post-Hardening Result (1,000 Users) |
| :--- | :--- | :--- | :--- | :---: |
| **`PT-RAG-001` / `PT-COP-001`** | `ATK-04`: 1,000-User Concurrent SQLite Writes | Default SQLite journal mode produced `57` `SQLITE_BUSY` lock errors and latency spikes during parallel HITL queue writes | Enabled `PRAGMA journal_mode=WAL;`, `PRAGMA synchronous=NORMAL;`, `busy_timeout=30000`, and `threading.RLock()` transaction serialization | **`0` errors / `0` locks** (`3,000 / 3,000` requests succeeded) |
| **`PT-RAG-002` / `PT-COP-002`** | `ATK-06`: XSS `<script>` & Control-Byte Injection | Raw `<script>` tags, `javascript:` URIs, event handlers (`onerror=`), and ASCII control bytes (`\x00-\x1f`) were accepted into queries and reviewer notes | Added strict Pydantic v2 input sanitization validators rejecting unsafe payloads with `HTTP 422` prior to execution | **`100%` blocked** (`0.0000` injection leakage) |
| **`PT-RAG-003` / `PT-COP-003`** | `ATK-08`: HTTP Security Header Audit | Responses omitted clickjacking and MIME-sniffing protection headers | Added FastAPI security headers middleware (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Permissions-Policy`) | **`100%` enforced** on all API & UI responses |
| **`PT-RAG-005` / `PT-COP-004`** | `ATK-01` & `ATK-02`: SQL/FTS5 Injection & RBAC Spoofing | Probed unbalanced FTS5 quotes, multi-statement `; DROP TABLE`, and `public` role spoofing on restricted `DOC-HR-008` | Pre-retrieval RBAC partition + AST read-only SQL validator + balanced token quoting | **`0.0000` leakage** across all 1,000 users |

---

## 2. 7-Day Automated 09:00 AM Rotation Schedule

| Day | Time (`Europe/Berlin`) | Target Project | TDD Unit Gate | Integration Flows | 1,000-User Post-Fix Errors |
| :--- | :---: | :--- | :---: | :---: | :---: |
| **Monday** | `09:00 AM` | [enterprise-hybrid-rag-workbench](https://github.com/Sushant-Nemade/enterprise-hybrid-rag-workbench) | `18/18 PASS` | `12/12 PASS` | **`0 / 3,000`** |
| **Tuesday** | `09:00 AM` | [enterprise-hybrid-data-copilot](https://github.com/Sushant-Nemade/enterprise-hybrid-data-copilot) | `19/19 PASS` | `11/11 PASS` | **`0 / 3,000`** |
| **Wednesday** | `09:00 AM` | [urban-change-detection-captioning](https://github.com/Sushant-Nemade/urban-change-detection-captioning) | `35/35 PASS` | `9/9 PASS` | **`0 / 3,000`** |
| **Thursday** | `09:00 AM` | [software-intake-gatekeeper](https://github.com/Sushant-Nemade/software-intake-gatekeeper) | `113/113 PASS` | `8/8 PASS` | **`0 / 3,000`** |
| **Friday** | `09:00 AM` | [privacy-flow-inspector](https://github.com/Sushant-Nemade/privacy-flow-inspector) | `64/64 PASS` | `8/8 PASS` | **`0 / 3,000`** |
| **Saturday** | `09:00 AM` | [airbnb-price-workbench](https://github.com/Sushant-Nemade/airbnb-price-workbench) | `34/34 PASS` | `8/8 PASS` | **`0 / 3,000`** |
| **Sunday** | `09:00 AM` | [MarketInsight](https://github.com/Sushant-Nemade/MarketInsight) | `57/57 PASS` | `8/8 PASS` | **`0 / 3,000`** |

---

## 3. Quickstart & Verification

```bash
# 1. Install locked dependencies
uv sync --frozen

# 2. Run the 5-stage pipeline for today's scheduled project (or --project all) with 1,000 virtual users
uv run --frozen python -m harness.cli --project all --users 1000 --check

# 3. Run ruff, strict mypy, and pytest
uv run --frozen ruff check src tests scripts
uv run --frozen mypy src/harness
uv run --frozen pytest -v

# 4. Optional: Register local Windows Task Scheduler 09:00 AM job (in addition to GitHub Actions 09:00 AM cron)
powershell -ExecutionPolicy Bypass -File scripts/register_local_9am_task.ps1
```
