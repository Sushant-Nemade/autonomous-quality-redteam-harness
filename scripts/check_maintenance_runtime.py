import json
from pathlib import Path

from portfolio_maintenance.executor import model_json, prepare_model

root = Path(__file__).resolve().parents[1]
cache = root / ".cache/maintenance"
prepare_model(root, cache)
schema = {
    "type": "object",
    "properties": {"approved": {"type": "boolean"}, "findings": {"type": "array", "items": {"type": "string"}}},
    "required": ["approved", "findings"],
    "additionalProperties": False,
}
payload, evidence = model_json(
    root,
    cache,
    root / "build/runtime-check",
    "runtime-check",
    'Inspect this Python function: def identity(value): return value. There is no requested behavior change. Return {"approved":true,"findings":[]} if it preserves its input. Do not invent executed tests.',
    schema,
)
assert payload == {"approved": True, "findings": []}, payload
report = {
    "status": "real-isolated-inference-passed",
    "model_response": payload,
    "execution": evidence,
    "scope": "Runtime smoke only, not project testing, security certification or a maintenance activation",
}
destination = root / "build/runtime-check/report.json"
destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
