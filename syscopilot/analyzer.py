import json
from dataclasses import dataclass
from typing import Any

from anthropic import Anthropic

from .models import Mode, Report, ReportLike, ShortReport
from .prompts import SCHEMAS, SIZE_CONSTRAINTS, SYSTEM_PROMPT, USER_TEMPLATE


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
    return "".join(parts).strip()


def _validate_report(data: dict, mode: Mode) -> ReportLike:
    if mode == "full":
        return Report.model_validate(data)
    return ShortReport.model_validate(data)


def _resolve_client(client: Any | None = None, api_key: str | None = None) -> Any:
    if client is not None:
        return client
    if not api_key:
        raise RuntimeError("api_key is required when client is not provided")
    return Anthropic(api_key=api_key)


def analyze_system(
    description: str,
    mode: Mode = "short",
    *,
    client: Any | None = None,
    api_key: str | None = None,
) -> AnalysisResult:
    resolved_client = _resolve_client(client=client, api_key=api_key)

    prompt = USER_TEMPLATE.format(
        description=description,
        schema=SCHEMAS[mode],
        size_constraints=SIZE_CONSTRAINTS[mode],
    )

    resp = resolved_client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2000,
        temperature=0.0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = _extract_text(resp)

    try:
        data = json.loads(raw)
        report = _validate_report(data, mode)
    except (json.JSONDecodeError, ValueError) as e:
        raise InvalidModelJSON(raw_text=raw, error=str(e)) from e
    return AnalysisResult(report=report, raw=raw)
