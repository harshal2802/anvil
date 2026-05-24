# feat: implement generate_report node for structured markdown output

Labels: feature, langgraph, evaluation

## Summary
- Adds the generate_report LangGraph node to compile structured markdown reports.
- Integrates Gemini Flash with Pydantic validation to ensure output schema compliance.
- Includes unit and integration tests for the new node.

## Why
We need a reliable way to generate structured markdown reports that conform to a strict schema. This implementation follows the design outlined in docs/adr/004-implement-generate-report-node.md.

## Changes
- src/nodes/generate_report.py: Implement the generate_report node using Gemini Flash and Pydantic validation.
- evals/test_generate_report.py: Add unit and integration tests to verify report generation and schema validation.
- docs/adr/004-implement-generate-report-node.md: Document the architectural decision for the report generation node.

## Eval Status
Run `pytest evals/test_generate_report.py` — judge scores populate on first CI run.

## Risk
The node assumes the passed-in model client supports the `with_structured_output` interface. If a raw SDK client or an incompatible LangChain model is passed instead of a compatible chat model, the node will raise an AttributeError at runtime.

## Reviewer Checklist
- Verify that the Pydantic schema correctly validates the generated markdown structure.
- Confirm that the node handles API timeouts or validation failures gracefully.
- Ensure the model client initialization in tests uses a mock or client that supports `with_structured_output`.
