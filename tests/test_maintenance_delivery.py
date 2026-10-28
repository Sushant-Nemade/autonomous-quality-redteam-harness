import base64
import json
from copy import deepcopy

import pytest

from portfolio_maintenance.delivery import REQUIRED_CHECKS, assert_ci_proof


@pytest.fixture
def proof():
    repository = "Sushant-Nemade/TravelBrain"
    branch = "maintenance/maintenance-2026-10-28"
    pull_request = {
        "state": "open",
        "mergeable_state": "clean",
        "draft": False,
        "user": {"login": "github-actions[bot]"},
        "base": {"ref": "main", "repo": {"full_name": repository}},
        "head": {"sha": "b" * 40, "ref": branch, "repo": {"full_name": repository}},
    }
    run = {
        "status": "completed",
        "conclusion": "success",
        "event": "workflow_dispatch",
        "path": ".github/workflows/verify.yml",
        "head_sha": "b" * 40,
        "head_branch": branch,
        "head_repository": {"full_name": repository},
    }
    jobs = [
        {"name": name, "status": "completed", "conclusion": "success"} for name in REQUIRED_CHECKS["TravelBrain"]
    ]
    return repository, pull_request, run, jobs


def test_only_exact_candidate_with_all_real_ci_jobs_can_promote(proof):
    assert_ci_proof(*proof)


@pytest.mark.parametrize(
    "field,value",
    [
        ("head_sha", "c" * 40),
        ("event", "pull_request"),
        ("conclusion", "failure"),
        ("path", ".github/workflows/untrusted.yml"),
    ],
)
def test_wrong_or_failed_ci_cannot_authorize_delivery(proof, field, value):
    repository, pull_request, run, jobs = deepcopy(proof)
    run[field] = value
    with pytest.raises(ValueError):
        assert_ci_proof(repository, pull_request, run, jobs)


def test_missing_skipped_or_failed_job_is_not_a_pass(proof):
    repository, pull_request, run, jobs = deepcopy(proof)
    for changed in [jobs[:-1], [*jobs, jobs[0]], [{**job, "conclusion": "skipped"} for job in jobs]]:
        with pytest.raises(ValueError):
            assert_ci_proof(repository, pull_request, run, changed)


def test_fork_and_nonbot_prs_cannot_gain_automatic_delivery(proof):
    repository, pull_request, run, jobs = deepcopy(proof)
    pull_request["head"]["repo"]["full_name"] = "other-owner/TravelBrain"
    with pytest.raises(ValueError):
        assert_ci_proof(repository, pull_request, run, jobs)
    pull_request["head"]["repo"]["full_name"] = repository
    pull_request["user"]["login"] = "another-user"
    with pytest.raises(ValueError):
        assert_ci_proof(repository, pull_request, run, jobs)


@pytest.mark.parametrize(
    "conclusion,attempt,native_state",
    [("success", 1, "clean"), ("success", 1, "blocked"), ("failure", 1, "clean"), ("failure", 2, "clean")],
)
def test_complete_trusted_delivery_merges_exact_sha_and_dispatches_main(
    proof, monkeypatch, conclusion, attempt, native_state
):
    from portfolio_maintenance import cli, delivery

    repository, pull_request, run, jobs = deepcopy(proof)
    pull_request.update(number=1, mergeable_state=native_state)
    run.update(conclusion=conclusion, run_attempt=attempt)
    original = "def truncate(value, limit):\n    return str(value)[:limit]\n"
    changed = "def truncate(value, limit):\n    if limit < 0:\n        raise ValueError('negative budget')\n    return str(value)[:limit]\n"
    regression = "import pytest\nfrom src.utils.async_utils import truncate\n\ndef test_negative():\n    with pytest.raises(ValueError):\n        truncate('hello', -1)\n"
    test_path = "tests/test_daily_20261028.py"
    report = {
        "repository": repository,
        "source_sha": "a" * 40,
        "candidate_sha": "b" * 40,
        "candidate_branch": pull_request["head"]["ref"],
        "pull_request_number": 1,
        "berlin_date": "2026-10-28",
        "run_id": "123",
        "detail": "Reject negative truncation budgets",
        "policy": {"automatic_production_merge": True},
        "reviews": [{"response": {"approved": True, "findings": []}}],
        "stages": [
            {
                "name": name,
                "exit_code": 1 if name == "red-regression" else 0,
                "junit": {
                    "cases": 1,
                    "passed": 0 if name == "red-regression" else 1,
                    "failures": 1 if name == "red-regression" else 0,
                    "errors": 0,
                    "skipped": 0,
                },
            }
            for name in [
                "baseline-unit-and-integration",
                "baseline-integration",
                "red-regression",
                "final-unit-and-integration",
                "final-integration",
            ]
        ],
    }
    calls = []

    def fake_api(method, path, payload=None):
        calls.append((method, path, payload))
        if path.endswith("/rerun") or path.endswith("/comments"):
            return {}
        if "/runs?event=pull_request" in path:
            return {"workflow_runs": []}
        if path.endswith("/actions/runs/456"):
            return run
        if path.endswith("/actions/runs/123"):
            return {
                "conclusion": "success",
                "head_sha": "a" * 40,
                "path": ".github/workflows/daily-maintenance.yml",
                "head_repository": {"full_name": repository},
            }
        if "/commits/" in path and "/pulls" in path:
            return [pull_request]
        if path.endswith("/pulls/1"):
            return pull_request
        if "/contents/runs/" in path:
            encoded = base64.b64encode(json.dumps(report).encode()).decode()
            return {"type": "file", "size": len(encoded), "content": encoded}
        if "/jobs?" in path:
            return {"jobs": jobs}
        if path.endswith("/git/ref/heads/main"):
            return {"object": {"sha": "a" * 40}}
        if "/files?" in path:
            return [
                {"filename": "src/utils/async_utils.py", "status": "modified"},
                {"filename": test_path, "status": "added"},
            ]
        if "/contents/" in path:
            source = regression if test_path in path else original if path.endswith("a" * 40) else changed
            return {"type": "file", "size": len(source), "content": base64.b64encode(source.encode()).decode()}
        if path.endswith("/merge"):
            assert payload == {"sha": "b" * 40, "merge_method": "squash"}
            return {"merged": True, "sha": "c" * 40}
        if path.endswith("/dispatches"):
            assert payload == {"ref": "main"}
            return {}
        raise AssertionError((method, path, payload))

    monkeypatch.setenv("MAINTENANCE_AUTO_MERGE", "1")
    monkeypatch.setattr(cli, "globally_paused", lambda: False)
    monkeypatch.setattr(delivery, "api", fake_api)
    monkeypatch.setattr(delivery, "persist_delivery", lambda *args: None)
    result = delivery.finalize(repository, "456")
    if conclusion == "failure":
        assert result["status"] == (
            "independent-ci-retry-running" if attempt == 1 else "rejected-automatic-delivery"
        )
        assert not any(method == "PUT" and path.endswith("/merge") for method, path, _ in calls)
        assert any(path.endswith("/rerun") for _, path, _ in calls) is (attempt == 1)
        return
    if native_state != "clean":
        assert result["status"] == "awaiting-native-required-checks"
        assert not any(method == "PUT" and path.endswith("/merge") for method, path, _ in calls)
        assert not any(method == "PATCH" for method, _, _ in calls)
        return
    assert result["merged_sha"] == "c" * 40
    assert result["main_verification_dispatched"]
    assert any(method == "PUT" and path.endswith("/merge") for method, path, _ in calls)


