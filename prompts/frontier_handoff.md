# Frontier Handoff Prompt

You are running the Frontier-scale repetition of the Flowcept LLM tutorial experiment. Reuse this repository for analysis and manifests, but generate Frontier-specific setup yourself:

- Install Flowcept's versioned `agent-loop-provenance` skill from `resources/skills/agent-loop-provenance` before DPL runs.
- Create environment setup for Frontier.
- Generate Slurm scripts for the same tutorial workflow.
- Run beyond the local Step 2 smoke test: execute the validation-scale Dask training campaign with fixed seeds/search bounds, validation metrics/losses, checkpoints or model artifacts, Slurm job records, node-hours, and telemetry/resource evidence.
- Preserve all generated scripts, settings, logs, Slurm stdout/stderr, Codex JSONL, and Mongo export package.
- Run the same experimental conditions: baseline, OPL, and DPL.
- Use three repetitions per condition unless constrained by allocation time.
- For DPL, use the provenance skill and emit explicit plan, step, loop, evaluation, criteria, result, decision, observation, belief, memory, and lesson learned annotations.

Do not change the analysis scripts unless Frontier evidence exposes a real bug. Export the run packages so they can be imported and queried locally.
