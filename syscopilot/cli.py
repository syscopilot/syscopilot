import os
from collections import Counter
from pathlib import Path
from typing import cast

import typer
from dotenv import load_dotenv
from rich import print

from .analyzer import analyze_system
from .artifacts import save_json_error, save_run, save_spec_run
from .llm import InvalidModelJSON
from .models import Mode, SystemSpec
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


if __name__ == "__main__":
    app()
