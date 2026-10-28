import base64
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from portfolio_maintenance.policy import digest, profile_for
from portfolio_maintenance.publisher import api, branch_commit, validate_candidate

REQUIRED_CHECKS = {
    "ai-blog-publisher": ["verify (windows-latest)", "verify (ubuntu-latest)"],
    "gitpulse": ["verify (ubuntu-latest)", "verify (windows-latest)"],
    "Doclify": ["verify (ubuntu-latest, 3.10)", "verify (ubuntu-latest, 3.13)", "verify (windows-latest, 3.13)"],
    "MarketInsight": ["verify (ubuntu-latest)", "verify (windows-latest)", "container"],
    "TravelBrain": [
        "container",
        "verify (windows-latest, 3.13)",
        "verify (ubuntu-latest, 3.13)",
        "verify (ubuntu-latest, 3.11)",
    ],
    "airbnb-price-workbench": [
        "container",
        "verify (ubuntu-latest, 3.13)",
        "reproduce",
        "verify (windows-latest, 3.13)",
        "verify (ubuntu-latest, 3.11)",
    ],
    "boston-housing-workbench": [
        "browser-security-load",
        "reproduce",
        "verify (ubuntu-latest, 3.11)",
        "container",
        "verify (ubuntu-latest, 3.13)",
        "verify (windows-latest, 3.13)",
    ],
}


def content(repository: str, path: str, ref: str) -> str:
    record = api("GET", f"repos/{repository}/contents/{path}?ref={ref}")
    if not record or record.get("type") != "file" or record.get("size", 150001) > 150000:
        raise ValueError("Required bounded evidence/source file is unavailable")
    return base64.b64decode(record["content"]).decode("utf-8")


def assert_ci_proof(repository: str, pull_request: dict, run: dict, jobs: list[dict]) -> None:
    profile = profile_for(repository)
    if (
        pull_request.get("state") != "open"
        or pull_request.get("draft")
        or pull_request.get("user", {}).get("login") != "github-actions[bot]"
        or pull_request["base"]["ref"] != "main"
        or pull_request["base"]["repo"]["full_name"] != repository
        or pull_request["head"]["repo"]["full_name"] != repository
    ):
        raise ValueError("Only the trusted repository's open maintenance bot PR is eligible")
    if not re.fullmatch(r"maintenance/maintenance-\d{4}-\d{2}-\d{2}(-pilot-\d+)?", pull_request["head"]["ref"]):
        raise ValueError("Unapproved maintenance branch")
    if (
        run.get("status") != "completed"
        or run.get("conclusion") != "success"
        or run.get("event") != "workflow_dispatch"
        or run.get("path") != ".github/workflows/" + profile.ci
        or run.get("head_sha") != pull_request["head"]["sha"]
        or run.get("head_branch") != pull_request["head"]["ref"]
        or run.get("head_repository", {}).get("full_name") != repository
    ):
        raise ValueError("Independent CI does not attest this exact owned candidate SHA")
    required = set(REQUIRED_CHECKS[repository.split("/")[1]])
    if len(jobs) != len(required) or {job.get("name") for job in jobs} != required:
        raise ValueError("Required CI job set is missing, duplicated or changed")
    if any(job.get("status") != "completed" or job.get("conclusion") != "success" for job in jobs):
        raise ValueError("Every required independent CI job must succeed")


def approve_owned_candidate_ci(repository: str, pull_request: dict) -> list[int]:
    profile = profile_for(repository)
    head = pull_request.get("head", {})
    if (
        pull_request.get("user", {}).get("login") != "github-actions[bot]"
        or head.get("repo", {}).get("full_name") != repository
        or pull_request.get("base", {}).get("repo", {}).get("full_name") != repository
        or not re.fullmatch(r"maintenance/maintenance-\d{4}-\d{2}-\d{2}(-pilot-\d+)?", head.get("ref", ""))
        or not re.fullmatch(r"[a-f0-9]{40}", head.get("sha", ""))
    ):
        raise ValueError("Only the exact owned maintenance bot candidate may receive workflow approval")
    runs = api(
        "GET",
        f"repos/{repository}/actions/workflows/{profile.ci}/runs?event=pull_request&head_sha={head['sha']}&per_page=20",
    )["workflow_runs"]
    approved = []
    for run in runs:
        if (
            run.get("conclusion") == "action_required"
            and run.get("event") == "pull_request"
            and run.get("head_sha") == head["sha"]
            and run.get("head_branch") == head["ref"]
            and run.get("path") == ".github/workflows/" + profile.ci
            and run.get("head_repository", {}).get("full_name") == repository
        ):
            api("POST", f"repos/{repository}/actions/runs/{run['id']}/approve", {})
            approved.append(run["id"])
    return approved


