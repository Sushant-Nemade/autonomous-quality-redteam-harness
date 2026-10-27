import argparse
import base64
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from portfolio_maintenance.pipeline import execute
from portfolio_maintenance.policy import EPOCH, ZONE, local_date, profile_for, registry, run_key, selection
from portfolio_maintenance.publisher import api, publish


def globally_paused() -> bool:
    record = api(
        "GET", "repos/Sushant-Nemade/autonomous-quality-redteam-harness/contents/maintenance/control.json?ref=main"
    )
    if not record or record.get("size", 1001) > 1000:
        raise ValueError("Global maintenance switch is unavailable; refusing unattended execution")
    state = json.loads(base64.b64decode(record["content"]))
    if not isinstance(state, dict) or set(state) != {"paused"} or not isinstance(state["paused"], bool):
        raise ValueError("Invalid global maintenance switch")
    return state["paused"]


def preflight(pilot: bool) -> dict:
    repository = os.environ["GITHUB_REPOSITORY"]
    profile_for(repository)
    day = local_date()
    paused = globally_paused() or os.environ.get("MAINTENANCE_DISABLED") == "1"
    selected = not paused and (pilot or selection(day).repository == repository)
    output = {
        "selected": str(selected).lower(),
        "date": day.isoformat(),
        "key": run_key(repository, day, pilot, os.environ["GITHUB_RUN_ID"]),
        "source_sha": os.environ["GITHUB_SHA"],
        "skip_reason": "",
    }
    if (
        not re.fullmatch(r"[a-f0-9]{40}", output["source_sha"])
        or os.environ.get("GITHUB_REF") != "refs/heads/main"
    ):
        raise ValueError("Maintenance can only start from the exact trusted main revision")
    if selected:
        marker = api("GET", f"repos/{repository}/contents/runs/{output['key']}.json?ref=maintenance-reports")
        if marker:
            output.update(selected="false", skip_reason="already-recorded-for-this-local-date")
        else:
            open_prs = api("GET", f"repos/{repository}/pulls?state=open&per_page=100") or []
            if len(open_prs) == 100 or any(item["head"]["ref"].startswith("maintenance/") for item in open_prs):
                output["skip_reason"] = (
                    "An earlier maintenance PR still requires human review; no duplicate proposal attempted"
                )
    destination = os.environ.get("GITHUB_OUTPUT")
    if destination:
        with Path(destination).open("a", encoding="utf-8") as handle:
            for name, value in output.items():
                handle.write(f"{name}={value}\n")
    return output


def run(args) -> dict:
    profile = profile_for(args.repository)
    args.work.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": 1,
        "repository": args.repository,
        "source_sha": args.source_sha,
        "berlin_date": args.date,
        "run_id": args.run_id,
        "stages": [],
        "status": "blocked-execution",
    }
    if args.skip_reason:
        report.update(status="awaiting-existing-human-review", detail=args.skip_reason)
    else:
        try:
            report = execute(
                args.control, args.target, args.work, args.cache, profile, args.source_sha, args.date, args.run_id
            )
        except Exception as error:
            report["detail"] = f"{type(error).__name__}: {str(error)[:1500]}"
    report["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    (args.work / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return report


def monitor(control_repository: str) -> dict:
    if globally_paused():
        return {"paused": True, "status": "Global owner kill switch enabled; no missed-run alert"}
    current = datetime.now(timezone.utc).astimezone(ZONE)
    day = current.date()
    if day < EPOCH or current.hour < 15:
        return {"berlin_date": day.isoformat(), "status": "not-due-before-cutoff"}
    expected = selection(day)
    key = run_key(expected.repository, day, False, "1")
    record = api("GET", f"repos/{expected.repository}/contents/runs/{key}.json?ref=maintenance-reports")
    outcome = {
        "berlin_date": day.isoformat(),
        "expected_repository": expected.repository,
        "scheduled_report_present": bool(record),
        "scope": "GitHub-hosted monitor; not an external availability guarantee",
    }
    blocked = False
    if record:
        actual = json.loads(base64.b64decode(record["content"]))
        blocked = str(actual.get("status", "")).startswith(("blocked", "rejected"))
        outcome["reported_status"] = actual.get("status")
    if not record or blocked:
        reason = "blocked or rejected maintenance" if blocked else "missing scheduled evidence"
        title = f"Maintenance alert: {day.isoformat()} {reason}"
        issues = api("GET", f"repos/{control_repository}/issues?state=open&per_page=100") or []
        if not any(issue["title"] == title for issue in issues):
            api(
                "POST",
                f"repos/{control_repository}/issues",
                {
                    "title": title,
                    "body": f"The 15:00 Europe/Berlin monitor found {reason} for {expected.repository}. "
                    "Check workflow failure, schedule delay/disabling, permission changes and the kill switch. "
                    "Do not interpret missing evidence as a pass. Manual recovery must use the same local-date deduplication policy.",
                },
            )
    return outcome


def main() -> None:
    parser = argparse.ArgumentParser(description="Real bounded portfolio maintenance; no legacy fixture outcomes")
    subcommands = parser.add_subparsers(dest="command", required=True)
    checking = subcommands.add_parser("preflight")
    checking.add_argument("--pilot", action="store_true")
    running = subcommands.add_parser("run")
    for name in ["control", "target", "work", "cache"]:
        running.add_argument("--" + name, type=Path, required=True)
    for name in ["repository", "source-sha", "date", "run-id"]:
        running.add_argument("--" + name, required=True)
    running.add_argument("--skip-reason", default="")
    publishing = subcommands.add_parser("publish")
    publishing.add_argument("--work", type=Path, required=True)
    publishing.add_argument("--baseline", type=Path, required=True)
    publishing.add_argument("--key", required=True)
    monitoring = subcommands.add_parser("monitor")
    monitoring.add_argument("--repository", default="Sushant-Nemade/autonomous-quality-redteam-harness")
    subcommands.add_parser("registry")
    args = parser.parse_args()
    if args.command == "preflight":
        result = preflight(args.pilot)
    elif args.command == "run":
        result = run(args)
    elif args.command == "publish":
        result = publish(args.work, args.baseline, args.key)
    elif args.command == "monitor":
        result = monitor(args.repository)
    else:
        result = [profile.model_dump() for profile in registry()]
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
