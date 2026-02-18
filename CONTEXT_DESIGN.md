# Syscopilot – Design Context (Current)

## What this is
Syscopilot is a local CLI that reviews a system design description using Anthropic Claude Opus and returns a structured, opinionated critique focused on distributed-systems failure modes.

The goal is **not** “LLM text output”, but a tool where:
- the model produces structured JSON,
- our code validates it (Pydantic),
- we support cost-controlled modes (short/full),
- we save artifacts for reproducibility,
- output JSON is compact + stable for diffing.

## Current state (V0)
- Language: Python
- Interface: CLI (Typer + Rich)
- LLM: Anthropic Opus via `anthropic` SDK
- Input: a `.txt/.md` system description file
- Output:
  - Validated Pydantic model:
    - `ShortReport` (6 keys) OR `Report` (10 keys)
  - CLI prints a digest (Architecture Summary + Top Concrete Fixes)
  - Artifacts saved under `runs/` per execution

## Core review lenses (must stay)
1) Idempotency & duplicate handling
2) Separation of responsibilities
3) Backpressure & flow control
4) Ingestion vs processing boundaries
5) Failure modes & recovery

## Output schemas

### Short mode schema (default) — 6 keys
Pydantic model `ShortReport` keys:
- architecture_summary: str
- assumptions_detected: List[str]
- idempotency_risks: List[str]
- backpressure_analysis: List[str]
- failure_scenarios: List[str]
- concrete_fixes: List[str]

### Full mode schema — 10 keys
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

Notes:
- Code uses `ReportLike = Union[ShortReport, Report]`.
- Default mode is **short** to reduce truncation risk + cost.

## Prompting strategy (cost controlled + JSON safety)
We force:
- JSON only (no markdown, no commentary)
- compact output (no pretty printing, no extra whitespace/newlines)
- strict caps on list sizes and item length
- low temperature (0.0)
- constraints + short mode as the primary mechanism to prevent truncation

Important lessons:
- JSON parse errors often come from **truncation** (cut mid-string), not formatting.
- Prefer shrinking output over retries to control cost.
- If size constraints are too tight, the model should output the **shortest valid JSON** that satisfies the schema.

## Module boundaries (important)
### analyzer.py
Owns:
- Constructing the user prompt (from templates + schema for the chosen mode)
- Calling Anthropic (or using an injected client)
- Extracting text from the model response
- Parsing JSON
- Validating with Pydantic
- Returning `AnalysisResult(report, raw)`

Does NOT own:
- filesystem I/O / persistence

### artifacts.py
Owns:
- Creating the `runs/` directory
- Writing artifacts atomically
- JSON serialization of validated report in compact, sorted-key form

### cli.py
Owns:
- CLI UX (help behavior, args/options validation)
- Loading API key from environment
- Orchestrating analyzer + artifacts
- Printing a digest to the console
- Mapping model-output failures to friendly messages and exit codes

### models.py / prompts.py
- `models.py`: Pydantic schemas + `Mode` type.
- `prompts.py`: system prompt, user template, and schema/size-constraint strings.

## Model-output failure taxonomy
Analyzer raises `InvalidModelJSON` (or subclasses) on model output failures, with a `kind`:
- `empty_output`: no text content extracted from model response
- `json_decode`: text was present but not valid JSON
- `schema_validation`: JSON parsed but did not match the required schema

CLI:
- Prints a friendly message for the failure kind
- Saves an error artifact `runs/json_error_<ts>.txt`
- Exits with code 1

## Artifacts (run logging)
Each analysis writes to `runs/` (directory created if missing):

Success:
- `runs/raw_<ts>.txt` — raw model output
- `runs/report_<ts>.json` — validated report JSON (compact + sorted keys)

Failure (model output issues):
- `runs/json_error_<ts>.txt` — contains:
  - failure kind
  - error message
  - raw output

Notes:
- JSON output is deterministic in formatting (compact + sorted keys) for diffing.
- Filenames are collision-resistant (timestamp + pid + random suffix), not reproducible across runs.

## CLI behavior and usage

### Help UX
- Running the CLI with **no subcommand** prints help and exits cleanly (code 0).

### Analyze command
Examples:
- `python -m syscopilot.cli analyze system.md`
- `python -m syscopilot.cli analyze system.md --mode short`
- `python -m syscopilot.cli analyze system.md --mode full`

`--mode`:
- accepts `short` or `full` (case-insensitive)
- default: `short`
- invalid values fail fast with a friendly error and exit code 2

## Repo structure (expected)
- syscopilot/
  - cli.py        # Typer app + commands (orchestration + UX)
  - analyzer.py   # Anthropic call + parsing + Pydantic validation
  - artifacts.py  # persistence + atomic writes + deterministic JSON formatting
  - prompts.py    # system/user templates + mode-specific constraints
  - models.py     # Pydantic schemas + mode types
- runs/ (not committed): raw outputs + json errors + reports
- .env (not committed): ANTHROPIC_API_KEY

## Non-goals (for now)
- Web UI
- Auth/accounts/payments
- Tool-calling agents
- Repo scanning / code parsing (future)

## Next tasks (new priority order)
1) Deterministic scoring (no extra API calls)
   - compute a risk score per lens (0–10) from the validated JSON
   - print “Top Risks” + “3-step action plan”
   - keep it reproducible (pure function over validated output)

2) Add lightweight smoke tests
   - schema validation tests for short/full
   - artifact creation tests (paths + filename pattern)
   - CLI help/no-subcommand behavior

3) Prompt hardening for JSON-only correctness
   - keep schemas aligned with Pydantic models
   - enforce caps (max items, max length)
   - optionally define an explicit “empty-but-valid JSON” policy and treat as failure

## Known risks / gotchas
- Opus output truncation -> invalid JSON; manage by shrinking output.
- Keep prompt + schema aligned (keys must match exactly).
- Never commit `.env` or API keys.
- Artifacts should not overwrite: keep collision-proof filenames.
