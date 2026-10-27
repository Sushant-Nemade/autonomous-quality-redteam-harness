import argparse
import importlib.util
import io
import json
import math
import statistics
import time
import unittest
from pathlib import Path
from xml.etree import ElementTree

PROFILES = {
    "Sushant-Nemade/ai-blog-publisher": (
        "unittest",
        "tests/test_publishing.py::PublishingTests::test_idempotent_publication_and_integrity",
        "approved idempotent publication and integrity",
    ),
    "Sushant-Nemade/gitpulse": (
        "unittest",
        "tests/test_api.py::ApiTests::test_authenticated_state_and_public_health",
        "authenticated local state and health API",
    ),
    "Sushant-Nemade/Doclify": (
        "pytest",
        "tests/test_pipeline.py::test_offline_draft_then_reviewed_publication",
        "offline draft, approval and publication",
    ),
    "Sushant-Nemade/MarketInsight": (
        "pytest",
        "tests/test_api.py::test_complete_research_save_reopen_clear_workflow",
        "mock-provider research, save, reopen and clear",
    ),
    "Sushant-Nemade/TravelBrain": (
        "pytest",
        "tests/test_api.py::test_actual_api_lifecycle",
        "offline local itinerary API lifecycle",
    ),
    "Sushant-Nemade/airbnb-price-workbench": (
        "pytest",
        "tests/test_runtime.py::test_actual_api_bounds_and_no_storage",
        "real local ONNX API contract and statelessness",
    ),
}


def repeated_workflows(repository: str, repetitions: int, output: Path) -> dict:
    if repository not in PROFILES or not 1 <= repetitions <= 1000:
        raise ValueError("Only reviewed profiles and 1-1000 local repetitions are allowed")
    mode, node, description = PROFILES[repository]
    started, cpu_started = time.monotonic(), time.process_time()
    latencies = []
    if mode == "unittest":
        filename, class_name, method = node.split("::")
        specification = importlib.util.spec_from_file_location("maintenance_owned_journey", filename)
        if specification is None or specification.loader is None:
            raise ValueError("Reviewed journey is unavailable")
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)
        case = getattr(module, class_name)

        class Result(unittest.TextTestResult):
            def startTest(self, test):
                self.before = time.monotonic()
                super().startTest(test)

            def stopTest(self, test):
                latencies.append(time.monotonic() - self.before)
                super().stopTest(test)

        suite = unittest.TestSuite(case(method) for _ in range(repetitions))
        result = unittest.TextTestRunner(stream=io.StringIO(), resultclass=Result).run(suite)
        counts = {
            "observed": result.testsRun,
            "failures": len(result.failures),
            "errors": len(result.errors),
            "skipped": len(result.skipped),
        }
    else:
        import pytest

        destination = output.with_suffix(".xml")
        status = pytest.main(
            [
                "-q",
                "-p",
                "no:cacheprovider",
                node,
                f"--count={repetitions}",
                "--repeat-scope=function",
                f"--junitxml={destination}",
            ],
        )
        if not destination.is_file() or destination.stat().st_size > 2_000_000:
            raise ValueError("Workflow evidence missing or oversized")
        root = ElementTree.fromstring(destination.read_bytes())
        cases = list(root.iter("testcase"))
        latencies = [float(case.get("time", "nan")) for case in cases]
        counts = {
            "observed": len(cases),
            "failures": sum(case.find("failure") is not None for case in cases),
            "errors": sum(case.find("error") is not None for case in cases),
            "skipped": sum(case.find("skipped") is not None for case in cases),
        }
        if status != 0 and not counts["failures"] and not counts["errors"]:
            counts["errors"] += 1
    finite = all(math.isfinite(value) and value >= 0 for value in latencies)
    percentiles = (
        statistics.quantiles(latencies, n=100, method="inclusive") if len(latencies) > 1 and finite else None
    )
    report = {
        "repository": repository,
        "scope": "Owned local regression journeys; Docker network isolation is enforced by the controller, not this script",
        "profile": description,
        "node": node,
        "requested_workflows": repetitions,
        **counts,
        "concurrency": 1,
        "duration_seconds": time.monotonic() - started,
        "cpu_process_seconds": time.process_time() - cpu_started,
        "journey_p95_ms": percentiles[94] * 1000 if percentiles else None,
        "journey_p99_ms": percentiles[98] * 1000 if percentiles else None,
        "http_request_count": None,
        "limitations": "Serial repeated regression journeys, NOT simultaneous users/browsers or a production capacity SLA. Test-defined mocks/fixtures remain in effect. HTTP requests are not independently counted.",
        "passed": finite
        and counts["observed"] == repetitions
        and not any(counts[key] for key in ["failures", "errors", "skipped"]),
    }
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--repetitions", type=int, default=1000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = repeated_workflows(args.repository, args.repetitions, args.output)
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
