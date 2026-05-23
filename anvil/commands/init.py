"""anvil init — scaffold a new project (greenfield) or retrofit PDD (brownfield).

Greenfield: ProjectScribe names the project and writes project.md,
then ConventionsScribe ∥ PlanScribe fan out to fill the rest of pdd/.
Brownfield (--existing) is a post-hackathon item.
"""

from __future__ import annotations

import asyncio
import subprocess
from datetime import date
from pathlib import Path

from rich.console import Console

from anvil.orchestrator.gemini import GeminiAuthError, GeminiResponseError
from anvil.orchestrator.sub_agents import (
    run_conventions_scribe,
    run_plan_scribe,
    run_project_scribe,
)

console = Console()


def execute(description: str, existing: bool, out: Path | None) -> None:
    if existing:
        console.print(
            "[yellow]anvil init --existing (brownfield) is not implemented yet "
            "in the hackathon scaffold.[/yellow]"
        )
        return

    target_parent = out if out is not None else Path.cwd()

    try:
        asyncio.run(_init_greenfield(description, target_parent))
    except GeminiAuthError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(2) from e
    except GeminiResponseError as e:
        console.print(f"[red]Flash returned malformed output:[/red] {e}")
        raise SystemExit(2) from e


async def _init_greenfield(description: str, out: Path) -> None:
    today = date.today().isoformat()
    console.print(
        f"[bold cyan]anvil init[/bold cyan] (greenfield) — "
        f"description: [italic]{description}[/italic]\n"
    )

    with console.status(
        "[bold cyan]ProjectScribe[/bold cyan] is naming the project and writing project.md…"
    ):
        project = await run_project_scribe(description, today)

    target = (out / project.project_slug).resolve()
    if target.exists():
        console.print(
            f"[red]{target} already exists.[/red] "
            "Pass [bold]--out[/bold] to write elsewhere, or remove the directory and retry."
        )
        raise SystemExit(1)

    _scaffold_project(target)
    (target / "pdd" / "context" / "project.md").write_text(
        project.project_md, encoding="utf-8"
    )
    console.print(f"[green]✓[/green] ProjectScribe → [bold]{target}[/bold]")

    with console.status(
        "[bold cyan]ConventionsScribe ∥ PlanScribe[/bold cyan] "
        "tailoring conventions and decomposing into phases…"
    ):
        conv, plan = await asyncio.gather(
            run_conventions_scribe(project.project_md, today),
            run_plan_scribe(project.project_md, description, today),
        )

    ctx = target / "pdd" / "context"
    ctx.joinpath("conventions.md").write_text(conv.conventions_md, encoding="utf-8")
    ctx.joinpath("decisions.md").write_text(conv.decisions_md, encoding="utf-8")
    console.print("[green]✓[/green] ConventionsScribe → conventions.md, decisions.md")

    feature_dir = target / "pdd" / "prompts" / "features" / plan.feature_area
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / plan.plan_filename).write_text(plan.plan_md, encoding="utf-8")
    (feature_dir / plan.phase_01_filename).write_text(
        plan.phase_01_prompt_md, encoding="utf-8"
    )
    console.print(
        f"[green]✓[/green] PlanScribe → "
        f"[dim]{plan.feature_area}/{plan.plan_filename}[/dim] + phase-01 prompt"
    )

    _git_commit_initial(target, description)
    console.print(
        f"\n[bold green]Done.[/bold green] "
        f"`cd {project.project_slug}` to enter the project.\n"
        f"Next: [bold]anvil run --phase 1[/bold]"
    )


def _scaffold_project(target: Path) -> None:
    if target.exists():
        raise FileExistsError(f"{target} already exists")
    for sub in (
        "pdd/context",
        "pdd/prompts/features",
        "pdd/evals/baselines",
        "pdd/evals/scripts",
        "src",
    ):
        (target / sub).mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=target, check=True)


def _git_commit_initial(target: Path, description: str) -> None:
    summary = description.strip().splitlines()[0][:60]
    subprocess.run(["git", "add", "."], cwd=target, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=anvil@local",
            "-c",
            "user.name=anvil",
            "commit",
            "-q",
            "-m",
            f"chore: anvil init — {summary}",
        ],
        cwd=target,
        check=True,
    )
