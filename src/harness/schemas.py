"""Strict Pydantic v2 data contracts for the Autonomous Daily TDD, Pentest, Improvement & 1,000-User Harness."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SeverityLevel(StrEnum):
    """Vulnerability and weakness severity levels reported by the Pentest Agent."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FindingStatus(StrEnum):
    """Lifecycle status of a Pentest finding after Improvement Agent remediation."""

    VULNERABLE_PRE_HARDENING = "VULNERABLE_PRE_HARDENING"
    REMEDIATED_AND_VERIFIED = "REMEDIATED_AND_VERIFIED"
    DEFENDED_BY_DESIGN = "DEFENDED_BY_DESIGN"


class ProjectTargetInfo(BaseModel):
    """Metadata for a single portfolio repository in the 7-day 09:00 AM rotation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    day_index: int = Field(..., ge=0, le=6, description="0=Monday .. 6=Sunday")
    day_name: str
    project_id: str
    repository_url: str
    live_demo_url: str | None
    primary_stack: list[str]
    scheduled_time_local: str = "09:00"
    timezone: str = "Europe/Berlin"
    focus_domain: str


class TDDTestSuiteSummary(BaseModel):
    """Stage 1: Test-Driven Development (RED -> GREEN -> REFACTOR) unit test gate report."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    tdd_cycle_enforced: bool
    red_phase_failing_tests_written: int = Field(..., ge=1)
    green_phase_passing_tests: int = Field(..., ge=1)
    refactor_phase_clean_lint_and_types: bool
    unit_tests_total: int = Field(..., ge=1)
    unit_tests_passed: int = Field(..., ge=1)
    assertion_density_per_test: float = Field(..., ge=1.0)
    modules_covered: list[str]


class IntegrationGateSummary(BaseModel):
    """Stage 2: End-to-End Integration Testing gate report."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    api_contract_checks_passed: bool
    storage_transaction_checks_passed: bool
    artifact_sha256_integrity_passed: bool
    ui_bundle_integrity_passed: bool
    integration_Flows_executed: int = Field(..., ge=1)
    integration_flows_passed: int = Field(..., ge=1)
    verified_invariants: list[str]


class PentestFinding(BaseModel):
    """Stage 3: Single vulnerability or weakness point discovered by the Red-Team Pentest Agent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    finding_id: str = Field(..., pattern=r"^PT-[A-Z0-9\-]+$")
    attack_vector_code: str = Field(..., pattern=r"^ATK-\d{2}$")
    attack_category: str
    severity: SeverityLevel
    target_component: str
    adversarial_payload: str
    pre_hardening_behavior: str
    post_hardening_behavior: str
    status_after_improvement: FindingStatus
    cwe_reference: str


class AgentDialogueTurn(BaseModel):
    """A single point-by-point turn between the Pentest Agent and the Improvement Agent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    turn_index: int = Field(..., ge=1)
    finding_id: str
    speaker: str = Field(..., pattern=r"^(Pentest_Agent|Improvement_Agent|Verification_Gate)$")
    bullet_points: list[str] = Field(..., min_length=1)
    code_target: str
    remediation_applied: str
    regression_test_added: str


class PersonaFlowMetrics(BaseModel):
    """Telemetry for a specific virtual user persona in the 1,000-user simulation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    persona_name: str
    virtual_users_count: int = Field(..., ge=1)
    steps_per_user: int = Field(..., ge=1)
    total_requests: int = Field(..., ge=1)
    pre_hardening_failures: int = Field(..., ge=0)
    post_hardening_failures: int = Field(..., ge=0)
    mean_latency_ms: float = Field(..., ge=0.0)
    p95_latency_ms: float = Field(..., ge=0.0)
    flow_steps_description: list[str]


class LoadSimulationComparison(BaseModel):
    """Stage 5: 1,000-Virtual-User Concurrency & Flow Simulation telemetry (Before vs After Hardening)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    virtual_users: int = Field(default=1000, ge=100)
    concurrency_workers: int = Field(..., ge=1)
    total_workflow_requests: int = Field(..., ge=100)
    pre_hardening_error_count: int = Field(..., ge=0)
    pre_hardening_error_rate: float = Field(..., ge=0.0, le=1.0)
    pre_hardening_sqlite_busy_locks: int = Field(..., ge=0)
    pre_hardening_p95_latency_ms: float = Field(..., ge=0.0)
    post_hardening_error_count: int = Field(..., ge=0)
    post_hardening_error_rate: float = Field(..., ge=0.0, le=1.0)
    post_hardening_sqlite_busy_locks: int = Field(..., ge=0)
    post_hardening_p50_latency_ms: float = Field(..., ge=0.0)
    post_hardening_p95_latency_ms: float = Field(..., ge=0.0)
    post_hardening_p99_latency_ms: float = Field(..., ge=0.0)
    post_hardening_throughput_rps: float = Field(..., ge=0.0)
    rbac_or_security_leakage_rate: float = Field(..., ge=0.0, le=1.0)
    digest_integrity_pass_rate: float = Field(..., ge=0.0, le=1.0)
    persona_breakdown: list[PersonaFlowMetrics]
    what_broke_and_how_fixed: list[str]


class ProjectIterationReport(BaseModel):
    """Complete 5-stage autonomous hardening report for one project."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project: ProjectTargetInfo
    stage1_tdd: TDDTestSuiteSummary
    stage2_integration: IntegrationGateSummary
    stage3_pentest_findings: list[PentestFinding]
    stage4_agent_dialogue: list[AgentDialogueTurn]
    stage5_load_simulation_1000_users: LoadSimulationComparison
    report_sha256: str = Field(..., min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")


class DailyHarnessMasterReport(BaseModel):
    """Top-level machine-readable artifact stored at artifacts/daily_improvement_report.json."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    harness_name: str = "autonomous-quality-redteam-harness"
    generated_at_utc: str
    scheduled_daily_time: str = "09:00 AM (Europe/Berlin & UTC)"
    active_day_project_id: str
    total_projects_in_rotation: int = 7
    total_virtual_users_per_project: int = 1000
    rotation_schedule: list[ProjectTargetInfo]
    project_reports: dict[str, ProjectIterationReport]
    overall_suite_sha256: str = Field(..., min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")


class SimulateRunRequest(BaseModel):
    """API request payload to trigger an on-demand 5-stage Pentest + Improvement + 1,000-User simulation."""

    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(default="enterprise-hybrid-rag-workbench")
    virtual_users: int = Field(default=1000, ge=100, le=5000)
    include_adversarial_attacks: bool = Field(default=True)


class SimulateRunResponse(BaseModel):
    """API response returning the 5-stage simulation and remediation transcript."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    project_id: str
    virtual_users_simulated: int
    report: ProjectIterationReport
    meta: dict[str, Any] = Field(default_factory=dict)
