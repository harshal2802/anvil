"""Discover and parse per-project PLAN.md + phase prompt artifacts.

`anvil init` produces:

    pdd/prompts/features/<area>/
        PLAN-<area>.md
        <area>-01-<phase-name>.md
        <area>-02-<phase-name>.md
        ...

This module finds that plan, parses the ordered list of phases, and
reads each phase prompt to extract the `## Intent` body. The
orchestrator then feeds that intent to NodeForge instead of the
hardcoded smoke-test intent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PhaseEntry:
    number: int
    name: str
    prompt_path: Path
    prompt_body: str
    intent: str


@dataclass(frozen=True)
class ProjectPlan:
    plan_path: Path
    feature_area: str
    phases: list[PhaseEntry]


def discover_plan(project_root: Path) -> ProjectPlan | None:
    """Return the first PLAN-*.md found under pdd/prompts/features/<area>/, or None."""
    candidates = sorted(project_root.glob("pdd/prompts/features/*/PLAN-*.md"))
    if not candidates:
        return None
    plan_path = candidates[0]
    feature_area = plan_path.parent.name
    phases = _parse_phases(plan_path.read_text(encoding="utf-8"), plan_path.parent)
    return ProjectPlan(plan_path=plan_path, feature_area=feature_area, phases=phases)


_PHASE_BLOCK = re.compile(
    r"^###\s+Phase\s+(\d+)\s*:\s*(.+?)\s*$"
    r"(?P<body>.*?)"
    r"(?=^###\s+Phase\s+\d+|\Z)",
    re.DOTALL | re.MULTILINE,
)
_PROMPT_REF = re.compile(r"\*\*Prompt:\*\*\s*(\S+)")
_PRODUCES_REF = re.compile(r"\*\*Produces:\*\*\s*(.+?)(?:\n|\Z)")
_INTENT_BLOCK = re.compile(r"##\s+Intent\s*\n(.*?)(?=\n##\s|\Z)", re.DOTALL)


def _parse_phases(plan_md: str, feature_dir: Path) -> list[PhaseEntry]:
    entries: list[PhaseEntry] = []
    for match in _PHASE_BLOCK.finditer(plan_md):
        number = int(match.group(1))
        name = match.group(2).strip()
        body = match.group("body")
        prompt_match = _PROMPT_REF.search(body)
        produces_match = _PRODUCES_REF.search(body)
        produces_text = produces_match.group(1).strip() if produces_match else ""

        if prompt_match:
            prompt_filename = Path(prompt_match.group(1).strip()).name
            prompt_path = feature_dir / prompt_filename
        else:
            prompt_path = feature_dir / _synthetic_prompt_filename(number, name, feature_dir)

        if prompt_path.exists():
            prompt_body = prompt_path.read_text(encoding="utf-8")
            intent_match = _INTENT_BLOCK.search(prompt_body)
            intent = intent_match.group(1).strip() if intent_match else prompt_body.strip()
        else:
            prompt_body = _synthesize_prompt_body(number, name, produces_text)
            prompt_path.parent.mkdir(parents=True, exist_ok=True)
            prompt_path.write_text(prompt_body, encoding="utf-8")
            intent = (
                f"Implement the `{name}` node. {produces_text}"
                if produces_text
                else f"Implement the `{name}` node per the PLAN."
            )

        entries.append(
            PhaseEntry(
                number=number,
                name=name,
                prompt_path=prompt_path,
                prompt_body=prompt_body,
                intent=intent,
            )
        )
    entries.sort(key=lambda p: p.number)
    return entries


def _synthetic_prompt_filename(number: int, name: str, feature_dir: Path) -> str:
    """Build a phase prompt filename matching PlanScribe's convention."""
    area = feature_dir.name
    slug = name.replace("_", "-").lower()
    return f"{area}-{number:02d}-{slug}.md"


def _synthesize_prompt_body(number: int, name: str, produces_text: str) -> str:
    """Stand-in phase prompt md when PlanScribe only emitted phase-01."""
    intent = produces_text or f"Implement the `{name}` node per the PLAN."
    return (
        f"# Phase {number}: {name}\n\n"
        f"## Intent\n{intent}\n\n"
        f"## Inputs\nInferred from prior phase outputs and the project state schema.\n\n"
        f"## Outputs\nWhatever this node produces should be added to GraphState "
        f"and consumed by downstream phases.\n\n"
        f"## Acceptance\n- Node integrates cleanly with the existing graph chain.\n"
        f"- All network/LLM calls retry with exponential backoff.\n"
        f"- Errors surface as `error` field on state, not raised exceptions.\n\n"
        f"_Note: this prompt was auto-synthesized from PLAN.md because "
        f"PlanScribe currently only emits the phase-01 prompt. Edit freely._\n"
    )
