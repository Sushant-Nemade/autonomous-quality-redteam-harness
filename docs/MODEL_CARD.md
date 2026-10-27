# Architecture & Methodology Card — Autonomous Quality, Red-Team Pentest & 1,000-User Simulation Harness

## 1. Purpose
`autonomous-quality-redteam-harness` is an automated daily **09:00 AM** product-hardening platform that rotates across 7 portfolio repositories (one project per day, Monday through Sunday) and executes a 5-stage verification and adversarial simulation pipeline:
1. **Stage 1: Test-Driven Development (TDD) Unit Gate (`RED -> GREEN -> REFACTOR`)**
2. **Stage 2: End-to-End Integration Testing Gate**
3. **Stage 3: Red-Team Security & Pentest Agent (`ATK-01` .. `ATK-08`)**
4. **Stage 4: Closed-Loop Improvement Agent Remediation Dialogue**
5. **Stage 5: 1,000-Virtual-User Concurrency & Multi-Step Flow Simulation (`3,000` workflow requests)**

## 2. 7-Day Automated 09:00 AM Rotation Schedule
| Day | Scheduled Time | Target Repository | Focus Domain |
| :--- | :---: | :--- | :--- |
| **Monday** | `09:00 Europe/Berlin` | `enterprise-hybrid-rag-workbench` | 4-Mode Hybrid RAG, Pre-Retrieval RBAC, Freshness Gate, NLI Claim Verifier & Digest-Bound HITL |
| **Tuesday** | `09:00 Europe/Berlin` | `enterprise-hybrid-data-copilot` | Data Freshness Gate, AST Read-Only Semantic SQL + SOP RAG Router, Numerical Parity & HITL Workflow |
| **Wednesday** | `09:00 Europe/Berlin` | `urban-change-detection-captioning` | Bi-Temporal Satellite Change Segmentation & Captioning, Split-Family Provenance & Visual Audit Cards |
| **Thursday** | `09:00 Europe/Berlin` | `software-intake-gatekeeper` | Multi-Ecosystem Binary/Archive SBOM, Electron Fuse Hardening, Authenticode & Expiring Policy Waivers |
| **Friday** | `09:00 Europe/Berlin` | `privacy-flow-inspector` | Offline HAR & WebSocket Privacy Gate, Checksummed IBAN/Steuer-ID/KVNR Detection & Redacted Exports |
| **Saturday** | `09:00 Europe/Berlin` | `airbnb-price-workbench` | Host-Disjoint Price Modeling, Calibrated Uncertainty & Browser WASM ONNX Parity |
| **Sunday** | `09:00 Europe/Berlin` | `MarketInsight` | Source-Dated Financial Research Tables, Owner-Bearer SQLite Reports & Grounded Synthesis |

## 3. Scope Boundaries
- Runs deterministically on CPU in GitHub Actions (`.github/workflows/daily_9am_improvement.yml`) and locally with zero paid LLM API calls.
- Simulates 1,000 concurrent virtual users across 5 personas against an embedded SQLite `WAL` + `RLock` workload engine and records exact before-vs-after hardening telemetry in `artifacts/daily_improvement_report.json`.
