# PROV-Agent-Loop Experiments

This repo contains the reusable experiment harness: environment setup, run manifests, Flowcept settings generation, Codex JSONL ingestion, Mongo export/import, metrics, and Q1-Q8 analysis scripts.

It does not contain fixed scripts for the machine-learning use case. The code assistant creates run-specific scripts, configs, logs, and summaries inside each run directory. The main protocol below is written for Frontier:

- Frontier runs: `runs/frontier/<run_id>/`
- local smoke/debug runs: `runs/local/<run_id>/`

## Services

MongoDB and Redis must be running before capture starts. It does not matter how you start them: Docker, Homebrew, system services, site modules, or Flowcept utilities are all fine.

Default local ports are configured in `project.yaml`:

- MongoDB: `localhost:27017`
- Redis: `localhost:6379`

Frontier manifests created with `--profile frontier_template` automatically generate Flowcept settings that use MongoDB and Redis at `login07`.

If needed for local/debug runs, edit `project.yaml` before creating a manifest.

One Docker option is:

```bash
docker run -d --name flowcept-mongo -p 27017:27017 mongo:7
docker run -d --name flowcept-redis -p 6379:6379 redis:7
```

## Install

Create the harness environment:

```bash
cd <prov-agent-loop-exps>
scripts/setup/create_venv.sh
```

Install Flowcept from the `agent_loop` branch separately:

```bash
git clone -b agent_loop https://github.com/valescamoura/flowcept.git ../flowcept-agent-loop
.venv/bin/python -m pip install -e "../flowcept-agent-loop[ml_dev,extras,dask,codex,telemetry]"
```

Install the provenance skill for DPL runs:

```bash
FLOWCEPT_ROOT=../flowcept-agent-loop scripts/setup/install_flowcept_skill.sh
```

Check the environment:

```bash
.venv/bin/python scripts/setup/check_environment.py
```

## Conditions

- `baseline`: workflow run assisted by Codex if desired, but with no Codex adapter ingestion and no OPL/DPL provenance. Pass `--codex-jsonl` anyway when a Codex session was used so the raw session log is preserved in the export package.
- `opl`: Codex JSONL capture with declared provenance disabled.
- `dpl`: Codex JSONL capture with declared provenance enabled. Start the Codex session with `$agent-loop-provenance`.

For paper repetitions, create a fresh Codex session and a fresh JSONL for each repetition. Replaying the same JSONL is useful for debugging the adapter, but it is not an independent repetition.

One run must use exactly one campaign id and one Mongo database:

```text
run_id -> campaign_id -> mongo_db
```

All Codex provenance, Flowcept workflow records, Dask records, metrics, checkpoints, generated scripts, and summaries for that repetition must use the same `$PAL_CAMPAIGN_ID`.

## Common Run Setup

Start a new Codex session first, because the JSONL file only exists after the session begins.

For baseline or OPL, send a small initializer:

```text
hi codex!
```

For DPL, send:

```text
Use $agent-loop-provenance in this session
```

Find the newest Codex JSONL:

```bash
find "${CODEX_HOME:-$HOME/.codex}/sessions" -type f -name 'rollout-*.jsonl' -print0 | xargs -0 ls -t | head -1
```

The condition-specific sections below show the exact `create_manifest.py` command for baseline, OPL, and DPL. They all use this shared setup before creating the manifest:

```bash
export PAL_VENV="$PWD/.venv"
export PAL_FLOWCEPT_ROOT=<path-to-flowcept-checkout>
export PAL_LLM_TUTORIAL_DIR="$PAL_FLOWCEPT_ROOT/examples/llm_tutorial"
```

For Frontier, the generated `flowcept-settings.yaml` points to MongoDB at `login07:27017` and creates a unique database name for that run.

Parameters:

- `--condition`: `baseline`, `opl`, or `dpl`.
- `--repetition`: repetition number, usually `1`, `2`, or `3`.
- `--profile`: use `frontier_template` for Frontier runs. `local_smoke` is only for desktop smoke/debug runs.
- `--codex-jsonl`: Codex session JSONL to consume.
- `--prompt-path`: prompt file used for the code-assistant run.
- `--mongo-db`: optional override. If omitted, a unique DB name is generated from the run id.
- `--run-root`: optional override. Frontier defaults to `runs/frontier`; local smoke/debug defaults to `runs/local`.

