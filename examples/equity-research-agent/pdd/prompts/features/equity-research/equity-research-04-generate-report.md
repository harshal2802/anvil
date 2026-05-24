# Phase 4: generate_report

## Intent
one LangGraph node — `generate_report` which compiles the final structured markdown report using Gemini Flash and validates it with Pydantic.

## Inputs
Inferred from prior phase outputs and the project state schema.

## Outputs
Whatever this node produces should be added to GraphState and consumed by downstream phases.

## Acceptance
- Node integrates cleanly with the existing graph chain.
- All network/LLM calls retry with exponential backoff.
- Errors surface as `error` field on state, not raised exceptions.

_Note: this prompt was auto-synthesized from PLAN.md because PlanScribe currently only emits the phase-01 prompt. Edit freely._
