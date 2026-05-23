"""Load PDD-formatted prompt files and extract orchestrator-relevant sections.

Each sub-agent prompt file under `anvil/prompts/sub-agents/` follows the
PDD prompt template with extensions (see pdd/prompts/features/sub-agents/
for the source of truth). This loader pulls out:

  - the Gemini system instruction (fenced block under "## System instruction...")
  - the user message template     (fenced block under "## User message template")
  - the temperature                (from "**Temperature:**" in the frontmatter)

Prompts are versioned in filenames (e.g., `node_forge.v1.0.0.md`). The
loader picks the highest version on disk.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from importlib import resources


@dataclass(frozen=True)
class PromptSpec:
    system_instruction: str
    user_template: str
    temperature: float

    def render(self, **context: object) -> str:
        out = self.user_template
        for key, value in context.items():
            out = out.replace(f"{{{{{key}}}}}", str(value))
        return out


def _extract_fenced_block(text: str, header: str) -> str:
    pattern = rf"##\s+{re.escape(header)}.*?\n```\w*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        raise ValueError(f"Could not find fenced block under '## {header}'")
    return match.group(1).strip()


def _extract_temperature(text: str) -> float:
    match = re.search(r"\*\*Temperature:\*\*\s*`?(\d+\.\d+)`?", text)
    if not match:
        raise ValueError("Could not find Temperature in prompt frontmatter")
    return float(match.group(1))


def load_sub_agent_prompt(name: str) -> PromptSpec:
    """Load a sub-agent prompt by name (e.g., 'node_forge'). Picks the highest version."""
    pkg = resources.files("anvil").joinpath("prompts", "sub-agents")
    candidates = sorted(
        (
            p
            for p in pkg.iterdir()
            if p.name.startswith(f"{name}.v") and p.name.endswith(".md")
        ),
        key=lambda p: p.name,
    )
    if not candidates:
        raise FileNotFoundError(
            f"No prompt file found for sub-agent '{name}' under {pkg}"
        )
    text = candidates[-1].read_text(encoding="utf-8")
    return PromptSpec(
        system_instruction=_extract_fenced_block(
            text, "System instruction (sent as Gemini system prompt)"
        ),
        user_template=_extract_fenced_block(text, "User message template"),
        temperature=_extract_temperature(text),
    )