The command only creates infrastructure files:

- `runs/frontier/<run_id>/manifest.yaml`
- `runs/frontier/<run_id>/flowcept-settings.yaml`
- `runs/frontier/<run_id>/run.env`

It does not run Codex, run the ML workflow, or choose hyperparameters. The code assistant generates run-specific files later, including `$PAL_SEARCH_CONFIG`.

If `PAL_VENV`, `PAL_FLOWCEPT_ROOT`, and `PAL_LLM_TUTORIAL_DIR` are exported before creating the manifest, they are copied into `run.env` so the Codex session can find the Python environment and tutorial without hard-coded user paths. If `PAL_VENV` is omitted, it defaults to `<prov-agent-loop-exps>/.venv`.

Source the run environment and activate the exact Python environment in every terminal that will use the run variables:

```bash
source runs/frontier/<run_id>/run.env
source "$PAL_VENV/bin/activate"
```

This exports absolute paths as well as ids. Commands use variables such as `$PAL_RUN_ID`, `$PAL_CAMPAIGN_ID`, `$PAL_MONGO_DB`, `$PAL_RUN_DIR`, `$PAL_RUN_ENV`, `$PAL_VENV`, `$PAL_SEARCH_CONFIG`, and `$FLOWCEPT_SETTINGS_PATH`.

After sourcing, use this interpreter for run commands:

```bash
"$PAL_VENV/bin/python"
```

When prompting Codex, paste `prompts/frontier_handoff.md` and replace `<ABSOLUTE_RUN_ENV_PATH>` with the absolute path printed in `$PAL_RUN_ENV`. The prompt requires Codex to run:

```bash
source "<ABSOLUTE_RUN_ENV_PATH>"
source "$PAL_VENV/bin/activate"
```

Do not let the assistant use a relative `source run.env` or a different Python interpreter; those can silently load an old run or miss the installed Flowcept/experiment dependencies.

## Baseline Run

Baseline may use Codex to help execute the workflow, but it does not ingest the Codex JSONL. Only the Flowcept/Dask workflow provenance is persisted.

Create a baseline manifest:

```bash
export PAL_VENV="$PWD/.venv"
export PAL_FLOWCEPT_ROOT=<path-to-flowcept-checkout>
export PAL_LLM_TUTORIAL_DIR="$PAL_FLOWCEPT_ROOT/examples/llm_tutorial"

.venv/bin/python scripts/run/create_manifest.py \
  --condition baseline \
  --repetition 1 \
  --profile frontier_template \
  --codex-jsonl <path-to-rollout.jsonl> \
  --prompt-path prompts/frontier_handoff.md
```

Then source the run and venv:

```bash
source runs/frontier/<run_id>/run.env
source "$PAL_VENV/bin/activate"
```

Do not run `measure_ingestion.py` for baseline. Return to the same Codex session, paste the experiment prompt, and replace `<ABSOLUTE_RUN_ENV_PATH>` with the absolute `$PAL_RUN_ENV` path. The assistant must run the Flowcept/Dask workflow with the existing `$PAL_CAMPAIGN_ID` and use `$PAL_VENV/bin/python`.

When the workflow is finished, validate and export:

```bash
.venv/bin/python scripts/run/validate_run.py --run-id "$PAL_RUN_ID"
.venv/bin/python scripts/capture/export_run.py \
  --run-id "$PAL_RUN_ID" \
  --output-root exports/frontier
```

## OPL Run

OPL ingests the Codex JSONL with declared provenance disabled.

Create an OPL manifest:

```bash
export PAL_VENV="$PWD/.venv"
export PAL_FLOWCEPT_ROOT=<path-to-flowcept-checkout>
export PAL_LLM_TUTORIAL_DIR="$PAL_FLOWCEPT_ROOT/examples/llm_tutorial"

.venv/bin/python scripts/run/create_manifest.py \
  --condition opl \
  --repetition 1 \
  --profile frontier_template \
  --codex-jsonl <path-to-rollout.jsonl> \
  --prompt-path prompts/frontier_handoff.md
```

Source the run and venv:

```bash
source runs/frontier/<run_id>/run.env
source "$PAL_VENV/bin/activate"
```

Start Codex JSONL ingestion before sending the real experiment prompt:

