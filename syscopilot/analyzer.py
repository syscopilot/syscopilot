import json
import os
from datetime import datetime

from anthropic import Anthropic
from dotenv import load_dotenv

from .models import Mode, Report, ReportLike, ShortReport
from .prompts import SCHEMAS, SIZE_CONSTRAINTS, SYSTEM_PROMPT, USER_TEMPLATE

load_dotenv()


def _extract_text(resp) -> str:
    parts = []
    for block in resp.content:
        if hasattr(block, "text") and block.text:
            parts.append(block.text)
    return "\n".join(parts).strip()


def _validate_report(data: dict, mode: Mode) -> ReportLike:
    if mode == "full":
        return Report.model_validate(data)
    return ShortReport.model_validate(data)


def analyze_system(description: str, mode: Mode = "short") -> ReportLike:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not found in .env")

    client = Anthropic(api_key=api_key)

    prompt = USER_TEMPLATE.format(
        description=description,
        schema=SCHEMAS[mode],
        size_constraints=SIZE_CONSTRAINTS[mode],
    )

    resp = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2000,
        temperature=0.0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = _extract_text(resp)

    os.makedirs("runs", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    raw_path = os.path.join("runs", f"raw_{ts}.txt")
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        err_path = os.path.join("runs", f"json_error_{ts}.txt")
        with open(err_path, "w", encoding="utf-8") as f:
            f.write(f"JSONDecodeError: {e}\n\n")
            f.write("---- RAW OUTPUT ----\n")
            f.write(raw)
        raise RuntimeError(
            f"Model returned invalid JSON. Saved raw output to {raw_path} and error to {err_path}"
        ) from e

    report = _validate_report(data, mode)

    report_path = os.path.join("runs", f"report_{ts}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report.model_dump_json())

    return report
