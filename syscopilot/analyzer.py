import json
import os
from dataclasses import dataclass

from anthropic import Anthropic
from dotenv import load_dotenv

from .models import Mode, Report, ReportLike, ShortReport
from .prompts import SCHEMAS, SIZE_CONSTRAINTS, SYSTEM_PROMPT, USER_TEMPLATE

load_dotenv()


class InvalidModelJSON(ValueError):
    def __init__(self, raw_text: str, error: str):
        super().__init__(f"Model returned invalid JSON: {error}")
        self.raw_text = raw_text
        self.error = error


@dataclass(frozen=True)
class AnalysisResult:
    report: ReportLike
    raw: str


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


def analyze_system(description: str, mode: Mode = "short") -> AnalysisResult:
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

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise InvalidModelJSON(raw_text=raw, error=str(e)) from e

    report = _validate_report(data, mode)
    return AnalysisResult(report=report, raw=raw)