```bash
nohup .venv/bin/python scripts/capture/measure_ingestion.py \
  --run-id "$PAL_RUN_ID" \
  --duration-sec 100000 \
  > "runs/frontier/$PAL_RUN_ID/adapter.log" 2>&1 &
echo $! > "runs/frontier/$PAL_RUN_ID/adapter.pid"
```

Return to the same Codex session, paste the experiment prompt, and replace `<ABSOLUTE_RUN_ENV_PATH>` with the absolute `$PAL_RUN_ENV` path. The assistant must use `$PAL_VENV/bin/python`.

When Codex finishes, stop ingestion and export:

```bash
kill "$(cat runs/frontier/$PAL_RUN_ID/adapter.pid)"
.venv/bin/python scripts/run/validate_run.py --run-id "$PAL_RUN_ID"
.venv/bin/python scripts/capture/export_run.py \
  --run-id "$PAL_RUN_ID" \
  --output-root exports/frontier
```

## DPL Run

DPL ingests the Codex JSONL with declared provenance enabled. Start the Codex session by explicitly enabling the provenance skill:

```text
Use $agent-loop-provenance in this session
```

Create a DPL manifest:

```bash
export PAL_VENV="$PWD/.venv"
export PAL_FLOWCEPT_ROOT=<path-to-flowcept-checkout>
export PAL_LLM_TUTORIAL_DIR="$PAL_FLOWCEPT_ROOT/examples/llm_tutorial"

.venv/bin/python scripts/run/create_manifest.py \
  --condition dpl \
  --repetition 1 \
  --profile frontier_template \
  --codex-jsonl <path-to-rollout.jsonl> \
  --prompt-path prompts/frontier_handoff.md
```

Source the run and venv:

```bash
source runs/frontier/<run_id>/run.env
source "$PAL_VENV/bin/activate"
```

Start ingestion:

```bash
nohup .venv/bin/python scripts/capture/measure_ingestion.py \
  --run-id "$PAL_RUN_ID" \
  --duration-sec 100000 \
  > "runs/frontier/$PAL_RUN_ID/adapter.log" 2>&1 &
echo $! > "runs/frontier/$PAL_RUN_ID/adapter.pid"
```

Return to the same Codex session, paste the experiment prompt, and replace `<ABSOLUTE_RUN_ENV_PATH>` with the absolute `$PAL_RUN_ENV` path. The assistant must use `$PAL_VENV/bin/python`. When Codex finishes, stop ingestion and export:

```bash
kill "$(cat runs/frontier/$PAL_RUN_ID/adapter.pid)"
.venv/bin/python scripts/run/validate_run.py --run-id "$PAL_RUN_ID"
.venv/bin/python scripts/capture/export_run.py \
  --run-id "$PAL_RUN_ID" \
  --output-root exports/frontier
```

## Ingestion Notes

For OPL/DPL, `measure_ingestion.py` starts `Flowcept(interceptors="codex", save_workflow=False, campaign_id=$PAL_CAMPAIGN_ID)` using the generated settings file. The settings use online mode, Redis/MQ, MongoDB, and the Codex adapter pointing at the JSONL from the manifest.

If `--duration-sec` expires first, it stops by itself. In both cases it writes:

```text
runs/frontier/<run_id>/ingestion_metrics.yaml
```

While it is running, it also updates:

```text
runs/frontier/<run_id>/ingestion_metrics.partial.yaml
```

That partial file is a safety snapshot for long/background runs. The final `ingestion_metrics.yaml` is still preferred for analysis because it has final counts and `ended_at`.

For local smoke/debug runs, the same command can be run in the foreground:

```bash
.venv/bin/python scripts/capture/measure_ingestion.py \
  --run-id "$PAL_RUN_ID" \
  --duration-sec 100000
```

The script handles `SIGTERM` and writes the final `ingestion_metrics.yaml`. If the process is interrupted unexpectedly, use `ingestion_metrics.partial.yaml` as the last saved snapshot. Avoid `kill -9`, because no process can save final metrics after `SIGKILL`.

## Export

For OPL/DPL, do not export while `measure_ingestion.py` is still running. Stop the foreground process with `Ctrl+C`, or stop the Frontier/background process with `kill "$(cat runs/frontier/$PAL_RUN_ID/adapter.pid)"`, then confirm `ingestion_metrics.yaml` exists. Baseline does not run `measure_ingestion.py`.

After the run is finished, validate the run identity:

