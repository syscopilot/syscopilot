import json
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from .analyzer import EmptyModelOutput, InvalidModelJSON, _extract_text, _resolve_client
from .models import Mode, SystemSpec
from .spec_prompts import (
    EXTRACT_TEMPLATE,
    PROPOSE_TEMPLATE,
    SPEC_SIZE_CONSTRAINTS,
    SYSTEM_SPEC_PROMPT,
    SYSTEM_SPEC_SCHEMA,
)


@dataclass(frozen=True)
class SpecResult:
    spec: SystemSpec
    raw: str


def _run_spec_prompt(
    description: str,
    template: str,
    mode: Mode,
    *,
    client: Any | None = None,
    api_key: str | None = None,
) -> SpecResult:
    resolved_client = _resolve_client(client=client, api_key=api_key)

    prompt = template.format(
        description=description,
        schema=SYSTEM_SPEC_SCHEMA,
        size_constraints=SPEC_SIZE_CONSTRAINTS[mode],
    )

    resp = resolved_client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2400,
        temperature=0.0,
        system=SYSTEM_SPEC_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = _extract_text(resp)

    if not raw.strip():
        raise EmptyModelOutput()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise InvalidModelJSON(raw_text=raw, error=str(e), kind="json_decode") from e

    try:
        spec = SystemSpec.model_validate(data)
    except ValidationError as e:
        raise InvalidModelJSON(raw_text=raw, error=str(e), kind="schema_validation") from e

    return SpecResult(spec=spec, raw=raw)


def extract_spec(
    text: str,
    mode: Mode = "short",
    *,
    client: Any | None = None,
    api_key: str | None = None,
) -> SpecResult:
    return _run_spec_prompt(
        text,
        EXTRACT_TEMPLATE,
        mode,
        client=client,
        api_key=api_key,
    )


def propose_spec(
    text: str,
    mode: Mode = "short",
    *,
    client: Any | None = None,
    api_key: str | None = None,
) -> SpecResult:
    return _run_spec_prompt(
        text,
        PROPOSE_TEMPLATE,
        mode,
        client=client,
        api_key=api_key,
    )
