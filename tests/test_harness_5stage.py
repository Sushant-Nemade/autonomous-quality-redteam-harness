"""Comprehensive pytest suite for the 5-stage Autonomous Daily TDD, Pentest, Improvement & 1,000-User Harness."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from harness.api import create_app
from harness.cli import execute_project_5stage_loop
from harness.cli import main as cli_main
from harness.improvement_agent import run_stage4_improvement_dialogue
from harness.pentest_agent import run_stage3_pentest_agent
from harness.scheduler import (
    PROJECTS_BY_ID,
    get_rotation_schedule,
    resolve_target_projects,
    select_project_for_date,
)
from harness.schemas import FindingStatus
from harness.tdd_and_integration import run_stage1_tdd_gate, run_stage2_integration_gate
from harness.user_simulator import run_stage5_1000_user_simulation


def test_7day_9am_rotation_scheduler_determinism() -> None:
    sched = get_rotation_schedule()
    assert len(sched) == 7
    assert all(p.scheduled_time_local == "09:00" for p in sched)

    # 2026-10-26 is Monday (0), 2026-10-27 is Tuesday (1), 2026-10-28 is Wednesday (2)
    assert select_project_for_date("2026-10-26").project_id == "enterprise-hybrid-rag-workbench"
    assert select_project_for_date("2026-10-27").project_id == "enterprise-hybrid-data-copilot"
    assert select_project_for_date("2026-10-28").project_id == "urban-change-detection-captioning"

    assert len(resolve_target_projects("all")) == 7
    assert len(resolve_target_projects("flagship")) == 3
    with pytest.raises(ValueError, match="Unknown project selector"):
        resolve_target_projects("nonexistent-project")


def test_stage1_tdd_and_stage2_integration_gates() -> None:
    for pid in PROJECTS_BY_ID:
        s1 = run_stage1_tdd_gate(pid)
        assert s1.tdd_cycle_enforced is True
        assert s1.unit_tests_passed == s1.unit_tests_total
        assert s1.refactor_phase_clean_lint_and_types is True

        s2 = run_stage2_integration_gate(pid)
        assert s2.api_contract_checks_passed is True
        assert s2.storage_transaction_checks_passed is True
        assert s2.artifact_sha256_integrity_passed is True
        assert s2.integration_flows_passed == s2.integration_Flows_executed


def test_stage3_pentest_and_stage4_improvement_dialogue() -> None:
    for pid in ("enterprise-hybrid-rag-workbench", "enterprise-hybrid-data-copilot"):
        findings = run_stage3_pentest_agent(pid)
        assert len(findings) >= 5
        assert all(
            f.status_after_improvement in (FindingStatus.REMEDIATED_AND_VERIFIED, FindingStatus.DEFENDED_BY_DESIGN)
            for f in findings
        )
        dialogue = run_stage4_improvement_dialogue(pid, findings)
        assert len(dialogue) == 2 * len(findings) + 1
        assert dialogue[-1].speaker == "Verification_Gate"


def test_stage5_1000_virtual_user_simulation_zero_post_hardening_errors() -> None:
    sim = run_stage5_1000_user_simulation("enterprise-hybrid-rag-workbench", virtual_users=1000)
    assert sim.virtual_users == 1000
    assert sim.total_workflow_requests == 3000
    assert sim.pre_hardening_error_count > 0
    assert sim.post_hardening_error_count == 0
    assert sim.post_hardening_error_rate == 0.0
    assert sim.post_hardening_sqlite_busy_locks == 0
    assert sim.rbac_or_security_leakage_rate == 0.0
    assert sim.digest_integrity_pass_rate == 1.0
    assert sum(p.virtual_users_count for p in sim.persona_breakdown) == 1000


def test_cli_check_and_fastapi_endpoints() -> None:
    assert cli_main(["--project", "all", "--check"]) == 0

    rep = execute_project_5stage_loop(PROJECTS_BY_ID["enterprise-hybrid-rag-workbench"], virtual_users=200)
    assert len(rep.report_sha256) == 64

    client = TestClient(create_app())
    h = client.get("/api/health")
    assert h.status_code == 200
    assert h.headers["X-Content-Type-Options"] == "nosniff"
    assert h.headers["X-Frame-Options"] == "DENY"

    s = client.get("/api/schedule")
    assert s.status_code == 200
    assert len(s.json()) == 7

    r = client.get("/api/report")
    assert r.status_code == 200
    assert len(r.json()["project_reports"]) == 7

    sim_resp = client.post(
        "/api/simulate",
        json={"project_id": "enterprise-hybrid-data-copilot", "virtual_users": 200},
    )
    assert sim_resp.status_code == 200
    assert sim_resp.json()["meta"]["post_hardening_errors"] == 0

    root = client.get("/")
    assert root.status_code == 200
    assert "<h1>Portfolio Maintenance</h1>" in root.text
    assert 'class="panel active" id="panel-maintenance"' in root.text
    assert "Legacy deterministic fixtures only" in root.text
    assert "Missing evidence is not a pass" in root.text
    assert "Guarded automatic merge / no routine approval" in root.text
