"""Anvil CLI entry point.

Wires Typer subcommands to thin command modules under `anvil.commands`.
Each command module exposes an `execute()` function; the orchestrator
lives under `anvil.orchestrator` and is shared across commands.
"""

from __future__ import annotations

from pathlib import Path

import typer

from anvil import __version__
from anvil.commands import edit, init, plan, run, serve, status

app = typer.Typer(
    name="anvil",
    help="Anvil — a Git-native, eval-driven IDE for agent graphs.",
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"anvil {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show the Anvil version and exit.",
    ),
) -> None:
    """Root callback — accepts global flags before any subcommand."""


@app.command("init")
def init_cmd(
    description: str = typer.Argument(
        ...,
        help="One-sentence description of the agent you want to build.",
    ),
    existing: bool = typer.Option(
        False,
        "--existing",
        help="Retrofit PDD into an existing LangGraph project (brownfield).",
    ),
    out: Path | None = typer.Option(
        None,
        "--out",
        "-o",
        help="Parent directory for the new project. Defaults to cwd.",
    ),
) -> None:
    """Scaffold a new agent project, or bring PDD discipline to an existing one."""
    init.execute(description=description, existing=existing, out=out)


@app.command("plan")
def plan_cmd(
    feature: str = typer.Argument(..., help="Feature description in plain English."),
) -> None:
    """Plan a new feature — produce PLAN.md and open GitHub issues per phase."""
    plan.execute(feature=feature)


@app.command("run")
def run_cmd(
    phase: int | None = typer.Option(
        None,
        "--phase",
        help="Run a specific phase number. Omit with --all to run every pending phase.",
    ),
    all_phases: bool = typer.Option(
        False,
        "--all",
        help="Run every pending phase in order.",
    ),
) -> None:
    """Execute one or more phase prompts via the four sub-agents."""
    run.execute(phase=phase, all_phases=all_phases)


@app.command("edit")
def edit_cmd(
    change: str = typer.Argument(..., help="Plain-English description of the change."),
) -> None:
    """Conversationally extend an existing Anvil project. Tier 3."""
    edit.execute(change=change)


@app.command("serve")
def serve_cmd(
    port: int = typer.Option(8000, "--port", "-p", help="HTTP port to listen on."),
    web: bool = typer.Option(
        False,
        "--web",
        help="Also serve a chat UI with live graph visualization.",
    ),
) -> None:
    """Host the project's LangGraph as a FastAPI service via LangServe."""
    serve.execute(port=port, web=web)


@app.command("status")
def status_cmd() -> None:
    """Show phase progress, eval scores, and prompt versions for the current project."""
    status.execute()


if __name__ == "__main__":
    app()
