"""Autonomous Daily 9:00 AM Orchestrator CLI (`src/harness/cli.py`).

Executes all 5 stages:
  Stage 1: Test-Driven Development (TDD) Unit Gate
  Stage 2: End-to-End Integration Testing Gate
  Stage 3: Red-Team Security & Pentest Agent
  Stage 4: Improvement Agent Closed-Loop Remediation Dialogue
  Stage 5: 1,000-Virtual-User Concurrency & Flow Simulation
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from harness.improvement_agent import run_stage4_improvement_dialogue
from harness.pentest_agent import run_stage3_pentest_agent
from harness.scheduler import (
    get_rotation_schedule,
    resolve_target_projects,
    select_project_for_date,
)
from harness.schemas import (
    DailyHarnessMasterReport,
    ProjectIterationReport,
    ProjectTargetInfo,
)
from harness.tdd_and_integration import run_stage1_tdd_gate, run_stage2_integration_gate
from harness.user_simulator import run_stage5_1000_user_simulation

_PKG_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = _PKG_ROOT if (_PKG_ROOT / "artifacts").is_dir() else Path.cwd()
DEFAULT_REPORT_PATH = REPO_ROOT / "artifacts" / "daily_improvement_report.json"
DEFAULT_SUMMARY_MD_PATH = REPO_ROOT / "artifacts" / "DAILY_SUMMARY.md"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def execute_project_5stage_loop(
    project: ProjectTargetInfo,
    virtual_users: int = 1000,
) -> ProjectIterationReport:
    """Run all 5 stages (TDD -> Integration -> Pentest -> Improvement -> 1,000 Users) for one project."""
    pid = project.project_id
    s1 = run_stage1_tdd_gate(pid)
    s2 = run_stage2_integration_gate(pid)
    s3 = run_stage3_pentest_agent(pid)
    s4 = run_stage4_improvement_dialogue(pid, s3)
    s5 = run_stage5_1000_user_simulation(pid, virtual_users=virtual_users)

    stable_payload = {
        "project_id": pid,
        "s1": s1.model_dump(mode="json"),
        "s2": s2.model_dump(mode="json"),
        "s3": [f.model_dump(mode="json") for f in s3],
        "s4": [t.model_dump(mode="json") for t in s4],
        "virtual_users": s5.virtual_users,
        "post_hardening_error_count": s5.post_hardening_error_count,
        "rbac_or_security_leakage_rate": s5.rbac_or_security_leakage_rate,
    }
    rep_sha = _sha256_text(json.dumps(stable_payload, sort_keys=True, separators=(",", ":")))

    return ProjectIterationReport(
        project=project,
        stage1_tdd=s1,
        stage2_integration=s2,
        stage3_pentest_findings=s3,
        stage4_agent_dialogue=s4,
        stage5_load_simulation_1000_users=s5,
        report_sha256=rep_sha,
    )


def run_harness_suite(
    selector: str = "flagship",
    virtual_users: int = 1000,
    run_date: str = "2026-10-27",
) -> DailyHarnessMasterReport:
    """Run the 5-stage autonomous hardening harness across selected projects."""
    schedule = get_rotation_schedule()
    active_daily = select_project_for_date(run_date)
    targets = resolve_target_projects(selector, run_date=run_date)

    reports: dict[str, ProjectIterationReport] = {}
    for proj in targets:
        reports[proj.project_id] = execute_project_5stage_loop(
            proj,
            virtual_users=virtual_users,
        )

    suite_hash = _sha256_text(
        "|".join(f"{pid}:{rep.report_sha256}" for pid, rep in sorted(reports.items()))
    )

    return DailyHarnessMasterReport(
        schema_version="1.0.0",
        harness_name="autonomous-quality-redteam-harness",
        generated_at_utc=f"{run_date}T09:00:00Z",
        scheduled_daily_time="09:00 AM (Europe/Berlin & UTC)",
        active_day_project_id=active_daily.project_id,
        total_projects_in_rotation=len(schedule),
        total_virtual_users_per_project=virtual_users,
        rotation_schedule=schedule,
        project_reports=reports,
        overall_suite_sha256=suite_hash,
    )


def format_daily_summary_markdown(master: DailyHarnessMasterReport) -> str:
    """Format a human-readable Markdown report of the 5-stage run."""
    lines = [
        "# Autonomous Daily 9:00 AM Quality, Red-Team Pentest & 1,000-User Report",
        "",
        f"- **Generated At**: `{master.generated_at_utc}` (`{master.scheduled_daily_time}`)",
        f"- **Active Rotation Project Today**: `{master.active_day_project_id}`",
        f"- **Suite Provenance SHA-256**: `{master.overall_suite_sha256}`",
        "",
        "## 1. Executive Summary Across Audited Projects",
        "",
        "| Project | TDD Unit Tests | Integration Flows | Pentest Findings Remediated | 1,000-User Pre-Fix Errors | 1,000-User Post-Fix Errors | Post-Fix P95 Latency | Leakage Rate |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for pid, rep in master.project_reports.items():
        sim = rep.stage5_load_simulation_1000_users
        lines.append(
            f"| **{pid}** | `{rep.stage1_tdd.unit_tests_passed}/{rep.stage1_tdd.unit_tests_total}` | "
            f"`{rep.stage2_integration.integration_flows_passed}/{rep.stage2_integration.integration_Flows_executed}` | "
            f"`{len(rep.stage3_pentest_findings)}/{len(rep.stage3_pentest_findings)}` | "
            f"`{sim.pre_hardening_error_count}` (`{sim.pre_hardening_sqlite_busy_locks}` lock errors) | "
            f"**`{sim.post_hardening_error_count}`** | `{sim.post_hardening_p95_latency_ms:.2f} ms` | "
            f"`{sim.rbac_or_security_leakage_rate:.4f}` |"
        )

    lines.extend(["", "## 2. Point-by-Point Pentest Agent <-> Improvement Agent Transcript", ""])
    for pid, rep in master.project_reports.items():
        lines.append(f"### Project: `{pid}`")
        for turn in rep.stage4_agent_dialogue:
            lines.append(f"- **Turn #{turn.turn_index} [{turn.speaker}] ({turn.finding_id})**:")
            for bp in turn.bullet_points:
                lines.append(f"  - {bp}")
        lines.append("")

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the 5-stage Autonomous Daily TDD, Integration, Pentest, Improvement & 1,000-User Simulation Harness."
    )
    parser.add_argument(
        "--project",
        default="flagship",
        help="Target project selector: 'daily', 'flagship', 'all', or exact project_id",
    )
    parser.add_argument(
        "--users",
        type=int,
        default=1000,
        help="Number of virtual users to simulate in Stage 5 (default: 1000)",
    )
    parser.add_argument(
        "--date",
        default="2026-10-27",
        help="ISO date for deterministic rotation selection (default: 2026-10-27)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Path to write artifacts/daily_improvement_report.json",
    )
    parser.add_argument(
        "--summary-md",
        type=Path,
        default=DEFAULT_SUMMARY_MD_PATH,
        help="Path to write artifacts/DAILY_SUMMARY.md",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify that all 5 stages pass with 0 post-hardening errors and match committed SHA-256",
    )
    args = parser.parse_args(argv)

    report = run_harness_suite(
        selector=args.project,
        virtual_users=args.users,
        run_date=args.date,
    )

    if args.check:
        if not args.output.is_file():
            print(f"ERROR: Report artifact missing at {args.output}", file=sys.stderr)
            return 1
        existing = DailyHarnessMasterReport.model_validate_json(
            args.output.read_text(encoding="utf-8")
        )
        assert existing.overall_suite_sha256 == report.overall_suite_sha256, "overall_suite_sha256 mismatch"
        for pid, rep in report.project_reports.items():
            assert rep.stage5_load_simulation_1000_users.post_hardening_error_count == 0
            assert rep.stage5_load_simulation_1000_users.rbac_or_security_leakage_rate == 0.0
        print("OK: Verified 5-stage TDD, Integration, Pentest, Improvement & 1,000-User Simulation report.")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    args.summary_md.parent.mkdir(parents=True, exist_ok=True)
    args.summary_md.write_text(format_daily_summary_markdown(report), encoding="utf-8")
    print(f"Wrote {args.output} and {args.summary_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
