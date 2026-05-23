"""anvil plan — decompose a feature into phases and open GitHub issues."""

from __future__ import annotations

import asyncio
import subprocess
from datetime import date
from pathlib import Path

from rich.console import Console

from anvil.orchestrator.gemini import GeminiAuthError, GeminiResponseError
from anvil.orchestrator.sub_agents import run_plan_scribe

console = Console()


class PlanError(Exception):
    """Raised when plan setup (project root, gh availability) fails."""


def _find_project_root(start: Path) -> Path:
    current = start.resolve()
    while True:
        if (current / "pdd" / "context" / "project.md").is_file():
            return current
        if (current / ".git").is_dir():
            raise PlanError(
                f"No pdd/context/project.md found above {start} "
                f"(hit repo boundary at {current}). "
                "Run from inside an Anvil-managed project, or run `anvil init` first."
            )
        if current.parent == current:
            raise PlanError(
                f"No pdd/context/project.md found above {start}. "
                "Run from inside an Anvil-managed project, or run `anvil init` first."
            )
        current = current.parent


def _check_gh_available() -> None:
    try:
        version = subprocess.run(
            ["gh", "--version"],
            check=False,
            capture_output=True,
        )
    except FileNotFoundError as e:
        raise PlanError(
            "`gh` CLI not found on PATH. "
            "Install it with `brew install gh`, then run `gh auth login`."
        ) from e

    if version.returncode != 0:
        stderr = version.stderr.decode("utf-8", errors="replace").strip()
        raise PlanError(f"`gh --version` failed: {stderr or 'unknown error'}")

    auth = subprocess.run(
        ["gh", "auth", "status"],
        check=False,
        capture_output=True,
    )
    if auth.returncode != 0:
        stderr = auth.stderr.decode("utf-8", errors="replace").strip()
        stdout = auth.stdout.decode("utf-8", errors="replace").strip()
        detail = stderr or stdout or "unknown error"
        raise PlanError(
            "`gh` is installed but not authenticated. "
            f"Run `gh auth login` first.\n[dim]{detail}[/dim]"
        )


async def _plan_feature(
    feature: str,
    project_root: Path,
    project_md: str,
    today: str,
) -> None:
    with console.status(
        "[bold cyan]PlanScribe[/bold cyan] decomposing into phases…"
    ):
        output = await run_plan_scribe(
            project_md=project_md, description=feature, today=today
        )

    feature_dir = project_root / "pdd" / "prompts" / "features" / output.feature_area
    if feature_dir.exists() and next(feature_dir.glob("PLAN-*.md"), None) is not None:
        raise PlanError(
            f"Feature area '{output.feature_area}' already has a PLAN. "
            f"Use a different feature description or remove {feature_dir} and retry."
        )

    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / output.plan_filename).write_text(output.plan_md, encoding="utf-8")
    (feature_dir / output.phase_01_filename).write_text(
        output.phase_01_prompt_md, encoding="utf-8"
    )
    console.print(
        f"[green]✓[/green] PlanScribe → "
        f"[dim]{output.feature_area}/{output.plan_filename}[/dim] + phase-01 prompt"
    )


def execute(feature: str) -> None:
    try:
        project_root = _find_project_root(Path.cwd())
        _check_gh_available()
        project_md = (project_root / "pdd" / "context" / "project.md").read_text(
            encoding="utf-8"
        )
    except PlanError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1) from e

    console.print(
        f"[bold cyan]anvil plan[/bold cyan] — feature: [italic]{feature}[/italic]\n"
        f"[dim]project root: {project_root}[/dim]"
    )

    today = date.today().isoformat()
    try:
        asyncio.run(_plan_feature(feature, project_root, project_md, today))
    except PlanError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1) from e
    except GeminiAuthError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(2) from e
    except GeminiResponseError as e:
        console.print(f"[red]Flash returned malformed output:[/red] {e}")
        raise SystemExit(2) from e

    console.print(
        "\n[bold green]Done.[/bold green] Opened the PLAN. "
        "Next: [bold]anvil plan[/bold] phase 3 (gh issues) or hand-edit the PLAN."
    )
