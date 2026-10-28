import json
import subprocess
import sys

import pytest

from portfolio_maintenance.pipeline import execute
from portfolio_maintenance.policy import Proposal, profile_for
from portfolio_maintenance.publisher import validate_candidate


def test_authorized_unattended_delivery_does_not_require_routine_human_approval(tmp_path, monkeypatch):
    from portfolio_maintenance import publisher

    monkeypatch.setenv("MAINTENANCE_AUTO_MERGE", "1")
    report = {
        "repository": "Sushant-Nemade/TravelBrain",
        "source_sha": "a" * 40,
        "berlin_date": "2026-10-28",
        "run_id": "123",
        "status": "no-safe-change",
        "stages": [],
        "policy": {"human_merge_required": True, "automatic_production_merge": False},
    }
    (tmp_path / "report.json").write_text(json.dumps(report), encoding="utf-8")
    monkeypatch.setattr(publisher, "api", lambda *args: None)
    monkeypatch.setattr(publisher, "branch_commit", lambda *args, **kwargs: "b" * 40)
    actual = publisher.publish(tmp_path, tmp_path, "maintenance-2026-10-28")
    assert actual["policy"]["human_merge_required"] is False
    assert actual["policy"]["automatic_production_merge"] is True


@pytest.fixture
def fixture_project(tmp_path):
    project = tmp_path / "source"
    project.mkdir()
    source = project / "src/utils/async_utils.py"
    source.parent.mkdir(parents=True)
    source.write_text("def truncate(value, limit):\n    return str(value)[:limit]\n", encoding="utf-8")
    tests = project / "tests"
    tests.mkdir()
    (tests / "test_api.py").write_text(
        "from src.utils.async_utils import truncate\n\ndef test_existing():\n    assert truncate('hello', 2) == 'he'\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "--quiet"], cwd=project, check=True)
    subprocess.run(["git", "add", "."], cwd=project, check=True)
    return project


@pytest.mark.parametrize("decision_status", ["candidate", "no_change"])
def test_real_red_green_execution_precedes_candidate_publication(
    fixture_project, tmp_path, monkeypatch, decision_status
):
    from portfolio_maintenance import pipeline

    original_process = pipeline.limited_process

    def trusted_process(command, cwd, timeout):
        if command[0] == "docker":
            return {"exit_code": 0, "output": "Fixture dependency-image substitute", "truncated": False}
        return original_process(command, cwd=cwd, timeout=timeout)

    def real_fixture_pytest(image, mounts, args, control, timeout):
        project = mounts["/work"][0]
        output = mounts["/evidence"][0]
        if args[0] == "/opt/maintenance/load_probe.py":
            (output / args[-1].split("/")[-1]).write_text(
                json.dumps(
                    {"passed": True, "scope": "Explicit workload fixture substitution; engines tested separately"}
                ),
                encoding="utf-8",
            )
            return {
                "exit_code": 0,
                "output": "Fixture workload boundary, not live workload evidence",
                "truncated": False,
            }
        actual = [argument.replace("/evidence/", str(output) + "/") for argument in args]
        result = subprocess.run(
            [sys.executable, *actual], cwd=project, capture_output=True, text=True, timeout=30, check=False
        )
        return {"exit_code": result.returncode, "output": result.stdout + result.stderr, "truncated": False}

    proposal = Proposal(
        status="candidate",
        summary="Reject negative truncation budgets",
        old="return str(value)[:limit]",
        new="if limit < 0:\n        raise ValueError('negative budget')\n    return str(value)[:limit]",
        test="import pytest\nfrom src.utils.async_utils import truncate\n\ndef test_negative_budget():\n    with pytest.raises(ValueError):\n        truncate('hello', -1)\n",
    )
    monkeypatch.setattr(pipeline, "limited_process", trusted_process)
    monkeypatch.setattr(pipeline, "isolated", real_fixture_pytest)
    monkeypatch.setattr(pipeline, "prepare_model", lambda *args: None)
    monkeypatch.setattr(pipeline, "author", lambda *args: (proposal, {"role": "fixture-author-not-live-AI"}))
    monkeypatch.setattr(
        pipeline,
        "model_json",
        lambda *args: (
            {"status": decision_status, "summary": "Reject negative truncation budgets"}
            if args[3] == "planning"
            else {"approved": True, "findings": []},
            {"role": "fixture-decision-review-not-live-AI"},
        ),
    )
    profile = profile_for("Sushant-Nemade/TravelBrain")
    report = execute(
        tmp_path, fixture_project, tmp_path / "work", tmp_path / "cache", profile, "a" * 40, "2026-10-28", "123"
    )
    if decision_status == "no_change":
        assert report["status"] == "no-safe-change"
        assert not (tmp_path / "work/candidate.json").exists()
        assert [stage["name"] for stage in report["stages"]] == [
            "baseline-unit-and-integration",
            "baseline-integration",
        ]
        return
    assert report["status"] == "candidate-verified-awaiting-ci-review"
    stages = {stage["name"]: stage for stage in report["stages"]}
    assert stages["red-regression"]["exit_code"] == 1
    assert stages["red-regression"]["junit"]["failures"] == 1
    assert stages["final-unit-and-integration"]["junit"]["passed"] == 2
    candidate = json.loads((tmp_path / "work/candidate.json").read_text())
    assert set(validate_candidate(candidate, report, fixture_project)) == {profile.file, candidate["test_path"]}
    candidate["files"][".github/workflows/ci.yml"] = "forbidden"
    with pytest.raises(ValueError, match="unapproved"):
        validate_candidate(candidate, report, fixture_project)


def test_existing_source_and_tests_cannot_be_replaced_silently(fixture_project, tmp_path):
    from portfolio_maintenance.pipeline import copy_tracked, verify_unchanged

    copied = tmp_path / "copy"
    inventory = copy_tracked(fixture_project, copied)
    (copied / "tests/test_api.py").write_text("assert True", encoding="utf-8")
    with pytest.raises(ValueError, match="modified"):
        verify_unchanged(copied, inventory, {})


@pytest.mark.parametrize("mode", ["pytest", "unittest"])
def test_workload_adapter_counts_actual_repeated_journeys(tmp_path, monkeypatch, mode):
    from portfolio_maintenance import load_probe

    monkeypatch.chdir(tmp_path)
    (tmp_path / "test_journey.py").write_text(
        "import unittest\n\ndef test_plain():\n    assert 2 + 2 == 4\n\nclass Journey(unittest.TestCase):\n    def test_journey(self):\n        self.assertEqual(2 + 2, 4)\n",
        encoding="utf-8",
    )
    node = "test_journey.py::test_plain" if mode == "pytest" else "test_journey.py::Journey::test_journey"
    repository = "Sushant-Nemade/TravelBrain"
    monkeypatch.setitem(
        load_probe.PROFILES, repository, (mode, node, "Fixture only, not a live API capacity claim")
    )
    report = load_probe.repeated_workflows(repository, 3, tmp_path / "load.json")
    assert report["observed"] == 3
    assert report["passed"] and report["concurrency"] == 1
    assert report["failures"] == 0 and report["errors"] == 0
    assert report["http_request_count"] is None
