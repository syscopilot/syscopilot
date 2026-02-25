import json
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from .design_prompts import DESIGN_USER_TEMPLATE, SYSTEM_DESIGN_PROMPT
from .llm import EmptyModelOutput, InvalidModelJSON, extract_text, resolve_client
from .models import DesignSessionError, DesignSessionResponse, SystemSpec


@dataclass(frozen=True)
class DesignStepResult:
    response: DesignSessionResponse
    raw: str


def design_step(
    system_spec: SystemSpec,
    user_message: str,
    last_error: DesignSessionError | None,
    *,
    client: Any | None = None,
    api_key: str | None = None,
) -> DesignStepResult:
    resolved_client = resolve_client(client=client, api_key=api_key)

    prompt = DESIGN_USER_TEMPLATE.format(
        system_spec_json=json.dumps(system_spec.model_dump(), separators=(",", ":"), sort_keys=True, ensure_ascii=False),
        user_message=user_message,
        last_error_json=(
            json.dumps(last_error.model_dump(), separators=(",", ":"), sort_keys=True, ensure_ascii=False)
            if last_error
            else "null"
        ),
    )

    resp = resolved_client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2400,
        temperature=0.0,
        system=SYSTEM_DESIGN_PROMPT,
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
        response = DesignSessionResponse.model_validate(data)
    except ValidationError as e:
        raise InvalidModelJSON(raw_text=raw, error=str(e), kind="schema_validation") from e

    return DesignStepResult(response=response, raw=raw)
