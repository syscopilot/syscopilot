from typing import Any

from anthropic import Anthropic


class InvalidModelJSON(ValueError):
    def __init__(self, raw_text: str, error: str, kind: str):
        super().__init__(f"Model output failure ({kind}): {error}")
        self.raw_text = raw_text
        self.error = error
        self.kind = kind


class EmptyModelOutput(InvalidModelJSON):
    def __init__(self):
        super().__init__(
            raw_text="",
            error="No text content found in model response",
            kind="empty_output",
        )


def resolve_client(client: Any | None = None, api_key: str | None = None) -> Any:
    if client is not None:
        return client
    if not api_key:
        raise RuntimeError("api_key is required when client is not provided")
    return Anthropic(api_key=api_key)


def extract_text(resp) -> str:
    parts = []
    for block in resp.content:
        if hasattr(block, "text") and block.text:
            parts.append(block.text)
    raw_text = "".join(parts)
    if not raw_text.strip():
        raise EmptyModelOutput()
    return raw_text.strip()
