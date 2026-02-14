from pathlib import Path

import typer
from rich import print

from .analyzer import analyze_system
from .models import Mode

app = typer.Typer()


@app.command()
def analyze(file: Path, mode: Mode = typer.Option("short", "--mode")):
    if not file.exists():
        print("[red]File not found[/red]")
        raise typer.Exit()

    content = file.read_text()
    report = analyze_system(content, mode=mode)
    print("[bold]Architecture Summary[/bold]")
    print(report.architecture_summary)
    print("\n[bold]Top Concrete Fixes[/bold]")
    for i, fix in enumerate(report.concrete_fixes[:5], 1):
        print(f"{i}. {fix}")


if __name__ == "__main__":
    app()
