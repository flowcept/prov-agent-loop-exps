# Frontier Machine Learning Workflow Prompt

You are running the Frontier-scale version of the Flowcept LLM tutorial experiment.

Human objective:

Explore model sizes, learning rates, batch sizes, data slices, and stopping criteria while using at most 10 requested Frontier nodes, completing each campaign within 30 minutes of running wall time, staying below an explicit agent-token budget, and producing a model that satisfies an explicit validation-loss threshold.

Use this experiment repository for manifests, settings templates, analysis scripts, query definitions, and artifact packaging. Use Flowcept's LLM tutorial as the application code. Existing local configuration files may be used as examples for paths and expected schema, but do not treat their hyperparameters as the Frontier search space. Generate Frontier-specific setup and a fresh per-run Frontier search configuration yourself.

Use the run manifest prepared by the human as the source of truth for run identity. For each condition/repetition, the human should already have created `runs/local/<run_id>/manifest.yaml`, `runs/local/<run_id>/flowcept-settings.yaml`, and `runs/local/<run_id>/run.env`. Source the existing `run.env` before running commands. Do not create a new manifest, and do not invent or manually rewrite campaign ids. Use the same `$PAL_CAMPAIGN_ID` for the code-assistant provenance and for every Flowcept-instrumented machine-learning workflow command, including generated Slurm scripts.

Before executing, create a concise plan that maps plan steps to concrete work:

- environment/module setup;
- conda or virtual environment setup;
- Flowcept configuration;
- fresh per-run search-space generation;
- code edits or configuration changes;
- tests or smoke validations;
- Slurm submission scripts;
- Dask data-preparation and training executions;
- explicit evaluation criteria for node budget, wall time, token usage, and validation loss;
- validation-loss and metric evaluations;
- Slurm status queries and log inspection;
- telemetry retrieval;
- pruning of unpromising trials;
- expansion of promising regions of the search space;
- checkpoint/model artifact preservation;
- final export package creation.

Respect these constraints:

- use at most 10 requested nodes;
- keep each campaign within 30 minutes of running wall time;
- choose and record an explicit agent-token budget before execution if one is not already present in the manifest or prompt;
- choose and record an explicit validation-loss threshold before execution if one is not already present in the manifest or prompt;
- generate a new per-run parameter/search-space file before executing the workflow;
- choose bounded Frontier search parameters yourself from the human objective and allocation limits;
- use fixed seeds in the generated search configuration;
- record model size, learning rate, batch size, data slice, stopping criteria, and validation result for every trial;
- preserve Slurm job ids, requested nodes, elapsed time, states, exit codes, stdout, and stderr;
- preserve Dask logs, workflow outputs, validation metrics/losses, telemetry summaries, checkpoints or model artifacts, generated scripts, settings, Codex JSONL, and manifests;
- do not change the scientific objective unless a blocker requires it;
- keep analysis scripts unchanged unless Frontier evidence exposes a real portability bug.

During execution, use tool invocations to run shell commands, edit files, launch jobs, query job status, inspect logs, retrieve telemetry, evaluate results, revise the plan, prune unpromising trials, and expand promising search regions when evidence supports doing so.

Run the validation-scale campaign, not only the local Step 2 smoke test. The run does not need to maximize model quality; it needs to produce enough cross-domain evidence to answer the Q1-Q8 provenance queries.

At the end, write a run summary containing:

- commands executed;
- git commit before and after;
- environment details;
- Slurm job ids and node-hours;
- node-budget, wall-time, token-budget, and validation-loss-threshold checks;
- hyperparameters and metrics;
- selected checkpoint/model artifact paths;
- telemetry/resource evidence paths;
- failures, retries, repairs, pruning decisions, and plan revisions;
- final status;
- files included in the export package.
