# Frontier Machine Learning Workflow Prompt

You are helping run Flowcept's Dask-based LLM hyperparameter grid-search workflow on OLCF Frontier using Slurm.

Objective:
Implement, execute, and refine the Frontier workflow so it searches model sizes, learning rates, batch sizes, and data slices, evaluates trial loss against node-hour consumption, prunes unpromising trials, and expands promising regions until the loss threshold or stopping criteria are met.

Use the experiment repository only as the control/capture/analysis harness. Do not treat this repository as the application implementation. The executable campaign code, Slurm scripts, workflow configs, search configs, logs, summaries, and any run-specific helper scripts must be created or adapted inside `$PAL_RUN_DIR`. Existing repository files may be inspected only as examples of expected structure or reusable harness commands.

Before executing, create a concise implementation plan that makes the steps explicit. The plan should identify:

- what repository files, tutorial files, or scripts need to be inspected or created;
- how the conda environment present in this directory will be used;
- which Slurm scripts or commands will launch and monitor Dask training jobs;
- which hyperparameters will be searched and which run-specific bounds/configuration will be created;
- how trial loss, node-hour consumption, resource use, and stopping criteria will be evaluated;
- how Flowcept provenance, PyTorch training-loop evidence, Slurm job IDs, Dask logs, telemetry, checkpoints, model artifacts, outputs, and manifests will be preserved.

Constraints & Execution Rules:
1. Target System: OLCF Frontier (Slurm scheduler, Cray EX, AMD MI250X GPUs).
2. Resource Limits: Requested nodes <= 10 nodes; running wall time <= 30 minutes per campaign.
3. Hyperparameters: Search model sizes, learning rates, batch sizes, and data slices using a run-specific configuration generated inside `$PAL_RUN_DIR`, with fixed seeds.
4. Search Size: Run an adaptive search with up to 8 total trials: 4 seed trials covering the generated search bounds, then up to 4 expansion trials around the best seed trials. Stop earlier only if the validation-loss threshold is reached, the 30-minute wall-time budget is near, or a blocker occurs.
5. Orchestration: Submit, monitor, and manage Dask training jobs through Slurm tool calls.
6. Provenance & Instrumentation: Enable Flowcept provenance tracking, including PyTorch training loops, Slurm job IDs, Dask records, and telemetry when available.
7. Loop Goal: Evaluate trial loss vs. node-hour consumption, prune unpromising trials, expand promising regions, and record the decision rationale.
8. Do not change the scientific objective unless a blocker requires it.

Use the run manifest prepared by the human as the source of truth for run identity. Before running commands, source the absolute run environment path with:

```bash
source "$PAL_RUN_ENV"
```

Never use a relative `source run.env`, because it can load a stale run from the wrong working directory. If `$PAL_RUN_ENV` is not set or the file does not exist, stop and ask the human for the absolute run.env path.

Do not create a new manifest, and do not invent or manually rewrite campaign ids. Use exactly the same `$PAL_CAMPAIGN_ID` for the code-assistant provenance and for every Flowcept-instrumented machine-learning workflow command, including generated Slurm scripts. Generate all run-specific files inside `$PAL_RUN_DIR`. Generate the per-run search configuration at `$PAL_SEARCH_CONFIG` and the final run summary at `$PAL_RUN_SUMMARY`.

At the end, write a run summary containing:

- commands executed;
- git commit before and after;
- environment details;
- Slurm job ids, requested nodes, elapsed time, state, exit code, stdout/stderr paths, and node-hours;
- Dask scheduler/worker logs and relevant task evidence;
- node-budget, wall-time, token-budget, and validation-loss-threshold checks;
- hyperparameters and metrics for every trial;
- selected checkpoint/model artifact paths;
- telemetry/resource evidence paths;
- failures, retries, repairs, pruning decisions, expansion decisions, and plan revisions;
- final status;
- files included in the export package.

Stop after the Frontier campaign succeeds, reaches the configured stopping criteria, or after writing a clear failure note that includes the command that failed, the error, the evidence inspected, and the next recommended fix.
