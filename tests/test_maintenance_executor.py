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