def persist_delivery(repository: str, key: str, report: dict) -> None:
    report["delivery_updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    text = json.dumps(report, indent=2, allow_nan=False) + "\n"
    summary = (
        "# Autonomous Maintenance Delivery\n\n"
        + "\n".join(
            [
                f"- Outcome: **{report['status']}**",
                f"- Source: `{report['source_sha']}`",
                f"- Candidate: `{report.get('candidate_sha', 'none')}`",
                f"- Merged: `{report.get('merged_sha', 'not merged')}`",
                f"- Detail: {str(report.get('detail', ''))[:1000]}",
                f"- Evidence: {report.get('run_url', '')}",
                "- Only authorized, exact-SHA, independently verified bounded maintenance is eligible.",
            ]
        )
        + "\n"
    )
    current_latest = json.loads(content(repository, "latest.json", "maintenance-reports"))
    files = {f"runs/{key}.json": text}
    if current_latest.get("run_id") == report.get("run_id"):
        files.update({"latest.json": text, "README.md": summary})
    branch_commit(
        repository,
        "maintenance-reports",
        files,
        report["source_sha"],
        f"Record delivery {key}: {report['status']}",
        must_be_new=False,
    )


def finalize(repository: str, run_id: str) -> dict:
    profile = profile_for(repository)
    if os.environ.get("MAINTENANCE_AUTO_MERGE") != "1":
        return {"status": "automatic-delivery-disabled"}
    if not re.fullmatch(r"[1-9][0-9]{0,20}", run_id):
        raise ValueError("Invalid independent CI run identifier")
    from portfolio_maintenance.cli import globally_paused

    if globally_paused() or os.environ.get("MAINTENANCE_DISABLED") == "1":
        return {"status": "automatic-delivery-paused"}
    run = api("GET", f"repos/{repository}/actions/runs/{run_id}")
    if (
        not run
        or run.get("status") != "completed"
        or run.get("path") != ".github/workflows/" + profile.ci
        or run.get("event") != "workflow_dispatch"
    ):
        return {"status": "not-an-independent-maintenance-ci-run"}
    if not str(run.get("head_branch", "")).startswith("maintenance/maintenance-"):
        return {"status": "not-a-maintenance-candidate"}
    candidates = api("GET", f"repos/{repository}/commits/{run['head_sha']}/pulls?state=open&per_page=10") or []
    candidates = [
        item for item in candidates if item.get("state") == "open" and item["head"]["sha"] == run["head_sha"]
    ]
    if len(candidates) != 1:
        return {"status": "no-unique-open-maintenance-pr"}
    pull_request = api("GET", f"repos/{repository}/pulls/{candidates[0]['number']}")
    branch = pull_request["head"]["ref"]
    if not re.fullmatch(r"maintenance/maintenance-\d{4}-\d{2}-\d{2}(-pilot-\d+)?", branch):
        raise ValueError("Unapproved delivery branch")
    key = branch.removeprefix("maintenance/")
    report = json.loads(content(repository, f"runs/{key}.json", "maintenance-reports"))
    if (
        report.get("candidate_sha") != run["head_sha"]
        or report.get("candidate_branch") != branch
        or report.get("repository") != repository
        or report.get("pull_request_number") != pull_request["number"]
        or report.get("policy", {}).get("automatic_production_merge") is not True
    ):
        raise ValueError("No matching authorized trusted publication evidence")
    origin = api("GET", f"repos/{repository}/actions/runs/{report['run_id']}")
    if (
        not origin
        or origin.get("conclusion") != "success"
        or origin.get("head_sha") != report["source_sha"]
        or origin.get("path") != ".github/workflows/daily-maintenance.yml"
        or origin.get("head_repository", {}).get("full_name") != repository
    ):
        raise ValueError("Candidate did not originate from a successful trusted maintenance workflow")
    try:
        if run.get("conclusion") != "success" and run.get("run_attempt", 1) == 1:
            api("POST", f"repos/{repository}/actions/runs/{run_id}/rerun", {})
            report.update(
                status="independent-ci-retry-running",
                independent_ci_run=run_id,
                detail="One full independent CI retry requested; every required check remains mandatory",
            )
            persist_delivery(repository, key, report)
            return report
        jobs = api("GET", f"repos/{repository}/actions/runs/{run_id}/jobs?filter=latest&per_page=100")["jobs"]
        assert_ci_proof(repository, pull_request, run, jobs)
        if api("GET", f"repos/{repository}/git/ref/heads/main")["object"]["sha"] != report["source_sha"]:
            raise ValueError("Main changed after the demonstrated regression; refusing stale delivery")
        changes = api("GET", f"repos/{repository}/pulls/{pull_request['number']}/files?per_page=100")
        test_path = "tests/test_daily_" + report["berlin_date"].replace("-", "") + ".py"
        if len(changes) != 2 or {item["filename"] for item in changes} != {profile.file, test_path}:
            raise ValueError("PR contains unapproved files")
        if {item["filename"]: item["status"] for item in changes} != {
            profile.file: "modified",
            test_path: "added",
        }:
            raise ValueError("Renames, deletions or existing-test modifications are forbidden")
        original = content(repository, profile.file, report["source_sha"])
        files = {path: content(repository, path, run["head_sha"]) for path in [profile.file, test_path]}
        candidate = {
            "repository": repository,
            "source_sha": report["source_sha"],
            "summary": report["detail"],
            "files": files,
            "test_path": test_path,
            "baseline_file_sha256": digest(original),
        }
        validation_report = {**report, "status": "candidate-verified-awaiting-ci-review"}
        with TemporaryDirectory() as temporary:
            baseline = Path(temporary)
            target = baseline / profile.file
            target.parent.mkdir(parents=True)
            target.write_text(original, encoding="utf-8")
            validate_candidate(candidate, validation_report, baseline)
        approved = approve_owned_candidate_ci(repository, pull_request)
        if approved:
            report.setdefault("automatically_approved_owned_ci_runs", []).extend(approved)
        fresh = api("GET", f"repos/{repository}/pulls/{pull_request['number']}")
        if fresh["head"]["sha"] != run["head_sha"]:
            raise ValueError("Candidate changed after independent verification")
        if fresh.get("mergeable_state") != "clean":
            report.update(
                status="awaiting-native-required-checks",
                independent_ci_run=run_id,
                detail="Independent exact-SHA CI passed; native PR checks are still running or settling. No bypass or routine manual approval is required.",
            )
            persist_delivery(repository, key, report)
            return report
        result = api(
            "PUT",
            f"repos/{repository}/pulls/{pull_request['number']}/merge",
            {"sha": run["head_sha"], "merge_method": "squash"},
        )
        if not result.get("merged"):
            raise ValueError("GitHub protected-branch merge did not complete")
    except (ValueError, RuntimeError) as error:
        report.update(status="rejected-automatic-delivery", detail=str(error)[:1500], independent_ci_run=run_id)
        api("PATCH", f"repos/{repository}/pulls/{pull_request['number']}", {"state": "closed"})
        api(
            "POST",
            f"repos/{repository}/issues/{pull_request['number']}/comments",
            {
                "body": "Automatic delivery rejected this candidate without merging: "
                + str(error)[:1000]
                + ". The next selected daily run can try a fresh baseline; no manual start is needed."
            },
        )
        persist_delivery(repository, key, report)
        return report
    report.update(
        status="merged-awaiting-main-verification",
        merged_sha=result["sha"],
        independent_ci_run=run_id,
        detail="Exact candidate passed every independent CI job and bounded-scope validation; merged without routine human approval",
    )
    persist_delivery(repository, key, report)
    try:
        api("POST", f"repos/{repository}/actions/workflows/{profile.ci}/dispatches", {"ref": "main"})
        report["main_verification_dispatched"] = True
    except RuntimeError as error:
        report["detail"] = "Merged safely; scheduled reconciliation will retry main CI dispatch: " + str(error)
    persist_delivery(repository, key, report)
    return report


def reconcile(repository: str) -> dict:
    profile = profile_for(repository)
    from portfolio_maintenance.cli import globally_paused

    if (
        os.environ.get("MAINTENANCE_AUTO_MERGE") != "1"
        or globally_paused()
        or os.environ.get("MAINTENANCE_DISABLED") == "1"
    ):
        return {"status": "automatic-delivery-disabled-or-paused"}
    record = api("GET", f"repos/{repository}/contents/latest.json?ref=maintenance-reports")
    if not record:
        return {"status": "nothing-awaiting-delivery"}
    report = json.loads(base64.b64decode(record["content"]))
    if report.get("policy", {}).get("automatic_production_merge") is not True or not report.get(
        "pull_request_number"
    ):
        return {"status": "nothing-authorized-for-automatic-delivery"}
    pull_request = api("GET", f"repos/{repository}/pulls/{report['pull_request_number']}")
    if not pull_request or pull_request["head"]["sha"] != report.get("candidate_sha"):
        return {"status": "no-matching-authorized-pr"}
    key = str(report["candidate_branch"]).removeprefix("maintenance/")
    if not re.fullmatch(r"maintenance-\d{4}-\d{2}-\d{2}(-pilot-\d+)?", key):
        raise ValueError("Invalid reconciliation evidence key")
    if pull_request.get("merged"):
        merged_sha = pull_request["merge_commit_sha"]
        if api("GET", f"repos/{repository}/git/ref/heads/main")["object"]["sha"] != merged_sha:
            return {"status": "newer-main-revision-preserved"}
        runs = api(
            "GET",
            f"repos/{repository}/actions/workflows/{profile.ci}/runs?branch=main&event=workflow_dispatch&per_page=20",
        )["workflow_runs"]
        matching = [run for run in runs if run["head_sha"] == merged_sha]
        report["merged_sha"] = merged_sha
        if not matching:
            attempts = report.get("main_dispatch_attempts", 0)
            if attempts >= 2:
                report.update(
                    status="blocked-main-verification-dispatch",
                    detail="Bounded dispatch retry limit exhausted; no deployment bypass",
                )
            else:
                api("POST", f"repos/{repository}/actions/workflows/{profile.ci}/dispatches", {"ref": "main"})
                report.update(status="merged-awaiting-main-verification", main_dispatch_attempts=attempts + 1)
        elif matching[0]["status"] != "completed":
            return {"status": "main-verification-still-running"}
        elif matching[0]["conclusion"] == "success":
            report.update(
                status="merged-main-ci-verified",
                detail="Automatic merge and independent main verification passed; deployment workflow may proceed",
            )
        elif matching[0].get("run_attempt", 1) == 1:
            api("POST", f"repos/{repository}/actions/runs/{matching[0]['id']}/rerun-failed-jobs", {})
            report.update(
                status="main-verification-retry-running",
                detail="One bounded retry of failed main CI; deployment remains gated",
            )
        else:
            report.update(
                status="blocked-post-merge-verification",
                detail="Main CI failed after one retry; existing public deployment is not replaced",
            )
        persist_delivery(repository, key, report)
        return report
    if pull_request.get("state") != "open":
        return {"status": "candidate-already-closed"}
    approve_owned_candidate_ci(repository, pull_request)
    branch = pull_request["head"]["ref"]
    runs = api(
        "GET",
        f"repos/{repository}/actions/workflows/{profile.ci}/runs?branch={branch}&event=workflow_dispatch&per_page=20",
    )["workflow_runs"]
    matching = [run for run in runs if run["head_sha"] == report["candidate_sha"]]
    if matching and matching[0]["status"] == "completed":
        return finalize(repository, str(matching[0]["id"]))
    return {"status": "independent-candidate-ci-still-running"}
