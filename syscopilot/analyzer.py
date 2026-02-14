import os
import json
from datetime import datetime
from dotenv import load_dotenv
from anthropic import Anthropic
from .prompts import SYSTEM_PROMPT, USER_TEMPLATE
from .models import Report

load_dotenv()

def _extract_text(resp) -> str:
    parts = []
    for block in resp.content:
        if hasattr(block, "text") and block.text:
            parts.append(block.text)
    return "\n".join(parts).strip()

def analyze_system(description: str) -> Report:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not found in .env")

    client = Anthropic(api_key=api_key)

    prompt = USER_TEMPLATE.format(description=description)

    resp = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2000,
        temperature=0.0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = _extract_text(resp)

    # Always dump raw output for inspection
    os.makedirs("runs", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = os.path.join("runs", f"raw_{ts}.txt")
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(raw)

    # Now try parse once (no retries)
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

    report = Report.model_validate(data)
    return report
