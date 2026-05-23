# Feature: Dev environment Makefile

**File:** pdd/prompts/features/devex/dev-environment.v1.0.0.md
**Created:** 2026-05-23
**Version:** 1.0.0
**Owns artifact:** [Makefile](../../../../Makefile)
**Flash calls:** 0 (human-authored; no model generation)
**Related decision:** [decisions.md](../../../context/decisions.md) — "Pin local Python to Homebrew `python@3.13` with `--copies` venv"

---

## Intent

Give every contributor one consistent way to bootstrap a working Anvil dev environment: create a Python venv, install Anvil + deps via `uv pip`, run tests, run the demo. The venv must be `--copies` (real binary, not symlinks) and the default Python must be one that can actually produce a `--copies` venv on macOS-arm64.

The Makefile is the only allowed entry point for setting up `.venv/`. Contributor docs (README, onboarding) should point at `make help` rather than reproducing the underlying `python -m venv` invocation.

## What to build

### 1. Top-level [Makefile](../../../../Makefile)

**Variables (top of file):**

```make
PYTHON ?= /opt/homebrew/bin/python3.13
VENV   := .venv
BIN    := $(VENV)/bin
ANVIL  := $(BIN)/anvil
```

`PYTHON` uses `?=` so a contributor on Linux or Intel-mac can override without editing the file:

```bash
PYTHON=$(brew --prefix python@3.13)/bin/python3.13 make dev
```

**Phony targets:** `help venv install dev test test-live demo clean reinstall`.

**Required recipes:**

- `help` — prints a one-line summary of each target (used as the default-ish discovery path).
- `$(VENV)/bin/python` — file target that creates the venv:
  ```make
  $(PYTHON) -m venv --copies $(VENV)
  $(BIN)/python -m pip install --quiet --upgrade pip
  $(BIN)/pip install --quiet uv
  ```
- `venv` — alias depending on `$(VENV)/bin/python`.
- `install` — `$(BIN)/uv pip install -e .` (depends on `venv`).
- `dev` — `$(BIN)/uv pip install -e ".[dev]"` (depends on `venv`).
- `test` — runs `$(BIN)/pytest -m "not live" -v`; tolerates pytest exit code 5 (no tests collected) so a fresh repo without tests does not fail the target.
- `test-live` — refuses to run without `.env`; sources `.env` and runs `$(BIN)/pytest -m live -v`.
- `demo` — refuses to run without `.env`; wipes `/tmp/anvil-demo`; runs `$(ANVIL) init "<sample description>" --out /tmp/anvil-demo`; prints the resulting tree.
- `reinstall` — `clean dev`.
- `clean` — removes `$(VENV)`, all `__pycache__/`, and all `*.egg-info/`.

## Acceptance

- `make help` prints every phony target with a one-line description.
- `make clean && make venv` succeeds and produces `.venv/bin/python3.13` as a real Mach-O binary (verify with `file .venv/bin/python3.13` — output contains `Mach-O` and `executable`, not `symbolic link`).
- `make dev` succeeds on a clean checkout against Homebrew `python@3.13`.
- `PYTHON=/opt/homebrew/anaconda3/bin/python3 make venv` (or any other working Python) overrides the default — proves `PYTHON` uses `?=`, not `=`.
- `make test` exits 0 even when no tests exist (pytest exit 5 must be tolerated).
- Invoking `make demo` or `make test-live` without `.env` prints `Missing .env with GOOGLE_API_KEY` and exits non-zero.

## Constraints (what the Makefile must never do)

- Never default `PYTHON` to bare `python3` — on macOS that resolves to Xcode's framework Python, which cannot create `--copies` venvs and will break this Makefile with `Error: This build of python cannot create venvs without using symlinks`.
- Never drop `--copies` from the `venv` recipe — see [decisions.md](../../../context/decisions.md).
- Never hardcode paths other than `$(VENV)`, `$(BIN)`, `$(ANVIL)` derived from `$(VENV)`. Contributors overriding `PYTHON` must still get a working build without further edits.
- Never use `pip install` in a recipe after `uv` is available — all installs go through `$(BIN)/uv pip`.
- Never add a recipe that mutates files outside the repo or `/tmp/anvil-demo`.

## Risks

- The `/opt/homebrew/bin/python3.13` default is macOS-arm64-specific. Linux and Intel-mac contributors must override via `PYTHON=...`. Cross-platform default detection is post-hackathon.
- If Homebrew renames or deprecates the `python@3.13` formula, the default path breaks. The override-via-env contract means contributors can recover without a code change, but the default will need a bump.
- `uv` is installed inside the venv (not globally) on purpose — keeps the venv self-contained — but it does mean every `make dev` after `make clean` re-downloads `uv`. Acceptable for now.

---

## Versioning log

- **v1.0.0** — 2026-05-23 — Initial. Replaces the previously untracked Makefile. Captures the Homebrew-pin + `--copies` decision after a contributor hit the symlink-venv error on Xcode's framework Python 3.9 and we traced the root cause.
