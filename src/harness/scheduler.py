"""Deterministic 7-Day 09:00 AM Portfolio Project Rotation Scheduler (`src/harness/scheduler.py`)."""

from __future__ import annotations

from datetime import date, datetime, timezone

from harness.schemas import ProjectTargetInfo

PORTFOLIO_7DAY_ROTATION: tuple[ProjectTargetInfo, ...] = (
    ProjectTargetInfo(
        day_index=0,
        day_name="Monday",
        project_id="enterprise-hybrid-rag-workbench",
        repository_url="https://github.com/Sushant-Nemade/enterprise-hybrid-rag-workbench",
        live_demo_url="https://sushant-nemade.github.io/enterprise-hybrid-rag-workbench/",
        primary_stack=["Python", "FastAPI", "SQLite FTS5", "ONNX Runtime", "Pydantic v2"],
        scheduled_time_local="09:00",
        timezone="Europe/Berlin",
        focus_domain="4-Mode Hybrid RAG, Pre-Retrieval RBAC, Freshness Gate, NLI Claim Verifier & Digest-Bound HITL",
    ),
    ProjectTargetInfo(
        day_index=1,
        day_name="Tuesday",
        project_id="enterprise-hybrid-data-copilot",
        repository_url="https://github.com/Sushant-Nemade/enterprise-hybrid-data-copilot",
        live_demo_url="https://sushant-nemade.github.io/enterprise-hybrid-data-copilot/",
        primary_stack=["Python", "FastAPI", "SQLite", "TypeScript", "Pydantic v2"],
        scheduled_time_local="09:00",
        timezone="Europe/Berlin",
        focus_domain="Data Freshness Gate, AST Read-Only Semantic SQL + SOP RAG Router, Numerical Parity & HITL Workflow",
    ),
    ProjectTargetInfo(
        day_index=2,
        day_name="Wednesday",
        project_id="urban-change-detection-captioning",
        repository_url="https://github.com/Sushant-Nemade/urban-change-detection-captioning",
        live_demo_url="https://huggingface.co/sushantnemade/MCI_augmented",
        primary_stack=["Python", "PyTorch", "SegFormer MiT-B1", "FastAPI", "Streamlit"],
        scheduled_time_local="09:00",
        timezone="Europe/Berlin",
        focus_domain="Bi-Temporal Satellite Change Segmentation & Captioning, Split-Family Provenance & Visual Audit Cards",
    ),
    ProjectTargetInfo(
        day_index=3,
        day_name="Thursday",
        project_id="software-intake-gatekeeper",
        repository_url="https://github.com/Sushant-Nemade/software-intake-gatekeeper",
        live_demo_url="https://github.com/marketplace/actions/software-intake-gatekeeper",
        primary_stack=["Python", "CycloneDX 1.6", "SARIF", "OSV.dev", "GitHub Actions"],
        scheduled_time_local="09:00",
        timezone="Europe/Berlin",
        focus_domain="Multi-Ecosystem Binary/Archive SBOM, Electron Fuse Hardening, Authenticode & Expiring Policy Waivers",
    ),
    ProjectTargetInfo(
        day_index=4,
        day_name="Friday",
        project_id="privacy-flow-inspector",
        repository_url="https://github.com/Sushant-Nemade/privacy-flow-inspector",
        live_demo_url="https://github.com/marketplace/actions/privacy-flow-inspector",
        primary_stack=["Python", "HAR", "Playwright", "SARIF", "GitHub Actions"],
        scheduled_time_local="09:00",
        timezone="Europe/Berlin",
        focus_domain="Offline HAR & WebSocket Privacy Gate, Checksummed IBAN/Steuer-ID/KVNR Detection & Redacted Exports",
    ),
    ProjectTargetInfo(
        day_index=5,
        day_name="Saturday",
        project_id="airbnb-price-workbench",
        repository_url="https://github.com/Sushant-Nemade/airbnb-price-workbench",
        live_demo_url="https://sushant-nemade.github.io/airbnb-price-workbench/",
        primary_stack=["Python", "scikit-learn", "ONNX Runtime Web", "TypeScript", "FastAPI"],
        scheduled_time_local="09:00",
        timezone="Europe/Berlin",
        focus_domain="Host-Disjoint Price Modeling, Calibrated Uncertainty & Browser WASM ONNX Parity",
    ),
    ProjectTargetInfo(
        day_index=6,
        day_name="Sunday",
        project_id="MarketInsight",
        repository_url="https://github.com/Sushant-Nemade/MarketInsight",
        live_demo_url="https://sushant-ai-demos.pages.dev/MarketInsight/",
        primary_stack=["Python", "FastAPI", "React 19", "TypeScript", "SQLite"],
        scheduled_time_local="09:00",
        timezone="Europe/Berlin",
        focus_domain="Source-Dated Financial Research Tables, Owner-Bearer SQLite Reports & Grounded Synthesis",
    ),
)

PROJECTS_BY_ID: dict[str, ProjectTargetInfo] = {
    p.project_id: p for p in PORTFOLIO_7DAY_ROTATION
}


def get_rotation_schedule() -> list[ProjectTargetInfo]:
    """Return the complete 7-day 09:00 AM project rotation schedule."""
    return list(PORTFOLIO_7DAY_ROTATION)


def select_project_for_date(target_date: date | str | None = None) -> ProjectTargetInfo:
    """Deterministically select the single daily target project for a given date (Monday=0 .. Sunday=6)."""
    if target_date is None:
        dt = datetime.now(timezone.utc).date()
    elif isinstance(target_date, str):
        dt = date.fromisoformat(target_date[:10])
    else:
        dt = target_date
    weekday_idx = dt.weekday()
    return PORTFOLIO_7DAY_ROTATION[weekday_idx]


def resolve_target_projects(selector: str = "daily", run_date: str | None = None) -> list[ProjectTargetInfo]:
    """Resolve `--project` selector ('daily', 'all', 'flagship', or specific project_id)."""
    cleaned = selector.strip()
    if cleaned.lower() == "daily":
        return [select_project_for_date(run_date)]
    if cleaned.lower() == "all":
        return list(PORTFOLIO_7DAY_ROTATION)
    if cleaned.lower() == "flagship":
        return list(PORTFOLIO_7DAY_ROTATION[:3])
    if cleaned in PROJECTS_BY_ID:
        return [PROJECTS_BY_ID[cleaned]]
    raise ValueError(
        f"Unknown project selector {selector!r}; allowed: 'daily', 'all', 'flagship', or {sorted(PROJECTS_BY_ID)}"
    )
