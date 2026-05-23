"""Pydantic response schemas for the four sub-agents.

Mirror the JSON Schemas defined in pdd/prompts/features/sub-agents/.
Used as `response_schema` in Gemini Flash structured-output calls.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class NewStateField(BaseModel):
    name: str
    type: str
    rationale: str


class NodeForgeOutput(BaseModel):
    filename: str = Field(description="snake_case, ends in .py")
    node_name: str = Field(description="snake_case function name")
    module_code: str = Field(description="full Python source")
    reads_from_state: list[str]
    writes_to_state: list[str]
    new_state_fields: list[NewStateField]
    external_deps: list[str]
    self_review: str = Field(description="one sentence — weakest part of the code")


class JudgeRubric(BaseModel):
    correctness: str
    completeness: str
    safety: str


class EvalSmithOutput(BaseModel):
    golden_dataset_jsonl: str = Field(description="7 lines, each a valid JSON object")
    eval_runner_filename: str = Field(description="evals/test_<node_name>.py")
    eval_runner_code: str
    judge_rubric: JudgeRubric
    pass_threshold_explanation: str


class DocScribeOutput(BaseModel):
    filename: str = Field(description="docs/adr/{NNN}-{slug}.md")
    title: str
    markdown_body: str


class MergeBotOutput(BaseModel):
    pr_title: str = Field(description="imperative mood, <= 70 chars")
    pr_body_markdown: str
    labels: list[str]


class ProjectScribeOutput(BaseModel):
    project_slug: str = Field(description="kebab-case, 2-5 words")
    project_md: str = Field(description="full markdown body of pdd/context/project.md")


class ConventionsScribeOutput(BaseModel):
    conventions_md: str
    decisions_md: str


class PlanScribeOutput(BaseModel):
    plan_md: str
    phase_01_prompt_md: str
    plan_filename: str = Field(description="PLAN-<area>.md")
    phase_01_filename: str = Field(description="<area>-01-<phase-name>.md")
    feature_area: str = Field(description="kebab-case subdirectory under pdd/prompts/features/")
