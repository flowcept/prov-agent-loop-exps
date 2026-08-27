Work directly on Frontier. The experiment environment is in:

```bash
$PAL_RUN_DIR/run.env
```

Before running anything, source `run.env` and inspect its variables:

```bash
source "$PAL_RUN_ENV"
source "$PAL_VENV/bin/activate"
```

Use the same `$PAL_CAMPAIGN_ID` for all code-assistant provenance and Flowcept-instrumented workflow stages.

Use `$PAL_VENV` for all Python/Dask/Flowcept commands. Do not switch Python environments unless this environment is missing or broken.

Use the Flowcept LLM tutorial checkout configured by the human. If `$PAL_LLM_TUTORIAL_DIR` is set, use that directory. Otherwise, locate it from the configured Flowcept checkout, commonly under:

```bash
$PAL_FLOWCEPT_ROOT/examples/llm_tutorial
```

If neither `$PAL_LLM_TUTORIAL_DIR` nor `$PAL_FLOWCEPT_ROOT` is available and the tutorial path cannot be discovered from the environment or README, stop and ask the human for the Flowcept checkout path. Do not invent an absolute path.

The Frontier project/allocation account is:

```text
GEN053
```

All Slurm jobs for this experiment must use project `GEN053` (e.g. `#SBATCH -A GEN053` or the equivalent existing Slurm option).

Use at most 200k assistant tokens for the full campaign. Keep reasoning and status messages concise, avoid broad exploratory searches, and do not run diagnostics that are not needed to execute or validate the workflow.

Before executing stages, inspect the current tutorial code, README, CLI arguments, Slurm scripts, result handling, and especially `default_exp_param_settings`.

## Hyperparameter configuration

The workflow hyperparameters are passed as a JSON STRING argument to the main Python command, not as a JSON file.

Inspect the current code to confirm the exact CLI argument, likely something such as:

```bash
--workflow-params '<JSON_STRING>'
```

Use `default_exp_param_settings` as the reference for the JSON structure and supported fields.

`max_runs` belongs inside this same JSON together with the other parameters.

For example, conceptually:

```json
{
  "emsize": [...],
  "nhid": [...],
  "nlayers": [...],
  "nhead": [...],
  "dropout": [...],
  "lr": [...],
  "epochs": 4,
  "max_runs": 80
}
```

Verify exactly how `generate_configs()` and `max_runs` behave before constructing the search space.

## Goal

Execute three adaptive hyperparameter-search stages:

```text
Stage 1: 10 nodes × 8 workers = 80 trials
Stage 2: 10 nodes × 8 workers = 80 new trials
Stage 3:  3 nodes × 8 workers = 24 new trials
```

Total target: 184 trials.

Each stage must use a separate Slurm job under project `GEN053`. Let each allocation finish and release its nodes before analyzing results and preparing the next stage.

## Walltime constraint

Each Slurm job must request NO MORE THAN 30 MINUTES.

The objective is:

```text
Stage 1: exactly 80 trials within <= 30 min
Stage 2: exactly 80 trials within <= 30 min
Stage 3: exactly 24 trials within <= 30 min
```

Before the full Stage 1, inspect the workload and, if needed, perform a small inexpensive timing test.

If trials are unlikely to finish within 30 minutes, do NOT increase the walltime or reduce the number of trials. Instead, adjust fixed workload-cost parameters such as epochs or dataset size in a controlled way while preserving the hyperparameter-search experiment.

Use `epochs=16` and `subset_size=400` as the initial fixed workload-cost defaults unless the tutorial code makes those values invalid. If Stage 1 completes much too quickly, increase only `epochs` and/or `subset_size` for later stages to use more of the 30-minute budget, but never exceed 30 minutes per Slurm job.

## Stage 1

Construct a broad, reproducible workflow-params JSON that produces exactly 80 valid, distinct configurations.

Use meaningful existing model hyperparameters such as learning rate, dropout, embedding/model size, hidden size, layers, and attention heads where supported.

Respect model constraints such as valid `emsize`/`nhead` combinations.

Prefer constructing a search space that naturally yields 80 valid configurations. If `max_runs=80` is used, first verify exactly how the implementation selects those 80 configurations.

Submit the existing Slurm workflow using:

* project/account `GEN053`;
* 10 nodes;
* 8 workers/node;
* walltime <= 30 minutes;
* Stage 1 workflow-params JSON;
* campaign ID from `$PAL_RUN_DIR/run.env`;
* the existing environment and specified virtualenv.

Record the exact JSON and Slurm job ID.

## Analyze Stage 1

After the allocation ends, inspect the actual training results and Flowcept records.

For each trial recover, where available:

* hyperparameter configuration;
* train/validation/test loss;
* training time;
* model/checkpoint ID;
* Flowcept/Dask IDs;
* success/failure status.

Use VALIDATION performance to rank configurations. Do not optimize using test loss.

You may create machine-readable analysis artifacts such as:

```text
stage1_results.json
stage1_analysis.json
```

Use the results to identify promising parameter ranges and combinations.

## Stage 2

Using Stage 1 results, construct a new workflow-params JSON representing exactly 80 NEW valid configurations.

Refine promising regions while retaining some exploration.

Ensure:

* exactly 80 trials;
* reproducibility;
* valid configurations;
* no exact duplicates from Stage 1;
* expected runtime <= 30 minutes.

Submit another `GEN053` Slurm job with:

```text
10 nodes
8 workers/node
walltime <= 30 min
```

using the same campaign ID.

After completion, analyze the combined 160 trials and create artifacts such as:

```text
stage2_results.json
combined_160_results.json
stage2_analysis.json
```

Analyze parameter sensitivity and interactions using validation performance.

## Stage 3

Using the combined first 160 trials, construct a final focused search producing exactly 24 NEW valid configurations.

Ensure:

* exactly 24 trials;
* no duplicates from previous stages;
* reproducibility;
* focus on the strongest regions found so far;
* expected runtime <= 30 minutes.

Submit under project `GEN053`:

```text
3 nodes
8 workers/node
24 workers
24 trials
walltime <= 30 min
```

using the same campaign ID.

## Final analysis

After Stage 3, analyze all 184 trials.

Select the best configuration using VALIDATION performance.

Report:

* full hyperparameter configuration;
* stage;
* train/validation/test metrics;
* training time;
* model/checkpoint identifier;
* relevant Flowcept/Dask identifiers;
* how to retrieve the winning persisted model, if available.

You may create final artifacts such as:

```text
all_184_results.json
final_analysis.json
best_model.json
```

## Execution behavior

First inspect the actual code and produce a concise execution plan. Then execute:

1. Stage 1 configuration and run
2. Stage 1 analysis
3. Stage 2 configuration and run
4. combined analysis
5. Stage 3 configuration and run
6. final ranking and best-model identification

Prefer minimal changes to the existing tutorial and Slurm/Dask implementation.

Keep a record of:

* project `GEN053`;
* campaign ID;
* exact workflow-params JSON for each stage;
* Slurm job IDs;
* analysis/result artifacts;
* final winning configuration/model.

If a stage fails, preserve completed results, diagnose the problem, make the smallest necessary fix, and avoid rerunning successful trials unnecessarily.
