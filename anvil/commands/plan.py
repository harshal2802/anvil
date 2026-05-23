"""anvil plan — decompose a feature into phases and open GitHub issues."""

from __future__ import annotations

import asyncio
import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from rich.console import Console
from tenacity import retry, stop_after_attempt, wait_exponential

from anvil.orchestrator.gemini import GeminiAuthError, GeminiResponseError
from anvil.orchestrator.sub_agents import run_plan_scribe

console = Console()


class PlanError(Exception):
    """Raised when plan setup (project root, gh availability) fails."""


class GhCliError(PlanError):
    """Raised when `gh issue create` exits non-zero."""


@dataclass(frozen=True)
class PhaseRef:
    number: int
    name: str
    body: str


_PHASE_HEADING_RE = re.compile(
    r"^###\s+Phase\s+(\d+):\s+(.+?)\s*$",
    re.MULTILINE,
)


def _parse_phases(plan_md: str) -> list[PhaseRef]:
    matches = list(_PHASE_HEADING_RE.finditer(plan_md))
    if not matches:
        return []
    phases: list[PhaseRef] = []
    for i, m in enumerate(matches):
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(plan_md)
        body_slice = plan_md[body_start:body_end]
        next_h2 = re.search(r"^##\s+", body_slice, re.MULTILINE)
        if next_h2 is not None:
            body_slice = body_slice[: next_h2.start()]
        phases.append(
            PhaseRef(
                number=int(m.group(1)),
                name=m.group(2).strip(),
                body=body_slice.strip("\n"),
            )
        )
    return phases


_PRODUCES_RE = re.compile(
    r"\*\*Produces:\*\*\s*\n(.*?)(?=\n\s*\n|\n\*\*|\Z)",
    re.DOTALL,
)
_DEPENDS_RE = re.compile(r"\*\*Depends on:\*\*\s*(.+?)\s*(?:\n|$)")
_RISK_RE = re.compile(r"\*\*Risk:\*\*\s*(.+?)\s*(?:\n|$)")


def _extract_phase_summary(phase_body: str) -> dict[str, str]:
    produces_match = _PRODUCES_RE.search(phase_body)
    depends_match = _DEPENDS_RE.search(phase_body)
    risk_match = _RISK_RE.search(phase_body)
    return {
        "produces": produces_match.group(1).strip() if produces_match else "",
        "depends_on": depends_match.group(1).strip() if depends_match else "",
        "risk": risk_match.group(1).strip() if risk_match else "",
    }


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
def _create_issue(title: str, body: str, labels: list[str]) -> str:
    cmd = ["gh", "issue", "create", "--title", title, "--body", body]
    for lbl in labels:
        cmd.extend(["--label", lbl])
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip() or "unknown error"
        raise GhCliError(f"gh issue create failed: {stderr}")
    for line in reversed((result.stdout or "").splitlines()):
        candidate = line.strip()
        if candidate:
            return candidate
    raise GhCliError("gh issue create succeeded but printed no URL")


def _build_issue_body(
    phase: PhaseRef,
    summary: dict[str, str],
    back_ref: str,
) -> str:
    parts: list[str] = []
    if summary["produces"]:
        parts.append(f"**Produces:**\n{summary['produces']}")
    if summary["depends_on"]:
        parts.append(f"**Depends on:** {summary['depends_on']}")
    if summary["risk"]:
        parts.append(f"**Risk:** {summary['risk']}")
    parts.append(back_ref)
    parts.append("---\nOpened by `anvil plan`.")
    return "\n\n".join(parts)


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

    phases = _parse_phases(output.plan_md)
    if not phases:
        raise PlanError(
            "PlanScribe emitted no parseable '### Phase N:' headings. "
            "PLAN is on disk; open issues manually."
        )

    back_ref = (
        f"From PLAN: pdd/prompts/features/"
        f"{output.feature_area}/{output.plan_filename}"
    )
    labels = ["anvil-phase", output.feature_area]
    successes: list[tuple[PhaseRef, str]] = []
    failures: list[tuple[PhaseRef, GhCliError]] = []

    for phase in phases:
        summary = _extract_phase_summary(phase.body)
        title = f"[{output.feature_area}] Phase {phase.number}: {phase.name}"
        body = _build_issue_body(phase, summary, back_ref)
        try:
            url = _create_issue(title, body, labels)
        except GhCliError as e:
            failures.append((phase, e))
            console.print(
                f"[yellow]⚠[/yellow] Phase {phase.number} ({phase.name}): {e}"
            )
            continue
        successes.append((phase, url))
        console.print(f"[green]✓[/green] #{phase.number}: {url}")

    console.print(
        f"\n[bold green]Opened {len(successes)} issues[/bold green] for feature "
        f"`{output.feature_area}`. Next: [bold]anvil run --phase 1[/bold]"
    )

    if failures:
        console.print("\n[red]Failures:[/red]")
        for phase, err in failures:
            console.print(
                f"  [red]✗[/red] Phase {phase.number} ({phase.name}): {err}"
            )
        console.print(
            f"\n[red]⚠ {len(failures)} issue(s) failed — see above. "
            "PLAN is on disk; rerun `gh issue create` manually for the failed phases."
            "[/red]"
        )
        raise SystemExit(1)


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
        "\n[bold green]Done.[/bold green] PLAN + issues created. "
        "Next: [bold]anvil run --phase 1[/bold]"
    )
