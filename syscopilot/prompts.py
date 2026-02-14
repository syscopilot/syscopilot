SYSTEM_PROMPT = """
You are a senior distributed systems architect.

You review system designs using these lenses:
1) Idempotency and duplicate handling
2) Separation of responsibilities
3) Backpressure and flow control
4) Ingestion vs processing boundaries
5) Failure modes and recovery

Be concrete. Avoid vague advice.
"""

USER_TEMPLATE = """\
Return ONLY valid, compact JSON (no markdown, no explanations, no trailing text).

Required schema (all keys required):
{{
  "architecture_summary": string,
  "assumptions_detected": string[],
  "idempotency_risks": string[],
  "responsibility_coupling": string[],
  "backpressure_analysis": string[],
  "ingestion_vs_processing": string[],
  "failure_scenarios": string[],
  "concrete_fixes": string[],
  "suggested_metrics": string[],
  "failure_injection_tests": string[]
}}

Hard rules (MUST follow):
- Output MUST be valid JSON only (no code fences, no markdown, no commentary).
- Output MUST be a single JSON object starting with '{{' and ending with '}}'.
- Use COMPACT JSON: no pretty-printing, no extra whitespace, no newlines.
- Do NOT include newline characters inside any JSON string.
- Do NOT use quotes inside strings unless escaped.

Size constraints (MUST follow):
- arrays: max 4 items each
- each item: ONE sentence, max 120 characters
- suggested_metrics: max 6 items
- failure_injection_tests: max 2 items
- Avoid repetition across sections.

Quality constraints:
- Be concrete: name boundaries (e.g., "WebSocket handler", "DB write", "alert webhook").
- If something is unknown, add it to assumptions_detected (do not invent facts).

System description:
{description}
"""
