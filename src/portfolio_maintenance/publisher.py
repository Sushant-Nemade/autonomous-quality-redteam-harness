import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from portfolio_maintenance.policy import apply_proposal, digest, masked_tree, profile_for, validate_test


def api(method: str, path: str, payload: dict | None = None):
    token = os.environ.get("GH_TOKEN", "")
    if not token:
        raise ValueError("Trusted publisher requires a repository-scoped GitHub token")
    if not path.startswith("repos/Sushant-Nemade/") or ".." in path:
        raise ValueError("Out-of-owner publication is forbidden")
    request = Request(
        "https://api.github.com/" + path,
        method=method,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload).encode() if payload is not None else None,
    )
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError("GitHub metadata response exceeds size budget")
            return json.loads(raw) if raw else {}
    except HTTPError as error:
        if error.code == 404 and method == "GET":
            return None
        raise RuntimeError(f"GitHub trusted publisher returned HTTP {error.code}") from None


def branch_commit(
    repository: str, branch: str, files: dict[str, str], parent_sha: str, message: str, *, must_be_new: bool
) -> str:
    current = api("GET", f"repos/{repository}/git/ref/heads/{branch}")
    if must_be_new and current:
        raise ValueError("Date branch already exists; refusing a duplicate publication")
    if not must_be_new and current:
        parent_sha = current["object"]["sha"]
    parent = api("GET", f"repos/{repository}/git/commits/{parent_sha}")
    tree = api(
        "POST",
        f"repos/{repository}/git/trees",
        {
            "base_tree": parent["tree"]["sha"],
            "tree": [
                {"path": name, "mode": "100644", "type": "blob", "content": content}
                for name, content in files.items()
            ],
        },
    )
    commit = api(
        "POST",
        f"repos/{repository}/git/commits",
        {"message": message, "tree": tree["sha"], "parents": [parent_sha]},
    )
    if current:
        api("PATCH", f"repos/{repository}/git/refs/heads/{branch}", {"sha": commit["sha"], "force": False})
    else:
        api("POST", f"repos/{repository}/git/refs", {"ref": "refs/heads/" + branch, "sha": commit["sha"]})
    return commit["sha"]


def validate_candidate(candidate: dict, report: dict, baseline: Path) -> dict[str, str]:
    repository, source_sha = report["repository"], report["source_sha"]
    profile = profile_for(repository)
    if report["status"] != "candidate-verified-awaiting-ci-review":
        raise ValueError("Only fully verified candidates can reach the publisher")
    if candidate["repository"] != repository or candidate["source_sha"] != source_sha:
        raise ValueError("Candidate provenance differs from the verified checkout")
    test = candidate["test_path"]
    if not re.fullmatch(r"tests/test_daily_[0-9]{8}\.py", test):
        raise ValueError("Unapproved regression path")
    files = candidate["files"]
    if set(files) != {profile.file, test} or sum(len(value.encode()) for value in files.values()) > 120_000:
        raise ValueError("Candidate attempts to change unapproved files")
    original = (baseline / profile.file).read_text(encoding="utf-8")
    if digest(original) != candidate["baseline_file_sha256"]:
        raise ValueError("Baseline file identity mismatch")
    if masked_tree(original, profile.function) != masked_tree(files[profile.file], profile.function):
        raise ValueError("Candidate changes code outside its approved function")
    from portfolio_maintenance.policy import Proposal, scope_source

    apply_proposal(
        original,
        Proposal(
            status="candidate",
            summary=candidate["summary"],
            old=scope_source(original, profile.function),
            new=scope_source(files[profile.file], profile.function),
            test=files[test],
        ),
        profile.function,
    )
    validate_test(files[test], profile)
    stages = {stage["name"]: stage for stage in report["stages"]}
    for required in [
        "baseline-unit-and-integration",
        "baseline-integration",
        "red-regression",
        "final-unit-and-integration",
        "final-integration",
    ]:
        if required not in stages:
            raise ValueError("Required executed stage is missing")
    if stages["red-regression"]["exit_code"] != 1 or stages["red-regression"]["junit"]["failures"] < 1:
        raise ValueError("No observed red behavioral regression")
    for name in [
        "baseline-unit-and-integration",
        "baseline-integration",
        "final-unit-and-integration",
        "final-integration",
    ]:
        if stages[name]["exit_code"] or stages[name]["junit"]["errors"] or stages[name]["junit"]["failures"]:
            raise ValueError("A mandatory executed suite did not pass")
    review = report["reviews"][-1]["response"]
    if review != {"approved": True, "findings": []}:
        raise ValueError("Security/correctness findings remain unresolved")
    return files


