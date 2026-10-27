"""FastAPI Service & Interactive Console for Autonomous Quality, Pentest & 1,000-User Harness (`src/harness/api.py`)."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from harness import __version__
from harness.cli import (
    DEFAULT_REPORT_PATH,
    execute_project_5stage_loop,
    run_harness_suite,
)
from harness.scheduler import PROJECTS_BY_ID, get_rotation_schedule
from harness.schemas import (
    DailyHarnessMasterReport,
    ProjectTargetInfo,
    SimulateRunRequest,
    SimulateRunResponse,
)

SITE_DIR = Path(__file__).resolve().parent / "site"


def create_app() -> FastAPI:
    """Create the FastAPI application with defensive security headers and 5-stage simulation routes."""
    app = FastAPI(
        title="Autonomous Daily TDD, Red-Team Pentest & 1,000-User Simulation Harness",
        version=__version__,
        description=(
            "Automated daily 9:00 AM product-hardening platform executing Stage 1 (TDD Unit Gate), "
            "Stage 2 (Integration Gate), Stage 3 (Red-Team Pentest Agent), Stage 4 (Improvement Agent "
            "Closed-Loop Remediation), and Stage 5 (1,000-Virtual-User Concurrency & Flow Simulation)."
        ),
    )

    @app.middleware("http")
    async def add_security_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response

    @app.get("/api/health", tags=["system"])
    def get_health() -> dict[str, Any]:
        return {
            "status": "ok",
            "version": __version__,
            "daily_schedule_time": "09:00 AM (Europe/Berlin & UTC)",
            "projects_in_rotation": len(PROJECTS_BY_ID),
            "stages": [
                "1_tdd_unit_gate",
                "2_integration_gate",
                "3_red_team_pentest_agent",
                "4_improvement_agent_dialogue",
                "5_1000_virtual_user_simulation",
            ],
        }

    @app.get("/api/schedule", response_model=list[ProjectTargetInfo], tags=["scheduler"])
    def list_rotation_schedule() -> list[ProjectTargetInfo]:
        return get_rotation_schedule()

    @app.get("/api/report", response_model=DailyHarnessMasterReport, tags=["reports"])
    def get_master_report() -> DailyHarnessMasterReport:
        if DEFAULT_REPORT_PATH.is_file():
            return DailyHarnessMasterReport.model_validate_json(
                DEFAULT_REPORT_PATH.read_text(encoding="utf-8")
            )
        return run_harness_suite(selector="flagship", virtual_users=1000)

    @app.post("/api/simulate", response_model=SimulateRunResponse, tags=["simulation"])
    def trigger_5stage_simulation(req: SimulateRunRequest) -> SimulateRunResponse:
        if req.project_id not in PROJECTS_BY_ID:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown project_id {req.project_id!r}; allowed: {sorted(PROJECTS_BY_ID)}",
            )
        target = PROJECTS_BY_ID[req.project_id]
        rep = execute_project_5stage_loop(target, virtual_users=req.virtual_users)
        return SimulateRunResponse(
            run_id=f"SIM-{uuid.uuid4().hex[:10].upper()}",
            project_id=req.project_id,
            virtual_users_simulated=req.virtual_users,
            report=rep,
            meta={
                "post_hardening_errors": rep.stage5_load_simulation_1000_users.post_hardening_error_count,
                "pentest_findings_remediated": len(rep.stage3_pentest_findings),
            },
        )

    if SITE_DIR.is_dir():
        data_sub = SITE_DIR / "data"
        if data_sub.is_dir():
            app.mount("/data", StaticFiles(directory=data_sub), name="site-data")

        @app.get("/", include_in_schema=False)
        def serve_console_index() -> FileResponse:
            return FileResponse(SITE_DIR / "index.html")
    else:

        @app.get("/", include_in_schema=False)
        def serve_fallback_root() -> JSONResponse:
            return JSONResponse({"service": "autonomous-quality-redteam-harness", "version": __version__})

    return app


app = create_app()