```bash
.venv/bin/python scripts/run/validate_run.py --run-id "$PAL_RUN_ID"
```

This checks that the generated settings point to the manifest campaign/database and that Mongo contains records for the expected campaign. It uses the Mongo host/port from the run `flowcept-settings.yaml`, not the global defaults in `project.yaml`.

Then package the run:

```bash
.venv/bin/python scripts/capture/export_run.py --run-id "$PAL_RUN_ID"
```

By default, the export package is written under the run directory:

```text
runs/frontier/<run_id>/export/
```

To collect many runs under one parent directory without collisions, use:

```bash
.venv/bin/python scripts/capture/export_run.py \
  --run-id "$PAL_RUN_ID" \
  --output-root exports/frontier
```

That writes:

```text
exports/frontier/<run_id>/
```

It includes:

- the manifest, settings, Codex JSONL copy, ingestion metrics, and validation report;
- run-generated files such as `search_config.yaml`, `run_summary.md`, logs, scripts, and configs;
- a `run_files/` copy of the run directory, excluding the export directory itself;
- Mongo JSON dumps for the entire run database, not just a campaign-filtered subset.

The default export refuses invalid runs. Use `--allow-invalid` only to package a broken run for debugging.

## Analyze On Another Laptop

Queries and analysis do not need to run on Frontier unless you specifically want Frontier query latency. The normal workflow is:

1. Run Codex + Flowcept ingestion on the source machine.
2. Export the package.
3. Copy the export package to the analysis laptop.
4. Import into local MongoDB.
5. Run direct Mongo Q1-Q8 and metrics locally.

On the analysis laptop:

```bash
cd <prov-agent-loop-exps>
scripts/setup/create_venv.sh
.venv/bin/python -m pip install -e "../flowcept-agent-loop[ml_dev,extras,dask,codex,telemetry]"
.venv/bin/python scripts/capture/import_run.py \
  --package-dir <path-to-export> \
  --mongo-db imported_<run_id>
```

Run Q1-Q8 direct Mongo checks:

```bash
.venv/bin/python scripts/analysis/run_query_suite.py --run-id <run_id>
```

Build metrics for one run:

```bash
.venv/bin/python scripts/analysis/build_metrics.py --run-id <run_id>
```

Aggregate all registered runs available on the analysis machine:

```bash
.venv/bin/python scripts/analysis/build_metrics.py --all
```

`run_query_suite.py` runs direct Mongo queries on the machine where the Mongo database is available. It is normally run on the analysis laptop after import, not on Frontier.

Flowcept Agent natural-language prompts live in `queries/agent_prompts/`. Those are the prompts to use later for agent-based query answering against the imported database.

## Outputs

Per run:

- `manifest.yaml`: run id, condition, repetition, campaign id, DB name, JSONL path, settings path.
- `flowcept-settings.yaml`: online Flowcept config with Mongo, Redis/MQ, campaign, and Codex adapter.
- `run.env`: shell variables for the active run.
- `search_config.yaml`: generated by the code assistant during the run.
- `run_summary.md`: generated by the code assistant at the end of the run.
- `ingestion_metrics.yaml`: generated by `measure_ingestion.py`.
- `analysis/query_outputs/Q1.json` through `Q8.json`.
- `analysis/query_completeness.csv`.
- `analysis/measurement_table.csv`.
- `export/`: portable package with Mongo JSON dumps and run artifacts.

Aggregated analysis outputs:

- `runs/local/analysis/measurement_table.csv` for imported/local analysis runs
- `runs/local/analysis/condition_summary.csv` for imported/local analysis runs

## Metrics Collected By The Harness

The scripts collect metrics that are independent from Flowcept telemetry:

- Codex JSONL size and line counts.
- Adapter ingestion wall time.
- Mongo collection counts before/after ingestion.
- Inserted-record deltas filtered by campaign id.
- Source lines/sec, source bytes/sec, and Mongo records/sec.
- Observer process CPU time and RSS memory.
- Insert latency mean/p95/max when timestamps exist in the DB records.
- Direct Mongo Q1-Q8 query latency mean/p95/max.
- Token totals discoverable from persisted model-invocation metadata.
- BSON footprint and class/entity counts from persisted Mongo records.

Frontier-only evidence such as Slurm job ids, node-hours, allocation details, and site scheduler timing must be generated by the Frontier run and preserved in the run directory/package.