def publish(work: Path, baseline: Path, key: str) -> dict:
    report = json.loads((work / "report.json").read_text(encoding="utf-8"))
    repository = report["repository"]
    profile = profile_for(repository)
    automatic = os.environ.get("MAINTENANCE_AUTO_MERGE") == "1"
    report.setdefault("policy", {}).update(
        human_merge_required=not automatic,
        automatic_production_merge=automatic,
        independent_ci_required=True,
    )
    if not re.fullmatch(r"maintenance-[0-9]{4}-[0-9]{2}-[0-9]{2}(-pilot-[0-9]+)?", key):
        raise ValueError("Invalid deduplication key")
    marker = api("GET", f"repos/{repository}/contents/runs/{key}.json?ref=maintenance-reports")
    if marker:
        return {"status": "duplicate", "key": key}
    candidate_path = work / "candidate.json"
    if report["status"] == "candidate-verified-awaiting-ci-review" and candidate_path.is_file():
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        files = validate_candidate(candidate, report, baseline)
        current_main = api("GET", f"repos/{repository}/git/ref/heads/main")["object"]["sha"]
        if current_main != report["source_sha"]:
            report.update(
                status="blocked-source-drift",
                detail="Main changed after verification; candidate was not published",
            )
        else:
            branch = "maintenance/" + key
            existing = api("GET", f"repos/{repository}/pulls?state=open&head=Sushant-Nemade:{branch}&per_page=5")
            if existing:
                report["pull_request"] = existing[0]["html_url"]
            else:
                sha = branch_commit(
                    repository, branch, files, report["source_sha"], candidate["summary"], must_be_new=True
                )
                delivery_notice = (
                    "**Unattended bounded delivery is authorized; independent CI and trusted eligibility validation remain mandatory.**"
                    if automatic
                    else "**Human review and independent project CI required; no automatic production merge.**"
                )
                body = (
                    "Automated, bounded maintenance proposal. "
                    + delivery_notice
                    + "\n\n"
                    + candidate["summary"]
                    + "\n\nBaseline SHA: `"
                    + report["source_sha"]
                    + "`\n\n"
                    "Observed behavioral RED then GREEN, existing unit/integration suites, and separate local-model review are recorded in the linked Actions run. "
                    "Pinned offline model roles run in fresh contexts; automated review is not independent human security certification. "
                    "Load adapter status is explicit in the report; no 1,000-user capacity claim is made.\n\n"
                    f"Evidence: https://github.com/{repository}/actions/runs/{report['run_id']}\n"
                )
                pull_request = api(
                    "POST",
                    f"repos/{repository}/pulls",
                    {
                        "title": "Maintenance: " + candidate["summary"][:140],
                        "head": branch,
                        "base": "main",
                        "body": body,
                        "draft": False,
                    },
                )
                report.update(
                    candidate_sha=sha,
                    pull_request=pull_request["html_url"],
                    pull_request_number=pull_request["number"],
                    candidate_branch=branch,
                    status="pull-request-awaiting-ci-auto-delivery"
                    if automatic
                    else "pull-request-awaiting-ci-and-human-review",
                )
                api("POST", f"repos/{repository}/actions/workflows/{profile.ci}/dispatches", {"ref": branch})
                report["independent_ci_dispatched"] = True
                report["ci_workflow"] = profile.ci
    report["published_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["run_url"] = f"https://github.com/{repository}/actions/runs/{report['run_id']}"
    if automatic and report.get("pull_request_number"):
        from portfolio_maintenance.delivery import approve_owned_candidate_ci

        pull_request = api("GET", f"repos/{repository}/pulls/{report['pull_request_number']}")
        try:
            report["automatically_approved_owned_ci_runs"] = approve_owned_candidate_ci(repository, pull_request)
        except RuntimeError as error:
            report["owned_ci_approval_pending"] = str(error)
    sanitized = dict(report)
    sanitized["stages"] = [
        {key: value for key, value in stage.items() if key != "log_tail"} for stage in report.get("stages", [])
    ]
    serialized = json.dumps(sanitized, indent=2, allow_nan=False) + "\n"
    summary = (
        "# Portfolio Maintenance\n\n"
        + "\n".join(
            [
                f"- Project: {repository}",
                f"- Source SHA: `{report['source_sha']}`",
                f"- Berlin date: {report['berlin_date']}",
                f"- Outcome: **{report['status']}**",
                f"- Detail: {str(report.get('detail', ''))[:800]}",
                f"- Evidence: {report['run_url']}",
                f"- Proposed PR: {report.get('pull_request', 'none')}",
                "- Publication policy: "
                + (
                    "authorized unattended merge only after independent CI and trusted eligibility checks."
                    if automatic
                    else "reviewed PR only; no automatic main merge or production deployment."
                ),
                "- A no-safe-change/rejected/blocked result is not a claimed improvement.",
            ]
        )
        + "\n"
    )
    branch_commit(
        repository,
        "maintenance-reports",
        {f"runs/{key}.json": serialized, "latest.json": serialized, "README.md": summary},
        report["source_sha"],
        f"Record {key}: {report['status']}",
        must_be_new=False,
    )
    (work / "report.json").write_text(serialized, encoding="utf-8")
    (work / "summary.md").write_text(summary, encoding="utf-8")
    return report
