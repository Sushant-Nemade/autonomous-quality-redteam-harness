from pathlib import Path

import pytest

from portfolio_maintenance.executor import docker_command, downloaded, minimal_environment, model_json


def test_generated_execution_has_no_network_privileges_or_credentials(tmp_path, monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "must-not-be-inherited")
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-be-inherited")
    environment = minimal_environment()
    assert "GH_TOKEN" not in environment and "OPENAI_API_KEY" not in environment
    command = docker_command("reviewed-image", {"/work": (tmp_path, True)}, "test-run", ["-m", "pytest"])
    for required in [
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--memory=4g",
        "--pids-limit=128",
        "--cpus=2",
    ]:
        assert required in command
    assert any("target=/work,readonly" in argument for argument in command)
    assert not any("docker.sock" in argument or "TOKEN" in argument for argument in command)


def test_modified_cached_model_fails_closed_before_any_download(tmp_path):
    destination = tmp_path / "model.gguf"
    destination.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        downloaded("https://example.invalid/never-called", destination, 100, "0" * 64)
    assert destination.read_bytes() == b"tampered"


def test_runtime_flags_are_not_editable_by_generated_project_code():
    root = Path(__file__).resolve().parents[1]
    dockerfile = (root / "maintenance/Model.Dockerfile").read_text()
    assert "USER 10001:10001" in dockerfile
    assert "llama-completion" in dockerfile


def test_dependency_locations_survive_the_readonly_source_mount():
    root = Path(__file__).resolve().parents[1]
    dockerfile = (root / "maintenance/Project.Dockerfile").read_text()
    assert "UV_PROJECT_ENVIRONMENT=/opt/venv" in dockerfile
    assert "UV_PYTHON=/usr/local/bin/python" in dockerfile
    assert "UV_PYTHON_DOWNLOADS=never" in dockerfile
    assert "mv frontend/node_modules /node_modules" in dockerfile
    assert "mv node_modules /node_modules" in dockerfile


def test_completion_preserves_generated_token_output_while_suppressing_metadata(tmp_path, monkeypatch):
    calls = []

    def run_isolated(image, mounts, args, control, timeout):
        calls.append(args)
        return {"exit_code": 0, "truncated": False, "output": '{"approved":true,"findings":[]}\n[end of text]'}

    monkeypatch.setattr("portfolio_maintenance.executor.isolated", run_isolated)
    payload, evidence = model_json(tmp_path, tmp_path, tmp_path, "review", "Review identity", {"type": "object"})
    assert payload["approved"] and evidence["role"] == "review"
    assert "--log-disable" not in calls[0], (
        "llama-completion emits generated tokens through generic LOG; disabling logs removes the answer"
    )
    assert calls[0][calls[0].index("--log-verbosity") + 1] == "0"


def test_executed_red_cannot_be_reclassified_as_no_change_or_rewrite_its_test(tmp_path, monkeypatch):
    from portfolio_maintenance import executor

    observed = []

    def response(control, cache, work, role, prompt, schema):
        observed.append(schema)
        return {
            "status": "candidate",
            "summary": "Reject a negative budget",
            "old": "return value",
            "new": "return value[:1]",
            "test": "assert True",
        }, {}

    monkeypatch.setattr(executor, "model_json", response)
    executor.author(
        tmp_path,
        tmp_path,
        tmp_path,
        "author",
        "Repair executed RED",
        {"old": "return value", "test": "assert True"},
    )
    assert observed[0]["properties"]["status"]["const"] == "candidate"
    assert observed[0]["properties"]["old"]["const"] == "return value"
    assert observed[0]["properties"]["test"]["const"] == "assert True"


def test_separate_pinned_reviewer_has_explicit_resource_budget(tmp_path, monkeypatch):
    from portfolio_maintenance import executor
    from portfolio_maintenance.policy import REVIEWER_BYTES, REVIEWER_FILE, REVIEWER_SHA256

    downloads, invocations = [], []

    def fake_download(*args, **kwargs):
        downloads.append((args, kwargs))

    def fake_inference(image, mounts, args, control, timeout):
        invocations.append(args)
        return {"exit_code": 0, "truncated": False, "output": '{"approved":true,"findings":[]}'}

    monkeypatch.setattr(executor, "downloaded", fake_download)
    monkeypatch.setattr(executor, "isolated", fake_inference)
    payload, evidence = executor.model_json(
        tmp_path, tmp_path, tmp_path, "security-review-0", "Review current candidate", {"type": "object"}
    )
    assert payload["approved"]
    assert evidence["model_sha256"] == REVIEWER_SHA256
    assert invocations[0][1].endswith(REVIEWER_FILE)
    assert downloads[0][0][2] == REVIEWER_BYTES
    assert downloads[0][1]["expected_size"] == REVIEWER_BYTES
    command = executor.docker_command("portfolio-maintenance-model", {}, "review", invocations[0])
    assert "--memory=8g" in command
    assert "--network=none" in command and "--cap-drop=ALL" in command
