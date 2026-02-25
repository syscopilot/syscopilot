SYSTEM_SPEC_PROMPT = """
You are a senior distributed systems architect producing SystemSpec v1 JSON.

Be explicit and concise.
"""

SYSTEM_SPEC_SCHEMA = """{
  \"schema_version\": \"syscopilot.systemspec.v1\",
  \"system\": {\"name\": string, \"domain\": string|null, \"goals\": string[], \"non_goals\": string[]},
  \"components\": [{\"id\": string, \"type\": string, \"name\": string, \"responsibilities\": string[], \"depends_on\": string[], \"runtime\": {\"kind\": string, \"platform\": string|null}|null, \"scaling\": {\"min\": number|null, \"max\": number|null, \"strategy\": string|null}|null}],
  \"links\": [{\"id\": string, \"from_id\": string, \"to_id\": string, \"transport\": {\"kind\": string, \"name\": string, \"format\": string|null}, \"semantics\": string[], \"delivery\": string|null, \"ordering\": string|null, \"key\": string|null, \"backpressure\": string|null}],
  \"data_stores\": [{\"id\": string, \"type\": string, \"ownership\": string, \"notes\": string[], \"retention\": string|null}],
  \"contracts\": [{\"id\": string, \"name\": string, \"owner_component_id\": string, \"schema\": object, \"evolution\": string|null}],
  \"deploy\": {\"orchestration\": string|null, \"regions\": string[], \"observability\": string[], \"notes\": string[]},
  \"requirements\": {\"slos\": string[], \"constraints\": string[], \"throughput_targets\": string[], \"latency_budgets\": string[]},
  \"open_questions\": string[],
  \"extensions\": object
}"""

SPEC_SIZE_CONSTRAINTS = {
    "short": """- Keep each list to max 3 items.
- Keep each item to one short sentence.
- Prefer omission over verbosity; use null for unknown optional fields.""",
    "full": """- Keep each list to max 8 items.
- Keep each item to one short sentence.
- Prefer concise, factual entries.""",
}

EXTRACT_TEMPLATE = """
Return ONLY valid, compact JSON (single object, no markdown, no newlines).

Target schema (all keys required):
{schema}

Task:
- Extract a SystemSpec from the implementation/system description below.
- MUST NOT invent unknown details.
- If an optional semantic detail is unknown, use the literal string \"unknown\" where appropriate.
- Add unknowns and ambiguities to open_questions.

Hard rules:
- Output must be valid JSON only.
- Output must be a single JSON object.
- Use compact JSON.
- schema_version must be \"syscopilot.systemspec.v1\".

Size constraints:
{size_constraints}

Input description:
{description}
"""

PROPOSE_TEMPLATE = """
Return ONLY valid, compact JSON (single object, no markdown, no newlines).

Target schema (all keys required):
{schema}

Task:
- Propose a SystemSpec from the goals/constraints description below.
- You may propose reasonable defaults when unspecified.
- List assumptions explicitly in extensions.assumptions.
- Add unresolved items to open_questions.

Hard rules:
- Output must be valid JSON only.
- Output must be a single JSON object.
- Use compact JSON.
- schema_version must be \"syscopilot.systemspec.v1\".

Size constraints:
{size_constraints}

Input description:
{description}
"""
