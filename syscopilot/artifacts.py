import json
import os
import secrets
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from pydantic import BaseModel


def make_timestamp() -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    return f"{timestamp}_{os.getpid()}_{secrets.token_hex(3)}"


def ensure_runs_dir(path: str = "runs") -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def _as_dict(report: dict[str, Any] | BaseModel) -> dict[str, Any]:
    if isinstance(report, BaseModel):
        return report.model_dump()
    return report


def _atomic_write(path: Path, content: str) -> None:
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp_file:
        tmp_file.write(content)
        tmp_path = Path(tmp_file.name)
    os.replace(tmp_path, path)


def save_run(raw: str, report: dict[str, Any] | BaseModel, runs_dir: str = "runs") -> dict[str, str]:
    ensure_runs_dir(runs_dir)
    ts = make_timestamp()

    raw_path = Path(runs_dir) / f"raw_{ts}.txt"
    report_path = Path(runs_dir) / f"report_{ts}.json"

    _atomic_write(raw_path, raw)

    report_dict = _as_dict(report)
    report_json = json.dumps(
        report_dict,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=False,
    )
    _atomic_write(report_path, report_json)

    return {
        "raw_path": str(raw_path),
        "report_path": str(report_path),
    }


def save_json_error(raw: str, error: str, kind: str, runs_dir: str = "runs") -> str:
    ensure_runs_dir(runs_dir)
    ts = make_timestamp()
    err_path = Path(runs_dir) / f"json_error_{ts}.txt"

    contents = (
        f"MODEL_OUTPUT_FAILURE\n"
        f"kind: {kind}\n"
        f"error: {error}\n\n"
        f"---- RAW OUTPUT ----\n{raw}"
    )
    _atomic_write(err_path, contents)
    return str(err_path)
