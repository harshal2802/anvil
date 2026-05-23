"""Read-only filesystem scanner for `anvil status`."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


_PHASE_FILENAME_RE = re.compile(r"^(?P<phase>\d{2})-(?P<rest>.+)\.md$")
_PROMPT_VERSION_RE = re.compile(
    r"^(?P<name>.+)\.v(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)\.md$"
)


class StatusScanError(Exception):
    """Unrecoverable scan error. Malformed JSON is logged at DEBUG, not raised."""


@dataclass(frozen=True)
class PhaseStatus:
    phase_number: int
    prompt_filename: str
    merged: bool


@dataclass(frozen=True)
class PlanStatus:
    plan_filename: str
    feature_area: str
    phases: tuple[PhaseStatus, ...]


@dataclass(frozen=True)
class EvalStatus:
    node_name: str
    pass_rate: float | None


@dataclass(frozen=True)
class PromptStatus:
    name: str
    version: tuple[int, int, int]
    filename: str


@dataclass(frozen=True)
class ProjectStatus:
    root: Path
    plans: tuple[PlanStatus, ...]
    evals: tuple[EvalStatus, ...]
    prompts: tuple[PromptStatus, ...]


def scan_project(root: Path) -> ProjectStatus:
    """Walk <root>/pdd/ and <root>/src/ once and return the observed state."""
    root = root.resolve()
    return ProjectStatus(
        root=root,
        plans=_scan_plans(root),
        evals=_scan_evals(root),
        prompts=_scan_prompts(root),
    )


def _scan_plans(root: Path) -> tuple[PlanStatus, ...]:
    features_dir = root / "pdd" / "prompts" / "features"
    if not features_dir.is_dir():
        return ()

    nodes_dir = root / "src" / "nodes"
    baselines_dir = root / "pdd" / "evals" / "baselines"

    plans: list[PlanStatus] = []
    for plan_path in sorted(features_dir.rglob("PLAN-*.md")):
        feature_dir = plan_path.parent
        phases: list[PhaseStatus] = []
        for sibling in sorted(feature_dir.glob("*.md")):
            if sibling == plan_path:
                continue
            match = _PHASE_FILENAME_RE.match(sibling.name)
            if match is None:
                continue
            phase_number = int(match.group("phase"))
            # evidence-based, not git-authoritative: a phase counts as merged
            # iff both a node module and a baseline JSON exist on disk.
            node_candidate = match.group("rest")
            merged = (
                (nodes_dir / f"{node_candidate}.py").is_file()
                and (baselines_dir / f"{node_candidate}.json").is_file()
            )
            phases.append(
                PhaseStatus(
                    phase_number=phase_number,
                    prompt_filename=sibling.name,
                    merged=merged,
                )
            )
        plans.append(
            PlanStatus(
                plan_filename=plan_path.name,
                feature_area=feature_dir.name,
                phases=tuple(phases),
            )
        )
    return tuple(plans)


def _scan_evals(root: Path) -> tuple[EvalStatus, ...]:
    baselines_dir = root / "pdd" / "evals" / "baselines"
    if not baselines_dir.is_dir():
        return ()

    evals: list[EvalStatus] = []
    for baseline_path in sorted(baselines_dir.glob("*.json")):
        try:
            raw = baseline_path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (json.JSONDecodeError, OSError) as exc:
            logger.debug("Skipping malformed baseline %s: %s", baseline_path, exc)
            continue
        if not isinstance(data, dict):
            logger.debug("Skipping non-object baseline %s", baseline_path)
            continue
        pass_rate: float | None = None
        for key in ("pass_at_1", "pass_rate"):
            if key in data:
                value = data[key]
                if isinstance(value, (int, float)):
                    pass_rate = float(value)
                    break
        evals.append(EvalStatus(node_name=baseline_path.stem, pass_rate=pass_rate))
    return tuple(evals)


def _scan_prompts(root: Path) -> tuple[PromptStatus, ...]:
    runtime_mirror = root / "anvil" / "prompts" / "sub-agents"
    canonical = root / "pdd" / "prompts" / "features" / "sub-agents"
    source_dir = runtime_mirror if runtime_mirror.is_dir() else canonical
    if not source_dir.is_dir():
        return ()

    highest: dict[str, PromptStatus] = {}
    for prompt_path in sorted(source_dir.glob("*.v*.md")):
        match = _PROMPT_VERSION_RE.match(prompt_path.name)
        if match is None:
            continue
        name = match.group("name")
        version = (
            int(match.group("major")),
            int(match.group("minor")),
            int(match.group("patch")),
        )
        current = highest.get(name)
        if current is None or version > current.version:
            highest[name] = PromptStatus(
                name=name, version=version, filename=prompt_path.name
            )
    return tuple(sorted(highest.values(), key=lambda p: p.name))
