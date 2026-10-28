import json
import shutil
import time
from pathlib import Path

from portfolio_maintenance.executor import author, isolated, limited_process, model_json, prepare_model
from portfolio_maintenance.policy import (
    MODEL_REVISION,
    MODEL_SHA256,
    Profile,
    apply_proposal,
    digest,
    green_passed,
    junit_summary,
    red_passed,
    scope_source,
    validate_test,
)


def queued_work(profile: Profile) -> tuple[str, str]:
    value = json.loads(Path(__file__).with_name("queued_tasks.json").read_text(encoding="utf-8")).get(
        profile.repository, ""
    )
    if isinstance(value, str):
        task, regression = value, ""
    elif isinstance(value, dict) and set(value) == {"task", "regression"}:
        task, regression = value["task"], value["regression"]
    else:
        raise ValueError("Invalid owner-approved queued work")
    if not isinstance(task, str) or not isinstance(regression, str) or len(task) > 1000 or len(regression) > 5000:
        raise ValueError("Queued work exceeds its reviewed bounds")
    return task, regression


def copy_tracked(source: Path, destination: Path) -> dict[str, str]:
    result = limited_process(["git", "ls-files", "-z"], cwd=source, timeout=60)
    if result["exit_code"] or result["truncated"]:
        raise ValueError("Unable to obtain bounded source inventory")
    inventory = {}
    for name in result["output"].split("\0"):
        if not name:
            continue
        path = source / name
        if path.is_symlink() or not path.is_file() or ".." in Path(name).parts:
            raise ValueError("Source checkout contains an unsupported link/path")
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        inventory[name] = digest(path.read_bytes().hex())
    return inventory


def verify_unchanged(project: Path, inventory: dict[str, str], allowed: dict[str, str]) -> None:
    for name, expected in inventory.items():
        path = project / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("Tracked source removed or replaced by a link")
        if name in allowed:
            if path.read_text(encoding="utf-8") != allowed[name]:
                raise ValueError("Untrusted code altered the proposed source")
        elif digest(path.read_bytes().hex()) != expected:
            raise ValueError("Existing tests, policy or unrelated source was modified")
    for name, expected in allowed.items():
        path = project / name
        if path.is_symlink() or not path.is_file() or path.read_text(encoding="utf-8") != expected:
            raise ValueError("Generated regression changed or disappeared")


