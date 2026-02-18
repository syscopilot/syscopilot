import os
from pathlib import Path
from typing import cast

import typer
from dotenv import load_dotenv
from rich import print

from .analyzer import InvalidModelJSON, analyze_system
from .artifacts import save_json_error, save_run
from .models import Mode

app = typer.Typer()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Syscopilot CLI entrypoint."""
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())
        raise typer.Exit(code=0)


@app.command()
def analyze(
    file: Path,
    mode: str = typer.Option(
        "short",
        "--mode",
        help="Analysis mode: short or full (case-insensitive).",
    ),
):
    normalized_mode = mode.lower()
    if normalized_mode not in {"short", "full"}:
        print("[red]Invalid mode. Use 'short' or 'full'.[/red]")
        raise typer.Exit(code=2)

    if not file.exists():
        print("[red]File not found[/red]")
        raise typer.Exit()

    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[red]ANTHROPIC_API_KEY not found in environment.[/red]")
        raise typer.Exit(code=1)

    content = file.read_text(encoding="utf-8")

    try:
        result = analyze_system(content, mode=cast(Mode, normalized_mode), api_key=api_key)
    except InvalidModelJSON as exc:
        failure_messages = {
            "json_decode": "Model returned invalid JSON",
            "schema_validation": "Model returned JSON that didn't match schema",
            "empty_output": "Model returned empty output",
        }
        message = failure_messages.get(exc.kind, "Model output validation failed")
        error_path = save_json_error(exc.raw_text, exc.error, exc.kind, runs_dir="runs")
        print(f"[red]{message}.[/red] Saved error artifact to [bold]{error_path}[/bold].")
        raise typer.Exit(code=1)

    save_run(result.raw, result.report, runs_dir="runs")

    report = result.report
    print("[bold]Architecture Summary[/bold]")
    print(report.architecture_summary)
    print("\n[bold]Top Concrete Fixes[/bold]")
    for i, fix in enumerate(report.concrete_fixes[:5], 1):
        print(f"{i}. {fix}")


if __name__ == "__main__":
    app()
