"""anvil plan — decompose a feature into phases and open GitHub issues."""

from __future__ import annotations

import subprocess
from pathlib import Path

from rich.console import Console

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

    _ = project_md

    console.print(
        f"[bold cyan]anvil plan[/bold cyan] — feature: [italic]{feature}[/italic]\n"
        f"[dim]project root: {project_root}[/dim]"
    )
    console.print("[dim]Phase 2 wires PlanScribe — coming next.[/dim]")
