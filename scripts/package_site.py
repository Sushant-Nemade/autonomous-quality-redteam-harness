"""Package static master report into src/harness/site/data/ for FastAPI and GitHub Pages."""

from __future__ import annotations

import json
from pathlib import Path

from harness.cli import (
    DEFAULT_REPORT_PATH,
    DEFAULT_SUMMARY_MD_PATH,
    format_daily_summary_markdown,
    run_harness_suite,
)

ROOT = Path(__file__).resolve().parents[1]
SITE_DATA_DIR = ROOT / "src" / "harness" / "site" / "data"


def build_site_data() -> None:
    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    report = run_harness_suite(selector="all", virtual_users=1000, run_date="2026-10-27")
    report_json = json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n"

    DEFAULT_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_REPORT_PATH.write_text(report_json, encoding="utf-8")
    DEFAULT_SUMMARY_MD_PATH.write_text(format_daily_summary_markdown(report), encoding="utf-8")

    (SITE_DATA_DIR / "daily_improvement_report.json").write_text(report_json, encoding="utf-8")
    print(f"Packaged 7-project 1,000-user report into {SITE_DATA_DIR}")


if __name__ == "__main__":
    build_site_data()
