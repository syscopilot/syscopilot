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


def _canonicalize(value: Any) -> Any:
    if isinstance(value, dict):
        canonical_dict = {key: _canonicalize(val) for key, val in value.items()}
        return dict(sorted(canonical_dict.items(), key=lambda item: item[0]))
    if isinstance(value, list):
        canonical_list = [_canonicalize(item) for item in value]
        if canonical_list and all(isinstance(item, dict) and "id" in item for item in canonical_list):
            return sorted(canonical_list, key=lambda item: str(item["id"]))
        return canonical_list
    return value


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


def save_spec_run(raw: str, spec: dict[str, Any] | BaseModel, runs_dir: str = "runs") -> dict[str, str]:
    ensure_runs_dir(runs_dir)
    ts = make_timestamp()

    raw_path = Path(runs_dir) / f"spec_raw_{ts}.txt"
    spec_path = Path(runs_dir) / f"spec_{ts}.json"

    _atomic_write(raw_path, raw)

    spec_dict = _canonicalize(_as_dict(spec))
    spec_json = json.dumps(
        spec_dict,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=False,
    )
    _atomic_write(spec_path, spec_json)

    return {
        "raw_path": str(raw_path),
        "spec_path": str(spec_path),
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


def save_design_turn(
    run_dir: str,
    turn_idx: int,
    user_message: str,
    response_dict: dict[str, Any],
    system_spec_dict: dict[str, Any],
    last_error_dict: dict[str, Any] | None,
) -> dict[str, str]:
    design_dir = Path(run_dir) / "design"
    design_dir.mkdir(parents=True, exist_ok=True)

    response_path = design_dir / "response.json"
    spec_path = design_dir / "system_spec.json"
    transcript_path = design_dir / "transcript.jsonl"

    canonical_response = _canonicalize(response_dict)
    canonical_spec = _canonicalize(system_spec_dict)
    canonical_error = _canonicalize(last_error_dict) if last_error_dict is not None else None

    _atomic_write(
        response_path,
        json.dumps(canonical_response, separators=(",", ":"), sort_keys=True, ensure_ascii=False),
    )
    _atomic_write(
        spec_path,
        json.dumps(canonical_spec, separators=(",", ":"), sort_keys=True, ensure_ascii=False),
    )

    transcript_record = {
        "turn": turn_idx,
        "user_message": user_message,
        "response": canonical_response,
        "last_error": canonical_error,
    }
    with transcript_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(transcript_record, separators=(",", ":"), sort_keys=True, ensure_ascii=False) + "\n")

    return {
        "response_path": str(response_path),
        "spec_path": str(spec_path),
        "transcript_path": str(transcript_path),
    }