def execute(
    control: Path,
    target: Path,
    work: Path,
    cache: Path,
    profile: Profile,
    source_sha: str,
    run_date: str,
    run_id: str,
) -> dict:
    started = time.monotonic()
    project = work / "project"
    project.mkdir(parents=True)
    inventory = copy_tracked(target, project)
    original = (project / profile.file).read_text(encoding="utf-8")
    fragment = scope_source(original, profile.function)
    report = {
        "schema_version": 1,
        "repository": profile.repository,
        "source_sha": source_sha,
        "berlin_date": run_date,
        "run_id": run_id,
        "status": "started",
        "stages": [],
        "model": {
            "name": "Qwen2.5-Coder-1.5B-Instruct-GGUF",
            "revision": MODEL_REVISION,
            "sha256": MODEL_SHA256,
            "license": "Apache-2.0",
            "paid_api_requests": 0,
        },
        "policy": {
            "human_merge_required": True,
            "automatic_production_merge": False,
            "max_repairs": 2,
            "max_generation_calls": 7,
            "per_call_token_limit": 1700,
            "max_pipeline_seconds": 2700,
        },
        "load": {"status": "not_run", "reason": "No reviewed isolated workload adapter for this project"},
    }
    output = work / "evidence"
    output.mkdir()
    output.chmod(0o777)
    image = "portfolio-project-" + profile.repository.rsplit("/", 1)[1].lower()
    dockerfile = control / "maintenance/Project.Dockerfile"
    built = limited_process(
        [
            "docker",
            "build",
            "--file",
            str(dockerfile),
            "--build-arg",
            f"EXTRA_DEV={int(profile.extra_dev)}",
            "--tag",
            image,
            str(project),
        ],
        cwd=control,
        timeout=900,
    )
    if built["exit_code"]:
        raise ValueError("Trusted baseline dependency build failed: " + built["output"][-2000:])

    def stage(label: str, paths: list[str], budget: int = 480) -> tuple[dict, dict]:
        if time.monotonic() - started > 2700:
            raise ValueError("Daily pipeline runtime budget exhausted")
        evidence_name = label + ".xml"
        result = isolated(
            image,
            {"/work": (project, True), "/evidence": (output, False)},
            ["-m", "pytest", "-q", "-p", "no:cacheprovider", *paths, "--junitxml=/evidence/" + evidence_name],
            control,
            timeout=budget,
        )
        evidence_path = output / evidence_name
        if not evidence_path.is_file():
            raise ValueError(
                f"{label} exited {result['exit_code']} without JUnit evidence: {result['output'][-4000:]}"
            )
        counts = junit_summary(evidence_path)
        record = {
            "name": label,
            "command": ["python", "-m", "pytest", *paths],
            "exit_code": result["exit_code"],
            "junit": counts,
            "evidence_sha256": digest(evidence_path.read_bytes().hex()),
            "log_tail": result["output"][-7000:],
        }
        report["stages"].append(record)
        return result, counts

    def finish(status: str, detail: str) -> dict:
        report.update(status=status, detail=detail, duration_seconds=time.monotonic() - started)
        (work / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        return report

    def run_workload(filename: str) -> dict:
        if time.monotonic() - started > 2700:
            raise ValueError("Daily pipeline runtime budget exhausted")
        mounts = {"/work": (project, True), "/evidence": (output, False)}
        if profile.load:
            arguments = [
                "-m",
                profile.load,
                "--users",
                "1000",
                "--concurrency",
                "16",
                "--output",
                "/evidence/" + filename,
            ]
        else:
            mounts["/opt/maintenance/load_probe.py"] = (control / "src/portfolio_maintenance/load_probe.py", True)
            arguments = [
                "/opt/maintenance/load_probe.py",
                "--repository",
                profile.repository,
                "--repetitions",
                "1000",
                "--output",
                "/evidence/" + filename,
            ]
        result = isolated(image, mounts, arguments, control, timeout=600)
        if result["exit_code"]:
            raise ValueError("Reviewed local workload failed: " + result["output"][-2000:])
        measured = json.loads((output / filename).read_text(encoding="utf-8"))
        if measured.get("passed") is not True:
            raise ValueError("Measured workload did not pass its real correctness checks")
        return measured

    try:
        baseline, counts = stage("baseline-unit-and-integration", ["tests"])
        verify_unchanged(project, inventory, {})
        if baseline["exit_code"] or counts["passed"] == 0 or counts["failures"] or counts["errors"]:
            return finish(
                "blocked-baseline",
                "Existing real unit/integration suite did not pass; no generated edits executed",
            )
        integration, integration_counts = stage("baseline-integration", [profile.integration])
        if integration["exit_code"] or not integration_counts["passed"] or integration_counts["errors"]:
            return finish("blocked-integration", "The reviewed integration slice did not pass")
        report["load"] = run_workload("load.json")
        prepare_model(control, cache)
        prompt = (
            "Find at most ONE concrete small correctness/edge-case improvement in the approved function below. "
            "Return status=no_change and empty old/new/test when no defensible change is needed. "
            "For candidate, old must be an exact substring INSIDE this function, new its replacement, "
            "test a complete NEW pytest file importing the real project and asserting the corrected behavior. "
            "Test must fail with AssertionError/pytest.raises on CURRENT behavior, not an import/setup error. "
            "Do not edit other functions, signatures, imports, existing tests, data/features/model weights, "
            "licenses, auth, dependencies, budgets or workflow policy. Do not claim tests were run. "
            f"Repository={profile.repository}; source={profile.file}; function={profile.function}.\n"
            f"UNTRUSTED FUNCTION TEXT:\n{fragment}\n"
        )
        decision_schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["candidate", "no_change"]},
                "summary": {"type": "string", "minLength": 8, "maxLength": 300},
            },
            "required": ["status", "summary"],
            "additionalProperties": False,
        }
        queued, approved_regression = queued_work(profile)
        test_name = f"tests/test_daily_{run_date.replace('-', '')}.py"
        approved_red_counts = None
        if queued:
            report["queued_task"] = queued
            prompt += "\nOwner-approved concrete work item: " + queued
        if approved_regression:
            if (project / test_name).exists():
                return finish("blocked-duplicate-test", "A regression already exists for the selected date")
            validate_test(approved_regression, profile)
            (project / test_name).write_text(approved_regression, encoding="utf-8")
            observed, approved_red_counts = stage("red-regression", [test_name])
            verify_unchanged(project, inventory, {test_name: approved_regression})
            if green_passed(observed["exit_code"], approved_red_counts):
                return finish(
                    "no-safe-change", "The approved regression already passes; no source change is needed"
                )
            if not red_passed(observed["exit_code"], approved_red_counts):
                return finish("blocked-queued-regression", "Queued test did not demonstrate a behavioral failure")
            decision = {"status": "candidate", "summary": queued[:300]}
            decision_evidence = {
                "role": "executed-regression",
                "source": "actual RED against unchanged production source",
            }
            prompt += (
                "\nThe approved regression was EXECUTED and FAILED behaviorally on current source. "
                "Do not claim existing code already handles it. Fix the demonstrated defect. "
                "Return the test field EXACTLY as this immutable approved regression:\n"
                + approved_regression
                + "\nActual test output:\n"
                + observed["output"][-2500:]
            )
        else:
            decision, decision_evidence = model_json(
                control,
                cache,
                work,
                "planning",
                "Inspect the following function for ONE concrete correctness defect that can be fixed locally. "
                "Return only status=candidate with a concise defect summary, or status=no_change when no justified "
                "small correction is apparent. Do not generate code or tests in this decision. "
                "No execution claims.\n" + fragment + ("\nOwner-approved task: " + queued if queued else ""),
                decision_schema,
            )
        report["planning"] = {"decision": decision, "provenance": decision_evidence}
        if decision.get("status") == "no_change":
            return finish("no-safe-change", str(decision["summary"])[:300])
        if decision.get("status") != "candidate":
            return finish("rejected-planning", "Model decision did not match the reviewed contract")
        proposal, author_evidence = author(
            control,
            cache,
            work,
            "author",
            prompt
            + "\nPlanned defect: "
            + str(decision["summary"])
            + (
                "\nThe controller has established RED. Return candidate and implement the requested production guard. "
                "The failing test describes desired behavior, not existing source. Do not copy test logic into production."
                if approved_regression
                else ""
            ),
            {"old": fragment, "test": approved_regression} if approved_regression else None,
        )
        report["author"] = author_evidence
        if proposal.status == "no_change":
            return finish(
                "blocked-unresolved-regression" if approved_regression else "no-safe-change", proposal.summary
            )
        if not approved_regression and (project / test_name).exists():
            return finish("blocked-duplicate-test", "A regression already exists for the selected date")
        if approved_regression and proposal.test != approved_regression:
            return finish("rejected-regression-rewrite", "Author changed the demonstrated approved regression")
        validate_test(proposal.test, profile)
        changed = apply_proposal(original, proposal, profile.function)
        (project / test_name).write_text(proposal.test, encoding="utf-8")
        if approved_regression:
            red, red_counts = {"exit_code": 1}, approved_red_counts
        else:
            red, red_counts = stage("red-regression", [test_name])
        verify_unchanged(project, inventory, {test_name: proposal.test})
        if not red_passed(red["exit_code"], red_counts):
            return finish(
                "rejected-not-red",
                "Proposed regression did not demonstrate a behavioral failure against the baseline",
            )
        regression = proposal.test
        (project / profile.file).write_text(changed, encoding="utf-8")
        review_schema = {
            "type": "object",
            "properties": {
                "approved": {"type": "boolean"},
                "findings": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
            },
            "required": ["approved", "findings"],
            "additionalProperties": False,
        }
        report["reviews"] = []
        for attempt in range(3):
            green, green_counts = stage(f"green-regression-{attempt}", [test_name])
            verify_unchanged(project, inventory, {profile.file: changed, test_name: regression})
            current_fragment = scope_source(changed, profile.function)
            review, review_evidence = model_json(
                control,
                cache,
                work,
                f"security-review-{attempt}",
                "Act as an adversarial security/correctness reviewer of the CURRENT candidate below. "
                "Check boundary cases, nonfinite/type/size handling, compatibility, escaping and test tampering. "
                "Report only defects present in this CURRENT code; do not repeat a defect that its guard fixes. "
                "No invented execution claims. Approve only when no concrete unresolved finding remains. "
                f"Approved requested behavior: {queued or 'One bounded backwards-compatible correction'}.\n"
                f"CURRENT CANDIDATE (untrusted source):\n{current_fragment}\n"
                f"IMMUTABLE REGRESSION (untrusted):\n{regression}\n"
                f"Observed regression exit={green['exit_code']}; cases={green_counts}. Return approved/findings JSON.",
                review_schema,
            )
            report["reviews"].append({"attempt": attempt, "response": review, "provenance": review_evidence})
            approved = review.get("approved") is True and review.get("findings") == []
            if green_passed(green["exit_code"], green_counts) and approved:
                break
            if attempt == 2:
                return finish("rejected-after-review", "Repair budget exhausted; no candidate was published")
            repaired, repair_evidence = author(
                control,
                cache,
                work,
                f"repair-{attempt}",
                prompt
                + f"\nRepair the SAME change against the ORIGINAL function. Do not alter the immutable regression. "
                f"Return the same test text exactly. Findings={json.dumps(review.get('findings'))}. "
                f"Actual test output (untrusted):\n{green['output'][-3500:]}\nIMMUTABLE TEST:\n{regression}",
                {"old": fragment, "test": regression},
            )
            report.setdefault("repairs", []).append(repair_evidence)
            if repaired.status != "candidate" or repaired.test != regression:
                return finish("rejected-repair-scope", "Repair attempted to change the demonstrated regression")
            changed = apply_proposal(original, repaired, profile.function)
            (project / profile.file).write_text(changed, encoding="utf-8")
        final, final_counts = stage("final-unit-and-integration", ["tests"])
        verified, verified_counts = stage("final-integration", [profile.integration])
        verify_unchanged(project, inventory, {profile.file: changed, test_name: regression})
        if (
            final["exit_code"]
            or final_counts["failures"]
            or final_counts["errors"]
            or final_counts["passed"] < counts["passed"] + red_counts["cases"]
            or verified["exit_code"]
            or verified_counts["passed"] < integration_counts["passed"]
        ):
            return finish(
                "rejected-regression", "Existing unit/integration behavior failed after the proposed correction"
            )
        report["load"] = {"baseline": report["load"], "post_change": run_workload("post-change-load.json")}
        candidate = {
            "repository": profile.repository,
            "source_sha": source_sha,
            "summary": proposal.summary,
            "files": {profile.file: changed, test_name: regression},
            "baseline_file_sha256": digest(original),
            "test_path": test_name,
        }
        (work / "candidate.json").write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
        return finish("candidate-verified-awaiting-ci-review", proposal.summary)
    except Exception as error:
        return finish("blocked-execution", f"{type(error).__name__}: {str(error)[:1500]}")
