from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from portfolio_maintenance.policy import (
    Proposal,
    apply_proposal,
    green_passed,
    junit_summary,
    local_date,
    profile_for,
    red_passed,
    registry,
    run_key,
    selection,
    validate_test,
)


def test_legacy_fixture_replay_is_not_an_unattended_improvement_schedule():
    root = Path(__file__).resolve().parents[1]
    legacy = (root / ".github/workflows/daily_9am_improvement.yml").read_text(encoding="utf-8")
    assert "schedule:" not in legacy, (
        "Fixed-count fixture replay must not masquerade as scheduled real project improvement."
    )


def test_one_project_per_local_date_with_complete_rotation():
    first = date(2026, 10, 28)
    selected = [selection(date.fromordinal(first.toordinal() + index)).repository for index in range(7)]
    assert len(set(selected)) == len(registry()) == 7
    assert selection(first).repository.endswith("/ai-blog-publisher")
    assert selection(date(2026, 11, 4)) == selection(first)


def test_berlin_date_rollover_and_dst_not_utc_weekday():
    assert local_date(datetime(2026, 7, 1, 22, 30, tzinfo=timezone.utc)) == date(2026, 7, 2)
    assert local_date(datetime(2026, 12, 1, 22, 30, tzinfo=timezone.utc)) == date(2026, 12, 1)
    with pytest.raises(ValueError):
        local_date(datetime(2026, 1, 1))


def test_durable_key_deduplicates_daily_but_distinguishes_explicit_pilots():
    repository = registry()[0].repository
    day = date(2026, 10, 28)
    assert run_key(repository, day, False, "1") == run_key(repository, day, False, "2")
    assert run_key(repository, day, True, "1") != run_key(repository, day, False, "1")
    with pytest.raises((ValueError, StopIteration)):
        run_key("other-owner/repo", day, False, "1")


def test_replacement_is_bound_to_one_existing_function():
    source = "def helper(value):\n    return value[:3]\n\ndef other():\n    return 7\n"
    proposal = Proposal(
        status="candidate",
        summary="Reject nonpositive slice limits",
        old="return value[:3]",
        new="return value[:2]",
        test="assert True",
    )
    assert "return value[:2]" in apply_proposal(source, proposal, "helper")
    bad = proposal.model_copy(update={"old": "return 7", "new": "return 9"})
    with pytest.raises(ValueError):
        apply_proposal(source, bad, "helper")
    escaped = proposal.model_copy(update={"new": "return value\n\ndef injected():\n    return 1"})
    with pytest.raises(ValueError):
        apply_proposal(source, escaped, "helper")


@pytest.mark.parametrize(
    "code",
    [
        "import os\nassert True",
        "import pytest\npytest.skip()\nassert True",
        "from boston_housing.contracts import Scenario\nScenario()",
    ],
)
def test_regression_cannot_escape_or_fake_a_test(code):
    with pytest.raises(ValueError):
        validate_test(code, profile_for("Sushant-Nemade/boston-housing-workbench"))


def test_junit_counts_observed_cases_not_claimed_totals(tmp_path):
    path = tmp_path / "actual.xml"
    path.write_text(
        '<testsuite tests="1000"><testcase name="real"><failure>assertion</failure></testcase></testsuite>'
    )
    counts = junit_summary(path)
    assert counts["cases"] == 1 and counts["failures"] == 1
    assert red_passed(1, counts)
    assert not red_passed(2, counts) and not green_passed(0, counts)
    path.write_text('<testsuite tests="1000"/>')
    with pytest.raises(ValueError):
        junit_summary(path)


def test_collection_and_environment_errors_are_not_a_red_regression(tmp_path):
    path = tmp_path / "error.xml"
    path.write_text('<testsuite><testcase name="broken"><error>import missing</error></testcase></testsuite>')
    assert not red_passed(1, junit_summary(path))


def test_missing_write_endpoint_is_not_reported_as_success(monkeypatch):
    from urllib.error import HTTPError

    from portfolio_maintenance import publisher

    def missing(*args, **kwargs):
        raise HTTPError("https://api.github.com/fixture", 404, "missing", {}, None)

    monkeypatch.setenv("GH_TOKEN", "fixture-only-not-a-real-token")
    monkeypatch.setattr(publisher, "urlopen", missing)
    assert publisher.api("GET", "repos/Sushant-Nemade/TravelBrain/git/ref/heads/missing") is None
    with pytest.raises(RuntimeError, match="404"):
        publisher.api(
            "POST", "repos/Sushant-Nemade/TravelBrain/actions/workflows/missing/dispatches", {"ref": "main"}
        )


def test_global_kill_switch_cannot_be_bypassed_by_manual_pilot(monkeypatch):
    from portfolio_maintenance import cli

    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    monkeypatch.setenv("GITHUB_REPOSITORY", "Sushant-Nemade/TravelBrain")
    monkeypatch.setenv("GITHUB_RUN_ID", "123")
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setattr(cli, "globally_paused", lambda: True)
    assert cli.preflight(True)["selected"] == "false"


def test_unavailable_global_switch_fails_closed(monkeypatch):
    from portfolio_maintenance import cli

    monkeypatch.setattr(cli, "api", lambda *args: None)
    with pytest.raises(ValueError, match="unavailable"):
        cli.globally_paused()
