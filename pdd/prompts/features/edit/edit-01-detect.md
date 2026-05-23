# Phase 1: Project-state loader + target-node detection (no Flash)

**Plan:** [PLAN-edit.md](PLAN-edit.md)
**Phase:** 1 of 4
**Estimated time:** ~25 min
**Dependencies:** none
**Flash calls:** 0

## Intent

Lay the foundation for `anvil edit "<change>"` by validating that the cwd is an Anvil project, enumerating already-shipped nodes from `src/nodes/*.py` (the source-of-truth per the PLAN's Decisions table), and deterministically picking the single node a plain-English change targets. No Flash, no PlanScribe, no `forge_phase` — those land in Phases 2 and 3. The whole surface is exit-on-ambiguity: never block on stdin, always print a copy-pasteable rerun hint.

## What to build

### 1. [anvil/commands/edit.py](../../../../anvil/commands/edit.py)

Rewrite the 19-line stub. Public surface stays `execute(change: str) -> None`; the CLI signature in `anvil/cli.py` is already wired and does not change.

#### Typed exceptions (module-local)

```python
class EditError(Exception):
    """Base for anvil-edit failures."""


class NotAnAnvilProjectError(EditError): ...


class NoNodesFoundError(EditError): ...


class AmbiguousTargetError(EditError): ...
```

#### `NodeSummary` dataclass

```python
@dataclass(frozen=True)
class NodeSummary:
    name: str
    module_path: Path
```

Optional fields `reads_from_state`/`writes_to_state` are deferred — v1 detection only needs `name`. Leave a TODO note rather than over-engineering.

#### Helper: `_enumerate_existing_nodes`

```python
def _enumerate_existing_nodes(project_root: Path) -> list[NodeSummary]: ...
```

- Globs `<project_root>/src/nodes/*.py`.
- Excludes `__init__.py`.
- Builds one `NodeSummary` per file (name = filename stem).
- If `src/nodes/` is missing OR the glob is empty, raises `NoNodesFoundError("No nodes shipped yet — run `anvil run --phase 1` first")`.

#### Helper: `_detect_target_node`

```python
def _detect_target_node(change: str, existing_nodes: list[NodeSummary]) -> str: ...
```

Deterministic v1 (per PLAN Decisions table: ship deterministic first):

1. Lowercase the change string; split on non-alphanumeric → set of change-tokens.
2. For each node, split `node.name` on `_` → set of name-tokens.
3. Score = `len(change_tokens & name_tokens)`.
4. If exactly one node has the unique top positive score → return its name.
5. If multiple tie at the top positive score OR every score is 0 → raise `AmbiguousTargetError` with a hint:
   `f"Ambiguous — rerun as: anvil edit \"<change> in <node-name>\". Candidates: {', '.join(c.name for c in candidates)}"` (candidates = either the tied top-scorers or, if all scores were 0, every node).
6. Leave `# TODO: Flash-detection expansion point` near the scoring block so the PLAN's Decisions-table directive is visible.

#### `execute(change)`

```python
def execute(change: str) -> None: ...
```

1. Locate project root via `Path.cwd()` and require `pdd/context/project.md` to exist. If not, raise `NotAnAnvilProjectError(f"Not inside an Anvil project (no pdd/context/project.md found in {cwd}).")`.
2. `nodes = _enumerate_existing_nodes(project_root)`.
3. `target = _detect_target_node(change, nodes)`.
4. On success, print:
   ```
   [bold cyan]anvil edit[/bold cyan] — change: [italic]{change}[/italic]
   [green]✓[/green] Target node detected: [bold]{target}[/bold]
   [dim]Phase 2 wires scoped PlanScribe — coming next.[/dim]
   ```
5. Wrap the three `EditError` subtypes in a `try/except` block shaped like `commands/init.py`'s `GeminiAuthError` handling — Rich-print the message, `raise SystemExit(1) from e`.

## Acceptance

- `cd /tmp && anvil edit "anything"` prints "Not inside an Anvil project …" and exits 1.
- Inside an Anvil project with `src/nodes/` empty (or absent), `anvil edit "anything"` prints the "No nodes shipped yet …" hint and exits 1.
- Inside a project with one node `triage_email.py`, `anvil edit "tag language on the triage step"` resolves to `triage_email` (token overlap on "triage") and exits 0 with the Rich confirmation.
- With two nodes `triage_email.py` and `draft_reply.py`, `anvil edit "improve performance"` (no token overlap) exits 1 with `Ambiguous — rerun as: anvil edit "<change> in <node-name>". Candidates: triage_email, draft_reply`.
- With two nodes that tie on token score, the candidate list lists only the tied ones.
- `mypy --strict anvil/commands/edit.py` is clean. No bare excepts. No `print()`.

## Risks

- **Tokenizer brittleness.** Splitting on non-alphanumeric is crude — a node named `triageemail` (no underscore) gets one big token and matches nothing. Mitigation: the PLAN explicitly accepts deterministic-first; the TODO marker is the upgrade path.
- **All-zero-score edges.** A change like "add retries" against a project with nodes `summarize_url` / `load_inputs` legitimately has no overlap — the ambiguity exit is the right UX. The candidate list shows the user every node so they can pick one and rerun with `in <name>` phrasing.
- **`src/nodes/` source-of-truth.** Per PLAN Decisions: the filesystem after `anvil run` is ground truth (aborted runs can leave stale phase prompts). Do not enumerate from `pdd/prompts/features/*/*-NN-*.md`.
- **`Path.cwd()` vs project-root walk-up.** v1 only checks cwd directly (cheap, matches the demo path). Walking up to find the nearest `pdd/context/project.md` is a post-demo polish item.
