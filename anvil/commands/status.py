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

    _print_phases(status)
    _print_evals(status)
    _print_prompts(status)


def _print_phases(status: ProjectStatus) -> None:
    if not status.plans:
        _print_empty("Phases", _PHASES_EMPTY_PATH)
        return
    table = Table(title="Phases", title_style="bold cyan", header_style="bold")
    table.add_column("Feature")
    table.add_column("PLAN")
    table.add_column("Phase")
    table.add_column("Prompt")
    table.add_column("Status")
    for plan in status.plans:
        _add_plan_rows(table, plan)
    console.print(table)


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


def _print_evals(status: ProjectStatus) -> None:
    if not status.evals:
        _print_empty("Evals", _EVALS_EMPTY_PATH)
        return
    table = Table(title="Evals", title_style="bold cyan", header_style="bold")
    table.add_column("Node")
    table.add_column("pass@1")
    for ev in status.evals:
        if ev.pass_rate is None:
            cell = "[dim]—[/dim]"
        else:
            cell = f"[green]✓ {ev.pass_rate:.0%}[/green]"
        table.add_row(ev.node_name, cell)
    console.print(table)


def _print_prompts(status: ProjectStatus) -> None:
    if not status.prompts:
        _print_empty("Prompts", _PROMPTS_EMPTY_PATH)
        return
    table = Table(title="Prompts", title_style="bold cyan", header_style="bold")
    table.add_column("Sub-agent")
    table.add_column("Version")
    table.add_column("File")
    for prompt in status.prompts:
        major, minor, patch = prompt.version
        table.add_row(prompt.name, f"v{major}.{minor}.{patch}", prompt.filename)
    console.print(table)


def _print_empty(section_title: str, expected_path: str) -> None:
    console.print(f"\n[bold cyan]{section_title}[/bold cyan]")
    console.print(f"  [dim]no data found at {expected_path}[/dim]")
