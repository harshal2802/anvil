"""anvil status — render phase progress, eval scores, and prompt versions as Rich tables."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.table import Table

from anvil.commands._status_scan import (
    PlanStatus,
    ProjectStatus,
    StatusScanError,
    scan_project,
)

console = Console()


_PHASES_EMPTY_PATH = "pdd/prompts/features/"
_EVALS_EMPTY_PATH = "pdd/evals/baselines/"
_PROMPTS_EMPTY_PATH = "anvil/prompts/sub-agents/ (or pdd/prompts/features/sub-agents/)"


def execute() -> None:
    cwd = Path.cwd()
    pdd_dir = cwd / "pdd"
    if not pdd_dir.is_dir():
        console.print(
            f"[red]Not inside an Anvil project (no pdd/ directory found in {cwd}).[/red]"
        )
        raise SystemExit(1)

    try:
        status = scan_project(cwd)
    except StatusScanError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1) from e

    console.print(_render_phases(status))
    console.print(_render_evals(status))
    console.print(_render_prompts(status))


def _render_phases(status: ProjectStatus) -> Table:
    table = Table(title="Phases", title_style="bold cyan", header_style="bold")
    table.add_column("Feature")
    table.add_column("PLAN")
    table.add_column("Phase")
    table.add_column("Prompt")
    table.add_column("Status")

    if not status.plans:
        table.add_row(
            "", "", "", "", f"[dim]no data found at {_PHASES_EMPTY_PATH}[/dim]"
        )
        return table

    for plan in status.plans:
        _add_plan_rows(table, plan)
    return table


def _add_plan_rows(table: Table, plan: PlanStatus) -> None:
    if not plan.phases:
        table.add_row(
            plan.feature_area,
            plan.plan_filename,
            "",
            "",
            "[dim]— not started[/dim]",
        )
        return

    for phase in plan.phases:
        if phase.merged:
            status_cell = "[green]✓ merged[/green]"
        else:
            status_cell = "[yellow]● prompt only[/yellow]"
        table.add_row(
            plan.feature_area,
            plan.plan_filename,
            f"{phase.phase_number:02d}",
            phase.prompt_filename,
            status_cell,
        )


def _render_evals(status: ProjectStatus) -> Table:
    table = Table(title="Evals", title_style="bold cyan", header_style="bold")
    table.add_column("Node")
    table.add_column("pass@1")

    if not status.evals:
        table.add_row("", f"[dim]no data found at {_EVALS_EMPTY_PATH}[/dim]")
        return table

    for ev in status.evals:
        if ev.pass_rate is None:
            cell = "[dim]—[/dim]"
        else:
            cell = f"[green]✓ {ev.pass_rate:.0%}[/green]"
        table.add_row(ev.node_name, cell)
    return table


def _render_prompts(status: ProjectStatus) -> Table:
    table = Table(title="Prompts", title_style="bold cyan", header_style="bold")
    table.add_column("Sub-agent")
    table.add_column("Version")
    table.add_column("File")

    if not status.prompts:
        table.add_row(
            "", "", f"[dim]no data found at {_PROMPTS_EMPTY_PATH}[/dim]"
        )
        return table

    for prompt in status.prompts:
        major, minor, patch = prompt.version
        table.add_row(prompt.name, f"v{major}.{minor}.{patch}", prompt.filename)
    return table
