# Anvil — Third-Party Notices and Attributions

This file documents external code and methodology that Anvil depends on, with explicit attribution and licensing terms.

---

## Vendored: PDD (Prompt Driven Development) workflows

Anvil uses the [PDD methodology](https://github.com/harshal2802/pdd-skill) as its process backbone. The following workflow files have been **vendored** (copied verbatim with a header banner) from the `pdd-skill` repository:

| Vendored path                                           | Source path (in pdd-skill)              |
|---------------------------------------------------------|------------------------------------------|
| `anvil/pdd_workflows/scaffold.md`                       | `core/workflows/scaffold.md`             |
| `anvil/pdd_workflows/init.md`                           | `core/workflows/init.md`                 |
| `anvil/pdd_workflows/context.md`                        | `core/workflows/context.md`              |
| `anvil/pdd_workflows/plan.md`                           | `core/workflows/plan.md`                 |
| `anvil/pdd_workflows/prompts.md`                        | `core/workflows/prompts.md`              |
| `anvil/pdd_workflows/eval.md`                           | `core/workflows/eval.md`                 |
| `anvil/pdd_workflows/review.md`                         | `core/workflows/review.md`               |
| `anvil/pdd_workflows/references/data-ml.md`             | `core/references/data-ml.md`             |

**Pinned commit:** `f83deb441aaf77cedd192eb10a01fe8a5c0d022c`
**Vendored on:** 2026-05-23

### License

`pdd-skill` is licensed under the [MIT License](https://github.com/harshal2802/pdd-skill/blob/main/LICENSE). Anvil is also MIT-licensed. Both projects are authored by Harshal Chourasiya.

The vendored files are unmodified except for a single header comment block at the top of each file marking provenance, the pinned SHA, and the vendoring date.

### Why vendor instead of depend?

PDD is a Claude Code skill (a directory of markdown instructions), not a Python package — there is nothing to `pip install`. Vendoring at a pinned SHA gives Anvil:

- Zero install friction for end users
- Reproducible behavior across Anvil versions (the same Anvil release always runs against the same PDD workflow text)
- A clean attribution boundary

### Update policy

Vendored files are **frozen** at the pinned commit SHA. To pull in upstream changes:

1. Update the pinned SHA at the top of this file
2. Re-run the vendoring script against the new SHA
3. Commit the result as a single PR titled `chore: refresh PDD workflows to <SHA-short>`

Updates flow **upstream → downstream only**. If a workflow file needs to change for Anvil-specific reasons, submit the change upstream to `pdd-skill` first, then re-vendor.

### Anvil's contributions back to pdd-skill

Anvil plans to contribute a new project-type reference file — `references/agent-graph.md` — covering LangGraph state schemas, stateful node design, evals for non-deterministic nodes, and deployment via LangServe. This file is being drafted as part of Anvil's hackathon build and will be submitted upstream as a pull request to `pdd-skill` after the Google I/O 2026 hackathon concludes.

---

## Hackathon contribution boundary

Per the [Google I/O 2026 hackathon rules](https://cerebralvalley.ai/e/google-io-hackathon), the contribution boundary for the hackathon submission is:

- **In scope (new work, this repo):** all Python source under `anvil/`, the CLI, the orchestrator, the four sub-agent prompts, the visual graph renderer, the GitHub integration, the LangServe wrapper, the web UI, and every example project under `examples/`.
- **Out of scope (prior work, used as-is):** the PDD methodology files vendored above, LangGraph, Gemini 3.5 Flash, LangServe, FastAPI, Next.js, react-flow, and standard Python dependencies.

PDD is the methodology Anvil enforces; Anvil is the LangGraph-specialized automation layer that operationalizes PDD via Gemini Flash. Both are authored by the same person; both are open source under MIT.
