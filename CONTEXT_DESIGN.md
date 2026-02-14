# Syscopilot – Design Context (Handoff)

## What this is
Syscopilot is a local CLI that reviews a system design description using Anthropic Claude Opus and returns a structured, opinionated critique focused on distributed-systems failure modes.

The goal is **not** “LLM text output”, but a deterministic tool where:
- the model produces structured JSON,
- our code validates it,
- we apply our own scoring/logic,
- we support cost-controlled modes (short/full),
- we save outputs for reproducibility.

## Current state (V0)
- Language: Python
- Interface: CLI (Typer + Rich)
- LLM: Anthropic Opus via `anthropic` SDK
- Input: a `.txt/.md` system description
- Output: JSON parsed into a Pydantic model (`Report`)
- We print a digest (Architecture Summary + top fixes) and can save full JSON.

## Core review lenses (must stay)
1) Idempotency & duplicate handling
2) Separation of responsibilities
3) Backpressure & flow control
4) Ingestion vs processing boundaries
5) Failure modes & recovery

## Output schema (current)
Pydantic model `Report` keys:
- architecture_summary: str
- assumptions_detected: List[str]
- idempotency_risks: List[str]
- responsibility_coupling: List[str]
- backpressure_analysis: List[str]
- ingestion_vs_processing: List[str]
- failure_scenarios: List[str]
- concrete_fixes: List[str]
- suggested_metrics: List[str]
- failure_injection_tests: List[str]

## Prompting strategy (cost controlled)
We force:
- JSON only (no markdown)
- compact output (no pretty printing, no extra text)
- hard caps on list sizes and item length
- low temperature (0.0) to reduce verbosity drift
- keep max_tokens low (initially ~2000) and reduce output via constraints instead of increasing max_tokens

Important bug discovered:
- JSON parse errors often came from **truncation** (output cut mid-string), not formatting.
- We prefer prompt caps + “short mode” over retry loops to control cost.

## CLI usage
Example:
- `python -m syscopilot.cli analyze system.txt`
(or whatever the current Typer command configuration is)

## Repo structure (expected)
- syscopilot/
  - cli.py
  - analyzer.py
  - prompts.py
  - models.py
- runs/ (not committed): raw outputs + json errors + reports
- .env (not committed): ANTHROPIC_API_KEY

## Non-goals (for now)
- Web UI
- Auth/accounts/payments
- Tool-calling agents
- Repo scanning / code parsing (future)

## Next 3 concrete tasks (priority order)
1) Add `--mode short|full`
   - short schema: 6 keys:
     - architecture_summary, assumptions_detected, idempotency_risks,
       backpressure_analysis, failure_scenarios, concrete_fixes
   - full schema: current 10 keys
   - default: short (cheaper, less truncation risk)

2) Save artifacts deterministically
   - save model raw output to `runs/raw_<ts>.txt`
   - save parsed report JSON to `runs/report_<ts>.json`
   - on failure, save `runs/json_error_<ts>.txt`

3) Add deterministic scoring (no extra API calls)
   - compute a risk score per lens (0–10) from the validated JSON
   - print “Top Risks” + “3-step action plan”
   - this makes the tool feel like an engine, not a wrapper

## Known risks / gotchas
- Opus output truncation -> invalid JSON; manage by shrinking output.
- Keep prompt + schema aligned (keys must match exactly).
- Never commit `.env` or API keys.
