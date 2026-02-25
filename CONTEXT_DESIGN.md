# Syscopilot – Design Context (Current)

## What this is
Syscopilot is a local CLI that reviews a system design description using Anthropic Claude Opus and returns structured, opinionated output focused on distributed-systems failure modes.

The tool is intentionally schema-first:
- model produces structured JSON,
- code validates JSON with Pydantic,
- short/full modes control cost and verbosity,
- CLI persists artifacts for reproducibility and diffing.

## Current state (V1)
- Language: Python
- Interface: CLI (Typer + Rich)
- LLM: Anthropic Opus via `anthropic` SDK
- Inputs:
  - `analyze`: implementation/system description file
  - `spec extract`: implementation/system description file
  - `spec propose`: goals/constraints description file
- Outputs:
  - Validated analysis report (`ShortReport` or `Report`)
  - Validated SystemSpec v1 (`SystemSpec`)
  - CLI digest and summary views
  - Artifacts under `runs/`

## Core review lenses (analysis)
1) Idempotency & duplicate handling
2) Separation of responsibilities
3) Backpressure & flow control
4) Ingestion vs processing boundaries
5) Failure modes & recovery

## Output schemas

### Analysis schemas
#### Short mode schema (default) — 6 keys
Pydantic model `ShortReport` keys:
- architecture_summary: str
- assumptions_detected: List[str]
- idempotency_risks: List[str]
- backpressure_analysis: List[str]
- failure_scenarios: List[str]
- concrete_fixes: List[str]

#### Full mode schema — 10 keys
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

### SystemSpec v1 schema
Pydantic model `SystemSpec` includes:
- `schema_version: Literal["syscopilot.systemspec.v1"]`
- `system`: name/domain/goals/non_goals
- `components[]`: id/type/name/responsibilities/depends_on/runtime/scaling
- `links[]`: id/from_id/to_id/transport/semantics/delivery/ordering/key/backpressure
- `data_stores[]`: id/type/ownership/notes/retention
- `contracts[]`: id/name/owner_component_id/schema/evolution
- `deploy`: orchestration/regions/observability/notes
- `requirements`: slos/constraints/throughput_targets/latency_budgets
- `open_questions[]`
- `extensions` (escape hatch dict)

Validation stays intentionally light:
- IDs are non-empty strings where defined.
- Enum-like values remain freeform strings.

## Prompting strategy
We force:
- JSON only (no markdown, no commentary)
- single JSON object output
- compact JSON (no pretty printing)
- short/full size caps on list content
- low temperature (0.0)

SystemSpec prompt modes:
- `extract`: must not invent unknown details; unknowns should become `open_questions`; optional semantic fields may use `"unknown"`.
- `propose`: may propose sensible defaults but must capture assumptions and open questions.

## Module boundaries (important)
### llm.py
Owns shared LLM utilities:
- `resolve_client(...)`
- `extract_text(...)`
- model output exceptions: `InvalidModelJSON`, `EmptyModelOutput`

### analyzer.py
Owns analysis-only orchestration:
- build analysis prompt
- call LLM
- parse JSON
- validate `ShortReport`/`Report`
- return `AnalysisResult(report, raw)`

### spec_analyzer.py
Owns spec-only orchestration:
- build extract/propose spec prompt
- call LLM
- parse JSON
- validate `SystemSpec`
- return `SpecResult(spec, raw)`

### artifacts.py
Owns persistence:
- create `runs/`
- atomic writes
- deterministic JSON serialization
- canonicalized SystemSpec persistence

### cli.py
Owns orchestration/UX only:
- command routing and options validation
- env loading and API key lookup
- analyzer/spec_analyzer invocation
- artifact persistence via `artifacts.py`
- user-facing summaries and warnings

### models.py / prompts.py / spec_prompts.py
- `models.py`: Pydantic schemas + mode types.
- `prompts.py`: analysis prompt templates.
- `spec_prompts.py`: SystemSpec extract/propose templates.

## Model-output failure taxonomy
Analyzer layers raise `InvalidModelJSON` with `kind`:
- `empty_output`: no text content extracted
- `json_decode`: text not valid JSON
- `schema_validation`: JSON parsed but schema mismatch

CLI behavior:
- maps `kind` to a friendly message
- saves `runs/json_error_<ts>.txt`
- exits code 1

## Artifacts (run logging)
Each command writes artifacts under `runs/`.

Analysis success:
- `runs/raw_<ts>.txt`
- `runs/report_<ts>.json`

SystemSpec success:
- `runs/spec_raw_<ts>.txt`
- `runs/spec_<ts>.json`

Failure (model output issues):
- `runs/json_error_<ts>.txt` (kind + error + raw output)

Notes:
- JSON artifacts use compact formatting and sorted keys.
- SystemSpec artifacts are canonicalized; lists of objects with `id` are sorted by `id`.
- Filenames are collision-resistant (timestamp + pid + random suffix).

## CLI behavior and usage
### Help UX
- Running the CLI with no subcommand prints help and exits code 0.

### Analyze command
- `python -m syscopilot.cli analyze system.md`
- `python -m syscopilot.cli analyze system.md --mode short`
- `python -m syscopilot.cli analyze system.md --mode full`

### SystemSpec commands
- `python -m syscopilot.cli spec extract system.md --mode short`
- `python -m syscopilot.cli spec extract system.md --mode full`
- `python -m syscopilot.cli spec propose goals.md --mode short`
- `python -m syscopilot.cli spec propose goals.md --mode full`

`--mode`:
- accepts `short` or `full` (case-insensitive)
- invalid values exit with code 2

Spec commands print:
- counts by `component.type`
- counts by `link.transport.kind`
- top open questions
- non-fatal semantic warnings (e.g., duplicate ids, dangling references)

## Repo structure (expected)
- syscopilot/
  - cli.py              # Typer app + commands (orchestration + UX)
  - llm.py              # shared LLM client/response utilities + output exceptions
  - analyzer.py         # analysis orchestration (prompt/call/parse/validate)
  - spec_analyzer.py    # SystemSpec orchestration (extract/propose)
  - artifacts.py        # persistence + atomic writes + deterministic JSON formatting
  - models.py           # Pydantic schemas + mode types
  - prompts.py          # analysis templates + constraints
  - spec_prompts.py     # SystemSpec templates + constraints
  - spec_validation.py  # semantic warnings for SystemSpec references/ids
- runs/ (not committed): raw outputs + json errors + reports/specs
- .env (not committed): `ANTHROPIC_API_KEY`

## Non-goals (for now)
- Web UI
- Auth/accounts/payments
- Tool-calling agents
- Repo scanning / code parsing

## Known risks / gotchas
- LLM truncation can produce invalid JSON.
- Prompt/schema drift must be avoided.
- Never commit `.env` or API keys.
- Artifacts are intended to be collision-proof and append-only.
