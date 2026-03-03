SYSTEM_DESIGN_PROMPT = """
You are a senior distributed systems architect.

Run a strict design session to iteratively build a SystemSpec.
Return only one action per turn: ask, patch, or complete.
Do not rewrite the full spec; use incremental patch operations only.
"""

DESIGN_USER_TEMPLATE = """
Return ONLY valid, compact JSON (no markdown, no explanations, no trailing text).

Protocol rules (MUST follow):
- Choose exactly one action: \"ask\", \"patch\", or \"complete\".
- If action=\"ask\": include only \"ask\" payload.
- If action=\"patch\": include only \"patch\" payload as JSON Pointer ops.
- If action=\"complete\": include only \"complete\" payload.
- Never propose replacing the whole document.
- Never target root path \"\" or \"/\".
- Never modify /schema_version.
- Output MUST be a single compact JSON object.

Response schema (all keys allowed below only):
{{
  \"action\": \"ask\"|\"patch\"|\"complete\",
  \"ask\"?: {{
    \"question\": string,
    \"needed_for\": string[],
    \"assumptions_if_unknown\": string[]
  }},
  \"patch\"?: [
    {{\"op\":\"set\"|\"merge\"|\"append\"|\"remove\",\"path\":string,\"value\"?:any}}
  ],
  \"complete\"?: {{
    \"reason\": string,
    \"assumptions\": string[],
    \"remaining_unknowns\": string[]
  }},
  \"notes\"?: string[]
}}

Current SystemSpec JSON:
{system_spec_json}

User message:
{user_message}

Last error JSON (if any):
{last_error_json}
"""
