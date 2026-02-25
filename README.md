# syscopilot

Local CLI that reviews a system design description using Claude Opus and outputs a structured report.

## Dependencies
This project uses `requirements.txt` for dependency management. It includes:
- anthropic
- typer
- rich
- python-dotenv
- pydantic v2 (`pydantic>=2,<3`)

## Local setup
```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run the CLI
```bash
python -m syscopilot.cli --help
python -m syscopilot.cli analyze system.txt --mode short
python -m syscopilot.cli spec extract system.txt --mode short
python -m syscopilot.cli spec propose system.txt --mode full
```

## Environment configuration
Set your Anthropic key before running commands that call the model:

```bash
export ANTHROPIC_API_KEY="..."
```

Or create a `.env` file with:

```dotenv
ANTHROPIC_API_KEY=...
```

## CI and devcontainer
- GitHub Actions installs dependencies with `pip install -r requirements.txt` before checks.
- Devcontainer runs `pip install -r requirements.txt` in `postCreateCommand`.

This keeps CI, devcontainer, and local setup aligned.
