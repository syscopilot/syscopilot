import json
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from .llm import EmptyModelOutput, InvalidModelJSON, extract_text, resolve_client
from .models import Mode, Report, ReportLike, ShortReport
from .prompts import SCHEMAS, SIZE_CONSTRAINTS, SYSTEM_PROMPT, USER_TEMPLATE


@dataclass(frozen=True)
class AnalysisResult:
    report: ReportLike
    raw: str


def _validate_report(data: dict, mode: Mode) -> ReportLike:
    if mode == "full":
        return Report.model_validate(data)
    return ShortReport.model_validate(data)


def analyze_system(
    description: str,
    mode: Mode = "short",
    *,
    client: Any | None = None,
    api_key: str | None = None,
) -> AnalysisResult:
    resolved_client = resolve_client(client=client, api_key=api_key)

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

    raw = extract_text(resp)

    if not raw.strip():
        raise EmptyModelOutput()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise InvalidModelJSON(raw_text=raw, error=str(e), kind="json_decode") from e

    try:
        report = _validate_report(data, mode)
    except ValidationError as e:
        raise InvalidModelJSON(raw_text=raw, error=str(e), kind="schema_validation") from e
    return AnalysisResult(report=report, raw=raw)
