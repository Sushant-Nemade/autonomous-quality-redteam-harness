import ast
import hashlib
import json
import re
from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

EPOCH = date(2026, 10, 28)
ZONE = ZoneInfo("Europe/Berlin")
MODEL_REVISION = "f86cb2c1fa58255f8052cc32aeede1b7482d4361"
MODEL_FILE = "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
MODEL_SHA256 = "cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046"
MODEL_BYTES = 1_117_320_768
LLAMA_REVISION = "a919179942157e0554f92c1c6f31ac874f50b40a"
REVIEWER_REVISION = "13fb94bfda8c8cf22497dc57b78f391a9acb426a"
REVIEWER_FILE = "qwen2.5-coder-7b-instruct-q4_k_m.gguf"
REVIEWER_SHA256 = "509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c"
REVIEWER_BYTES = 4_683_073_536


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    repository: str = Field(pattern=r"^Sushant-Nemade/[A-Za-z0-9._-]+$")
    file: str
    function: str
    integration: str
    extra_dev: bool
    ci: str
    load: str | None


class Proposal(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    status: str = Field(pattern=r"^(candidate|no_change)$")
    summary: str = Field(min_length=8, max_length=500)
    old: str = Field(max_length=2500)
    new: str = Field(max_length=4000)
    test: str = Field(max_length=5000)


def registry() -> tuple[Profile, ...]:
    payload = json.loads(Path(__file__).with_name("registry.json").read_text(encoding="utf-8"))
    profiles = tuple(Profile.model_validate(item) for item in payload)
    if len(profiles) != 7 or len({item.repository for item in profiles}) != 7:
        raise ValueError("Registry must contain exactly seven distinct reviewed projects")
    return profiles


def profile_for(repository: str) -> Profile:
    return next(profile for profile in registry() if profile.repository == repository)


def local_date(now: datetime | None = None) -> date:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("A timezone-aware timestamp is required")
    return current.astimezone(ZONE).date()


def selection(day: date) -> Profile:
    profiles = registry()
    return profiles[(day - EPOCH).days % len(profiles)]


def run_key(repository: str, day: date, pilot: bool, run_id: str) -> str:
    profile_for(repository)
    if not re.fullmatch(r"[1-9][0-9]{0,20}", run_id):
        raise ValueError("Invalid run identifier")
    suffix = f"-pilot-{run_id}" if pilot else ""
    return f"maintenance-{day.isoformat()}{suffix}"


def digest(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def function_node(tree: ast.Module, qualified: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    parts = qualified.split(".")
    body = tree.body
    for index, name in enumerate(parts):
        node = next(
            (
                node
                for node in body
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
            ),
            None,
        )
        if node is None:
            raise ValueError("Reviewed function is missing")
        if index == len(parts) - 1:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                raise ValueError("Reviewed scope is not a function")
            return node
        body = node.body
    raise ValueError("Invalid function scope")


def scope_source(source: str, qualified: str) -> str:
    node = function_node(ast.parse(source), qualified)
    return "".join(source.splitlines(keepends=True)[node.lineno - 1 : node.end_lineno])


def masked_tree(source: str, qualified: str) -> str:
    tree = deepcopy(ast.parse(source))
    node = function_node(tree, qualified)
    node.body = [ast.Pass()]
    return ast.dump(tree, include_attributes=False)


def apply_proposal(source: str, proposal: Proposal, qualified: str) -> str:
    if proposal.status != "candidate" or not proposal.old.strip() or proposal.old == proposal.new:
        raise ValueError("A meaningful candidate replacement is required")
    if any(token in proposal.new for token in ["__import__", "__builtins__", "pytest", "unittest", "sys.modules"]):
        raise ValueError("Test/runtime tampering is forbidden")
    fragment = scope_source(source, qualified)
    if fragment.count(proposal.old) != 1:
        raise ValueError("Old text must match exactly once inside the approved function")
    if len(proposal.new.splitlines()) > 75 or len(proposal.old.splitlines()) > 50:
        raise ValueError("Proposal exceeds the bounded diff budget")
    node = function_node(ast.parse(source), qualified)
    lines = source.splitlines(keepends=True)
    changed = (
        "".join(lines[: node.lineno - 1])
        + fragment.replace(proposal.old, proposal.new, 1)
        + "".join(lines[node.end_lineno :])
    )
    if masked_tree(source, qualified) != masked_tree(changed, qualified):
        raise ValueError("Changes outside the approved function are forbidden")
    imports_before = {
        ast.dump(item) for item in ast.walk(ast.parse(source)) if isinstance(item, (ast.Import, ast.ImportFrom))
    }
    for item in ast.walk(ast.parse(changed)):
        if isinstance(item, (ast.Import, ast.ImportFrom)) and ast.dump(item) not in imports_before:
            raise ValueError("Generated production imports are forbidden")
        if (
            isinstance(item, ast.Call)
            and isinstance(item.func, ast.Name)
            and item.func.id in {"exec", "eval", "compile", "breakpoint"}
        ):
            raise ValueError("Dynamic code execution is forbidden")
    return changed


def validate_test(source: str, project: Profile) -> None:
    tree = ast.parse(source)
    has_assertion = any(isinstance(item, ast.Assert) for item in ast.walk(tree))
    has_expected_exception = any(
        isinstance(item, ast.With)
        and any(
            isinstance(context.context_expr, ast.Call)
            and isinstance(context.context_expr.func, ast.Attribute)
            and isinstance(context.context_expr.func.value, ast.Name)
            and context.context_expr.func.value.id == "pytest"
            and context.context_expr.func.attr == "raises"
            for context in item.items
        )
        for item in ast.walk(tree)
    )
    if not has_assertion and not has_expected_exception:
        raise ValueError("Regression must contain an actual assertion")
    allowed = {"pytest", project.file.split("/")[0], "src", "airbnb_price", "boston_housing"}
    imported = False
    for item in ast.walk(tree):
        if isinstance(item, ast.Import):
            roots = {alias.name.split(".")[0] for alias in item.names}
        elif isinstance(item, ast.ImportFrom):
            roots = {(item.module or "").split(".")[0]}
        else:
            roots = set()
        if roots - allowed:
            raise ValueError("Regression import is outside its reviewed project/pytest scope")
        imported |= bool(roots - {"pytest"})
        if isinstance(item, ast.Attribute) and item.attr in {
            "skip",
            "xfail",
            "exit",
            "main",
            "setattr",
            "setitem",
            "__dict__",
            "__globals__",
        }:
            raise ValueError("Regression may not skip, exit or rewrite test/runtime state")
    if not imported:
        raise ValueError("Regression must import the actual project under test")


def junit_summary(path: Path) -> dict:
    if path.stat().st_size > 2_000_000:
        raise ValueError("JUnit report exceeds evidence size limit")
    raw = path.read_bytes()
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("DTD/entity evidence is forbidden")
    root = ElementTree.fromstring(raw)
    cases = list(root.iter("testcase"))
    if not cases or len(cases) > 5000:
        raise ValueError("Evidence must include actual bounded test case records")
    counts = {"cases": len(cases), "failures": 0, "errors": 0, "skipped": 0}
    for case in cases:
        for key, tag in [("failures", "failure"), ("errors", "error"), ("skipped", "skipped")]:
            counts[key] += case.find(tag) is not None
    counts["passed"] = counts["cases"] - counts["failures"] - counts["errors"] - counts["skipped"]
    return counts


def red_passed(exit_code: int, evidence: dict) -> bool:
    return exit_code == 1 and evidence["failures"] > 0 and evidence["errors"] == 0 and evidence["skipped"] == 0


def green_passed(exit_code: int, evidence: dict) -> bool:
    return exit_code == 0 and evidence["passed"] == evidence["cases"] and evidence["cases"] > 0
