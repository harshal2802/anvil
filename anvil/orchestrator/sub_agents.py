"""The four sub-agents that run inside a per-phase execution.

Execution shape (three steps, ~3 Flash calls in wall time):

  1. NodeForge                       (depends on phase input)
  2. EvalSmith ∥ DocScribe           (depend on NodeForge output)
  3. MergeBot                        (depends on EvalSmith + DocScribe)

MergeBot cannot run in parallel with EvalSmith and DocScribe because its
PR body references the eval path, the ADR filename, and the ADR title.
For demo theatre, the UI animates all four panels concurrently, but the
runtime sequence is honest about the dependency.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from anvil.orchestrator.gemini import run_agent
from anvil.orchestrator.prompt_loader import load_sub_agent_prompt
from anvil.orchestrator.schemas import (
    ConventionsScribeOutput,
    DocScribeOutput,
    EvalSmithOutput,
    MergeBotOutput,
    NodeForgeOutput,
    PlanScribeOutput,
    ProjectScribeOutput,
)


@dataclass(frozen=True)
class PhaseInput:
    user_intent: str
    existing_nodes_json: str
    state_schema_source: str
    repo_conventions_json: str
    next_adr_number: str = "001"
    today: str = "2026-05-23"


@dataclass(frozen=True)
class PhaseOutput:
    node: NodeForgeOutput
    evals: EvalSmithOutput
    adr: DocScribeOutput
    pr: MergeBotOutput


async def _node_forge(phase: PhaseInput) -> NodeForgeOutput:
    spec = load_sub_agent_prompt("node_forge")
    user_message = spec.render(
        user_intent=phase.user_intent,
        existing_nodes_json=phase.existing_nodes_json,
        state_schema_source=phase.state_schema_source,
        repo_conventions_json=phase.repo_conventions_json,
    )
    return await run_agent(
        system_instruction=spec.system_instruction,
        user_message=user_message,
        response_schema=NodeForgeOutput,
        temperature=spec.temperature,
    )


async def _eval_smith(phase: PhaseInput, node: NodeForgeOutput) -> EvalSmithOutput:
    spec = load_sub_agent_prompt("eval_smith")
    user_message = spec.render(
        user_intent=phase.user_intent,
        module_code=node.module_code,
        node_name=node.node_name,
        reads_from_state=", ".join(node.reads_from_state),
        writes_to_state=", ".join(node.writes_to_state),
    )
    return await run_agent(
        system_instruction=spec.system_instruction,
        user_message=user_message,
        response_schema=EvalSmithOutput,
        temperature=spec.temperature,
    )


async def _doc_scribe(phase: PhaseInput, node: NodeForgeOutput) -> DocScribeOutput:
    spec = load_sub_agent_prompt("doc_scribe")
    excerpt = "\n".join(node.module_code.splitlines()[:40])
    user_message = spec.render(
        user_intent=phase.user_intent,
        node_name=node.node_name,
        first_40_lines_of_module_code=excerpt,
        node_forge_self_review_field=node.self_review,
        existing_nodes_json=phase.existing_nodes_json,
        next_adr_number=phase.next_adr_number,
        today=phase.today,
    )
    return await run_agent(
        system_instruction=spec.system_instruction,
        user_message=user_message,
        response_schema=DocScribeOutput,
        temperature=spec.temperature,
    )


async def _merge_bot(
    phase: PhaseInput,
    node: NodeForgeOutput,
    evals: EvalSmithOutput,
    adr: DocScribeOutput,
) -> MergeBotOutput:
    spec = load_sub_agent_prompt("merge_bot")
    file_list = [
        f"src/nodes/{node.filename}",
        evals.eval_runner_filename,
        adr.filename,
    ]
    user_message = spec.render(
        user_intent=phase.user_intent,
        node_name=node.node_name,
        file_list_json=str(file_list),
        adr_filename_and_title=f"{adr.filename} — {adr.title}",
        eval_runner_filename=evals.eval_runner_filename,
        node_forge_self_review_field=node.self_review,
    )
    return await run_agent(
        system_instruction=spec.system_instruction,
        user_message=user_message,
        response_schema=MergeBotOutput,
        temperature=spec.temperature,
    )


async def forge_phase(phase: PhaseInput) -> PhaseOutput:
    """Run the per-phase execution: NodeForge, then (EvalSmith ∥ DocScribe), then MergeBot."""
    node = await _node_forge(phase)
    evals, adr = await asyncio.gather(
        _eval_smith(phase, node),
        _doc_scribe(phase, node),
    )
    pr = await _merge_bot(phase, node, evals, adr)
    return PhaseOutput(node=node, evals=evals, adr=adr, pr=pr)


async def run_project_scribe(description: str, today: str) -> ProjectScribeOutput:
    spec = load_sub_agent_prompt("project_scribe")
    user_message = spec.render(description=description, today=today)
    return await run_agent(
        system_instruction=spec.system_instruction,
        user_message=user_message,
        response_schema=ProjectScribeOutput,
        temperature=spec.temperature,
    )


async def run_conventions_scribe(project_md: str, today: str) -> ConventionsScribeOutput:
    spec = load_sub_agent_prompt("conventions_scribe")
    user_message = spec.render(project_md=project_md, today=today)
    return await run_agent(
        system_instruction=spec.system_instruction,
        user_message=user_message,
        response_schema=ConventionsScribeOutput,
        temperature=spec.temperature,
    )


async def run_plan_scribe(
    project_md: str, description: str, today: str
) -> PlanScribeOutput:
    spec = load_sub_agent_prompt("plan_scribe")
    user_message = spec.render(
        project_md=project_md, description=description, today=today
    )
    return await run_agent(
        system_instruction=spec.system_instruction,
        user_message=user_message,
        response_schema=PlanScribeOutput,
        temperature=spec.temperature,
    )


async def run_plan_scribe_scoped(
    project_md: str, change: str, target_node: str, today: str
) -> PlanScribeOutput:
    scoped_description = f"Single-node change to `{target_node}`: {change}"
    return await run_plan_scribe(
        project_md=project_md, description=scoped_description, today=today
    )
