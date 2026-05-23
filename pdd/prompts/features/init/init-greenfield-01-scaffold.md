# Phase 1: Scaffold + --out + git (no Flash)

**Plan:** [PLAN-init-greenfield.md](PLAN-init-greenfield.md)
**Phase:** 1 of 4
**Estimated time:** ~20 min
**Dependencies:** none
**Flash calls:** 0

## Intent

Lay the filesystem foundation for `anvil init` greenfield. Adds the `--out` option to the CLI, replaces the stub `init.py` with a real entry point that prepares the async greenfield function (filled in Phase 2/3), and provides a `_scaffold_project` helper that creates the directory tree + git init.

## What to build

### 1. [anvil/cli.py](../../../../anvil/cli.py)
Add a `--out` Typer Option to `init_cmd`:

```python
out: Path = typer.Option(
    Path.cwd(),
    "--out",
    "-o",
    help="Parent directory for the new project. Defaults to cwd.",
)
```

Pass it through to `init.execute(description=description, existing=existing, out=out)`.

### 2. [anvil/commands/init.py](../../../../anvil/commands/init.py)
Replace the stub. Public surface:

```python
def execute(description: str, existing: bool, out: Path) -> None: ...
```

- If `existing` is True: print "brownfield not yet implemented" and exit 0 (out of scope this phase).
- Else: call `asyncio.run(_init_greenfield(description, out))`.
- In this phase, `_init_greenfield` is a stub that prints the parsed args and exits — no Flash, no filesystem writes yet. Phase 2 wires Flash; Phase 3 wires the rest.

### 3. `_scaffold_project(target: Path) -> None` helper (in `init.py`)

```
target/
├── pdd/
│   ├── context/
│   ├── prompts/features/
│   └── evals/
│       ├── baselines/
│       └── scripts/
├── src/
└── .git/                 (via `git init`)
```

- Error if `target` already exists (do not overwrite).
- `subprocess.run(["git", "init", "-q"], cwd=target, check=True)`.
- Do NOT create an initial commit here — Phase 3 makes the single commit after all files land.

## Acceptance

- `anvil init --help` shows `--out` option.
- `anvil init "foo" --out /tmp/anvil-test` runs the stub `_init_greenfield`, prints parsed args, exits 0. No filesystem changes yet (that's Phase 2's job once the slug is known).
- `_scaffold_project(Path("/tmp/foo123"))` from a Python REPL creates the expected tree with `.git/` initialized.

## Risks

- `subprocess` git availability — assumed (hackathon target machine has git).
- Existing dir collision is handled at the `_scaffold_project` boundary, but the *check* runs only after Phase 2 produces the Flash-derived slug. Acceptable: the Flash call paid in is sunk cost, the error message tells the user to retry with `--out`.