@pytest.mark.parametrize(
    "attempts,expected", [(0, "merged-awaiting-main-verification"), (2, "blocked-main-verification-dispatch")]
)
def test_reconciliation_retries_missing_main_ci_without_an_unbounded_loop(proof, monkeypatch, attempts, expected):
    from portfolio_maintenance import cli, delivery

    repository, pull_request, _, _ = deepcopy(proof)
    pull_request.update(number=1, merged=True, merge_commit_sha="c" * 40)
    report = {
        "repository": repository,
        "source_sha": "a" * 40,
        "candidate_sha": "b" * 40,
        "candidate_branch": pull_request["head"]["ref"],
        "pull_request_number": 1,
        "run_id": "123",
        "policy": {"automatic_production_merge": True},
        "main_dispatch_attempts": attempts,
    }
    calls = []

    def fake_api(method, path, payload=None):
        calls.append((method, path, payload))
        if "/contents/latest.json" in path:
            return {"content": base64.b64encode(json.dumps(report).encode()).decode()}
        if path.endswith("/pulls/1"):
            return pull_request
        if path.endswith("/git/ref/heads/main"):
            return {"object": {"sha": "c" * 40}}
        if "/runs?branch=main" in path:
            return {"workflow_runs": []}
        if path.endswith("/dispatches"):
            assert payload == {"ref": "main"}
            return {}
        raise AssertionError((method, path))

    monkeypatch.setenv("MAINTENANCE_AUTO_MERGE", "1")
    monkeypatch.delenv("MAINTENANCE_DISABLED", raising=False)
    monkeypatch.setattr(cli, "globally_paused", lambda: False)
    monkeypatch.setattr(delivery, "api", fake_api)
    monkeypatch.setattr(delivery, "persist_delivery", lambda *args: None)
    result = delivery.reconcile(repository)
    assert result["status"] == expected
    assert sum(method == "POST" for method, _, _ in calls) == (1 if attempts == 0 else 0)


def test_only_matching_owned_bot_run_receives_execution_approval(proof, monkeypatch):
    from portfolio_maintenance import delivery

    repository, pull_request, run, _ = deepcopy(proof)
    waiting = {**run, "id": 77, "event": "pull_request", "conclusion": "action_required"}
    foreign = {**waiting, "id": 78, "head_repository": {"full_name": "other-owner/TravelBrain"}}
    calls = []

    def fake_api(method, path, payload=None):
        calls.append((method, path))
        if method == "GET":
            return {"workflow_runs": [waiting, foreign]}
        assert path.endswith("/77/approve") and payload == {}
        return {}

    monkeypatch.setattr(delivery, "api", fake_api)
    assert delivery.approve_owned_candidate_ci(repository, pull_request) == [77]
    assert sum(method == "POST" for method, _ in calls) == 1
    pull_request["user"]["login"] = "someone-else"
    before = len(calls)
    with pytest.raises(ValueError):
        delivery.approve_owned_candidate_ci(repository, pull_request)
    assert len(calls) == before
