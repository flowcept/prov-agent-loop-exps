# Local OPL Machine Learning Workflow Prompt

You are helping run the local smoke version of a machine-learning workflow experiment.

Human objective:

Explore model sizes, learning rates, batch sizes, data slices, and stopping criteria for Flowcept's LLM tutorial while keeping the run small enough for this local environment. The local goal is not to maximize model quality; it is to exercise the workflow loop and produce enough logs, commands, configurations, tests, evaluations, and artifacts for later analysis.

Experiment constraints:

- resource budget: use at most the local resources available in the current environment and record what was used or requested;
- wall-time budget: each campaign should stay within 30 minutes of running wall time;
- agent-token budget: keep the interaction compact and record the token usage available from Codex/Flowcept logs;
- quality criterion: define a local validation-loss threshold or proxy success criterion in the generated per-run search config, then evaluate whether the run satisfied it.

Use the experiment repository as the control directory and the Flowcept LLM tutorial as the application code. Read existing scripts and README instructions before acting. `project.yaml` and `configs/profiles/local_smoke.yaml` may be used as examples for paths and expected schema, but do not treat their hyperparameters as the experiment's fixed search space.

Use the run manifest prepared by the human as the source of truth for run identity. Before running commands, source the absolute run environment path with `source "$PAL_RUN_ENV"`. Never use a relative `source run.env`, because it can load a stale run. If `$PAL_RUN_ENV` is not set or the file does not exist, stop and ask the human for the absolute run.env path. Do not create a new manifest, and do not invent or manually rewrite campaign ids. Use exactly the same `$PAL_CAMPAIGN_ID` for the code-assistant provenance and for every Flowcept-instrumented machine-learning workflow command. Generate all run-specific files inside `$PAL_RUN_DIR`. Generate the per-run search configuration at `$PAL_SEARCH_CONFIG`.

The required structure for `$PAL_SEARCH_CONFIG` is defined in `docs/search_config_contract.md`. Choose the actual values yourself for this run.

Before executing, create a concise plan that maps plan steps to concrete work:

- code/configuration inspection;
- any required code edits or configuration changes;
- Step 1 search-workflow execution;
- Step 2 data-preparation plus search-workflow execution;
- tests or smoke validations;
- generation of a fresh per-run search configuration;
- explicit evaluation criteria for resource budget, wall time, token usage, and validation loss/proxy quality;
- evaluation of validation loss or available proxy metrics;
- search-space pruning or expansion decisions within the generated local bounds;
- log, manifest, output, and artifact preservation.

Respect these constraints:

- run only the local smoke scope: Step 1 and Step 2;
- generate a new per-run parameter/search-space file at `$PAL_SEARCH_CONFIG` before executing the workflow;
- choose the local smoke search bounds yourself, using the objective and local resource limits;
- explore model size, learning rate, batch size, data slice, and stopping criteria within the generated small grid;
- record why the selected bounds are reasonable for a local smoke run;
- keep the campaign within 30 minutes of running wall time;
- choose and record an explicit local agent-token budget before execution;
- choose and record an explicit local validation-loss threshold or proxy quality criterion before execution;
- do not add per-epoch, parent-forward, or child-layer instrumentation;
- do not change the scientific objective unless a blocker requires it.

During execution, use tool invocations to inspect code/configuration, edit files only if needed, run shell commands, execute the workflow, inspect logs, evaluate results, and revise the plan when evidence shows a failure or an unpromising trial.

Stop after Step 2 succeeds, or after writing a clear failure note that includes the failed command, observed error, evidence inspected, and next recommended fix.
