from pathlib import Path
from typing import cast

import typer
from rich import print

from .analyzer import analyze_system
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

    content = file.read_text()
    report = analyze_system(content, mode=cast(Mode, normalized_mode))
    print("[bold]Architecture Summary[/bold]")
    print(report.architecture_summary)
    print("\n[bold]Top Concrete Fixes[/bold]")
    for i, fix in enumerate(report.concrete_fixes[:5], 1):
        print(f"{i}. {fix}")


if __name__ == "__main__":
    app()
