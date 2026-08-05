# Frontier Handoff

The Frontier user should clone this experiment repository and use `prompts/frontier_handoff.md` as the ordinary task prompt for their Codex session.

Before DPL runs, install the Flowcept skill:

```bash
scripts/setup/install_flowcept_skill.sh
```

If Flowcept is not importable from the active environment, set `FLOWCEPT_ROOT` to the Flowcept checkout first. Start a new Codex session after installing the skill.

They should generate Frontier-specific pieces in that session:

- module/environment setup;
- Slurm scripts;
- run directories;
- condition-specific Flowcept settings;
- artifact export package.

Reusable analysis scripts in this repository should stay unchanged unless Frontier exposes a real portability bug.

## Scope

Frontier validation should run beyond the local Step 2 smoke test.

The Frontier run should execute the paper-scale LLM tutorial campaign with:

- data preparation and Dask training workflow;
- fixed seeds and bounded hyperparameter search;
- multiple training configurations within the allocation limits;
- validation metrics/loss records;
- checkpoints or model artifact records;
- Slurm job ids, requested nodes, elapsed time, states, and exit codes;
- node-hour accounting;
- telemetry/resource evidence available on Frontier.

The run does not need to maximize model quality. It needs to exercise the agentic loop and produce enough cross-domain provenance evidence for Q1-Q8.

## Required conditions

- Baseline: script-only workflow, no Codex adapter.
- OPL: Codex JSONL consumed by the adapter with DPL disabled.
- DPL: Codex JSONL consumed by the adapter with DPL enabled and the provenance skill active.

Use three repetitions per condition unless allocation time prevents it.

## Returned artifact

The returned package must follow `docs/artifact_contract.md`. It can be imported locally with:

```bash
.venv/bin/python scripts/capture/import_run.py --package-dir /path/to/package --mongo-db imported_frontier_run
```
