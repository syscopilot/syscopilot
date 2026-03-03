import os
from collections import Counter
from pathlib import Path
from typing import Any, cast

import typer
from dotenv import load_dotenv
from rich import print

from .analyzer import analyze_system
from .artifacts import make_timestamp, save_design_turn, save_json_error, save_run, save_spec_run
from .design_session import design_step
from .llm import InvalidModelJSON
from .models import (
    Deploy,
    DesignSessionError,
    PatchOp,
    Mode,
    Requirements,
    SystemInfo,
    SystemSpec,
)
from .spec_analyzer import extract_spec, propose_spec
from .spec_validation import validate_spec_semantics

app = typer.Typer()
spec_app = typer.Typer(help="SystemSpec generation commands.")
app.add_typer(spec_app, name="spec")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Syscopilot CLI entrypoint."""
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())
        raise typer.Exit(code=0)


def _resolve_mode(mode: str) -> Mode:
    normalized_mode = mode.lower()
    if normalized_mode not in {"short", "full"}:
        print("[red]Invalid mode. Use 'short' or 'full'.[/red]")
        raise typer.Exit(code=2)
    return cast(Mode, normalized_mode)


def _read_api_key() -> str:
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[red]ANTHROPIC_API_KEY not found in environment.[/red]")
        raise typer.Exit(code=1)
    return api_key


def _read_file(file: Path) -> str:
    if not file.exists():
        print("[red]File not found[/red]")
        raise typer.Exit(code=1)
    return file.read_text(encoding="utf-8")


def _handle_invalid_json(exc: InvalidModelJSON) -> None:
    failure_messages = {
        "json_decode": "Model returned invalid JSON",
        "schema_validation": "Model returned JSON that didn't match schema",
        "empty_output": "Model returned empty output",
    }
    message = failure_messages.get(exc.kind, "Model output validation failed")
    error_path = save_json_error(exc.raw_text, exc.error, exc.kind, runs_dir="runs")
    print(f"[red]{message}.[/red] Saved error artifact to [bold]{error_path}[/bold].")
    raise typer.Exit(code=1)


def _print_spec_summary(spec: SystemSpec) -> None:
    component_counts = Counter(component.type for component in spec.components)
    link_counts = Counter(link.transport.kind for link in spec.links)

    print("[bold]SystemSpec Summary[/bold]")
    print(f"components: {len(spec.components)} | links: {len(spec.links)}")

    print("\n[bold]Components by type[/bold]")
    if component_counts:
        for component_type, count in component_counts.most_common():
            print(f"- {component_type}: {count}")
    else:
        print("- none")

    print("\n[bold]Links by transport kind[/bold]")
    if link_counts:
        for transport_kind, count in link_counts.most_common():
            print(f"- {transport_kind}: {count}")
    else:
        print("- none")

    print("\n[bold]Top open questions[/bold]")
    if spec.open_questions:
        for index, question in enumerate(spec.open_questions[:5], 1):
            print(f"{index}. {question}")
    else:
        print("none")


def _print_spec_warnings(spec: SystemSpec) -> None:
    warnings = validate_spec_semantics(spec)
    if not warnings:
        return
    print("\n[yellow][bold]Semantic warnings[/bold][/yellow]")
    for warning in warnings:
        print(f"[yellow]- {warning}[/yellow]")


def _initial_system_spec() -> SystemSpec:
    return SystemSpec(
        schema_version="syscopilot.systemspec.v1",
        system=SystemInfo(name="TBD", domain=None, goals=[], non_goals=[]),
        components=[],
        links=[],
        data_stores=[],
        contracts=[],
        deploy=Deploy(orchestration=None, regions=[], observability=[], notes=[]),
        requirements=Requirements(slos=[], constraints=[], throughput_targets=[], latency_budgets=[]),
        open_questions=[],
        extensions={},
    )


def _decode_pointer_segment(segment: str) -> str:
    return segment.replace("~1", "/").replace("~0", "~")


def _pointer_tokens(path: str) -> list[str]:
    if path in {"", "/"}:
        raise ValueError("root path overwrite is not allowed")
    if not path.startswith("/"):
        raise ValueError(f"invalid JSON pointer '{path}'")
    return [_decode_pointer_segment(token) for token in path.split("/")[1:]]


def _as_index(token: str, size: int) -> int:
    if token == "-":
        return size
    try:
        idx = int(token)
    except ValueError as exc:
        raise ValueError(f"list index must be integer, got '{token}'") from exc
    if idx < 0 or idx > size:
        raise ValueError(f"list index out of range: {idx}")
    return idx


def _navigate_parent(doc: Any, tokens: list[str]) -> tuple[Any, str]:
    current = doc
    for token in tokens[:-1]:
        if isinstance(current, dict):
            if token not in current:
                raise ValueError(f"path not found: missing key '{token}'")
            current = current[token]
        elif isinstance(current, list):
            idx = _as_index(token, len(current) - 1)
            if idx >= len(current):
                raise ValueError(f"path not found: list index '{token}'")
            current = current[idx]
        else:
            raise ValueError("cannot traverse into scalar value")
    return current, tokens[-1]


def apply_patch_ops(spec: SystemSpec, ops: list[PatchOp]) -> SystemSpec:
    payload = spec.model_dump()
    for op in ops:
        if op.path in {"", "/"}:
            raise ValueError("root path overwrite is not allowed")
        if op.path == "/schema_version" or op.path.startswith("/schema_version/"):
            raise ValueError("schema_version cannot be modified")

        tokens = _pointer_tokens(op.path)
        parent, last = _navigate_parent(payload, tokens)

        if op.op == "set":
            if isinstance(parent, dict):
                parent[last] = op.value
            elif isinstance(parent, list):
                idx = _as_index(last, len(parent))
                if idx == len(parent):
                    parent.append(op.value)
                else:
                    parent[idx] = op.value
            else:
                raise ValueError("set target parent must be object or array")
        elif op.op == "merge":
            if not isinstance(op.value, dict):
                raise ValueError("merge op requires object value")
            if isinstance(parent, dict):
                target = parent.get(last)
                if not isinstance(target, dict):
                    raise ValueError("merge target must be an object")
                target.update(op.value)
            elif isinstance(parent, list):
                idx = _as_index(last, len(parent) - 1)
                if idx >= len(parent) or not isinstance(parent[idx], dict):
                    raise ValueError("merge target must be an object")
                parent[idx].update(op.value)
            else:
                raise ValueError("merge target parent must be object or array")
        elif op.op == "append":
            if isinstance(parent, dict):
                target = parent.get(last)
                if not isinstance(target, list):
                    raise ValueError("append target must be an array")
                target.append(op.value)
            elif isinstance(parent, list):
                idx = _as_index(last, len(parent) - 1)
                if idx >= len(parent) or not isinstance(parent[idx], list):
                    raise ValueError("append target must be an array")
                parent[idx].append(op.value)
            else:
                raise ValueError("append target parent must be object or array")
        elif op.op == "remove":
            if isinstance(parent, dict):
                if last not in parent:
                    raise ValueError(f"remove target key does not exist: '{last}'")
                del parent[last]
            elif isinstance(parent, list):
                idx = _as_index(last, len(parent) - 1)
                if idx >= len(parent):
                    raise ValueError(f"remove index out of range: {idx}")
                parent.pop(idx)
            else:
                raise ValueError("remove target parent must be object or array")

    try:
        return SystemSpec.model_validate(payload)
    except Exception as exc:
        raise ValueError(f"patched spec failed validation: {exc}") from exc


def _completion_missing_items(spec: SystemSpec) -> list[str]:
    missing: list[str] = []
    if not spec.system.name.strip() or spec.system.name == "TBD":
        missing.append("system.name")
    if len(spec.system.goals) < 1:
        missing.append("system.goals")
    if len(spec.components) < 1:
        missing.append("components")
    if len(spec.links) < 1:
        missing.append("links")
    if len(spec.data_stores) < 1:
        missing.append("data_stores")
    if len(spec.requirements.slos) < 1:
        missing.append("requirements.slos")
    return missing


@app.command()
def analyze(
    file: Path,
    mode: str = typer.Option(
        "short",
        "--mode",
        help="Analysis mode: short or full (case-insensitive).",
    ),
):
    resolved_mode = _resolve_mode(mode)
    content = _read_file(file)
    api_key = _read_api_key()

    try:
        result = analyze_system(content, mode=resolved_mode, api_key=api_key)
    except InvalidModelJSON as exc:
        _handle_invalid_json(exc)

    save_run(result.raw, result.report, runs_dir="runs")

    report = result.report
    print("[bold]Architecture Summary[/bold]")
    print(report.architecture_summary)
    print("\n[bold]Top Concrete Fixes[/bold]")
    for i, fix in enumerate(report.concrete_fixes[:5], 1):
        print(f"{i}. {fix}")


@spec_app.command("extract")
def spec_extract(
    file: Path,
    mode: str = typer.Option(
        "short",
        "--mode",
        help="Spec mode: short or full (case-insensitive).",
    ),
):
    resolved_mode = _resolve_mode(mode)
    content = _read_file(file)
    api_key = _read_api_key()

    try:
        result = extract_spec(content, mode=resolved_mode, api_key=api_key)
    except InvalidModelJSON as exc:
        _handle_invalid_json(exc)

    paths = save_spec_run(result.raw, result.spec, runs_dir="runs")
    print(f"Saved spec to [bold]{paths['spec_path']}[/bold]")
    print(f"Saved raw model output to [bold]{paths['raw_path']}[/bold]")
    _print_spec_summary(result.spec)
    _print_spec_warnings(result.spec)


@spec_app.command("propose")
def spec_propose(
    file: Path,
    mode: str = typer.Option(
        "short",
        "--mode",
        help="Spec mode: short or full (case-insensitive).",
    ),
):
    resolved_mode = _resolve_mode(mode)
    content = _read_file(file)
    api_key = _read_api_key()

    try:
        result = propose_spec(content, mode=resolved_mode, api_key=api_key)
    except InvalidModelJSON as exc:
        _handle_invalid_json(exc)

    paths = save_spec_run(result.raw, result.spec, runs_dir="runs")
    print(f"Saved spec to [bold]{paths['spec_path']}[/bold]")
    print(f"Saved raw model output to [bold]{paths['raw_path']}[/bold]")
    _print_spec_summary(result.spec)
    _print_spec_warnings(result.spec)


@app.command()
def design():
    api_key = _read_api_key()
    run_dir = Path("runs") / make_timestamp()
    current_spec = _initial_system_spec()
    last_error: DesignSessionError | None = None
    turn_idx = 1

    print("[bold]Starting design session. Type 'exit' to quit.[/bold]")

    while True:
        user_message = input("design> ").strip()
        if user_message.lower() in {"exit", "quit"}:
            print("Exiting design session.")
            break
        if not user_message:
            continue

        try:
            result = design_step(current_spec, user_message, last_error, api_key=api_key)
        except InvalidModelJSON as exc:
            save_json_error(exc.raw_text, exc.error, exc.kind, runs_dir=str(run_dir / "design"))
            last_error = DesignSessionError(
                code="MODEL_JSON_ERROR",
                message="Model returned invalid JSON",
                details={"kind": exc.kind, "error": exc.error},
            )
            continue

        response = result.response
        response_dict = response.model_dump(exclude_none=True)

        if response.action == "ask":
            print(response.ask.question)
            last_error = None
        elif response.action == "patch":
            try:
                current_spec = apply_patch_ops(current_spec, response.patch)
                print("Applied patch operations.")
                last_error = None
            except Exception as exc:
                print(f"[yellow]Patch rejected:[/yellow] {exc}")
                last_error = DesignSessionError(
                    code="PATCH_APPLY_ERROR",
                    message="Failed to apply patch operations",
                    details={"error": str(exc), "ops": [op.model_dump() for op in response.patch]},
                )
        else:
            missing = _completion_missing_items(current_spec)
            if missing:
                print("[yellow]Completion rejected: missing required fields.[/yellow]")
                last_error = DesignSessionError(
                    code="INCOMPLETE_SPEC",
                    message="Completion checklist failed",
                    details={"missing": missing},
                )
            else:
                print("Design session complete.")
                last_error = None
                save_design_turn(
                    str(run_dir),
                    turn_idx,
                    user_message,
                    response_dict,
                    current_spec.model_dump(),
                    None,
                )
                break

        save_design_turn(
            str(run_dir),
            turn_idx,
            user_message,
            response_dict,
            current_spec.model_dump(),
            last_error.model_dump() if last_error else None,
        )
        turn_idx += 1


if __name__ == "__main__":
    app()
