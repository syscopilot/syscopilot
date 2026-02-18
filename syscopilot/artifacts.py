import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def make_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def ensure_runs_dir(path: str = "runs") -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def _as_dict(report: dict[str, Any] | BaseModel) -> dict[str, Any]:
    if isinstance(report, BaseModel):
        return report.model_dump()
    return report


def save_run(raw: str, report: dict[str, Any] | BaseModel, runs_dir: str = "runs") -> dict[str, str]:
    ensure_runs_dir(runs_dir)
    ts = make_timestamp()

    raw_path = Path(runs_dir) / f"raw_{ts}.txt"
    report_path = Path(runs_dir) / f"report_{ts}.json"

    raw_path.write_text(raw, encoding="utf-8")

    report_dict = _as_dict(report)
    report_json = json.dumps(
        report_dict,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=False,
    )
    report_path.write_text(report_json, encoding="utf-8")

    return {
        "raw_path": str(raw_path),
        "report_path": str(report_path),
    }


def save_json_error(raw: str, error: str, runs_dir: str = "runs") -> str:
    ensure_runs_dir(runs_dir)
    ts = make_timestamp()
    err_path = Path(runs_dir) / f"json_error_{ts}.txt"

    contents = f"JSONDecodeError: {error}\n\n---- RAW OUTPUT ----\n{raw}"
    err_path.write_text(contents, encoding="utf-8")
    return str(err_path)
