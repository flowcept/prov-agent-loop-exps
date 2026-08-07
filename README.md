# PROV-Agent-Loop Experiments

This repository contains the local experiment harness for the paper evaluation. It prepares Flowcept settings, run manifests, Codex JSONL capture/replay, Mongo export/import, metrics, and the Q1-Q8 query suite.

The ML use case is Flowcept's LLM tutorial, but the experiment has two scales:

- `local_smoke`: run only through tutorial Step 2 to validate the harness, adapter, skill, Mongo persistence, export/import, and Q1-Q8 scripts.
- `frontier_validation`: run the training campaign described in the paper, including Dask data preparation, model training, fixed seeds/search bounds, validation metrics/losses, checkpoints or model artifacts, telemetry, and Slurm/node-hour evidence.

Per-epoch/model-forward/child-layer instrumentation may stay reduced in local smoke, but Frontier validation must produce enough ML, scheduler, resource, and telemetry evidence to answer the paper queries.

## Setup

Start the external services required by Flowcept before running the harness:

- MongoDB at `localhost:27017`.
- Redis at `localhost:6379`.

If your Flowcept settings define service binaries, use the Flowcept CLI:

```bash
flowcept --start-redis
flowcept --start-mongo
flowcept --check-services
```

`flowcept --start-services` is not currently the path used here because the Flowcept command is a placeholder. If MongoDB/Redis are already managed by Docker, Homebrew, modules, or a site service manager, start them with that mechanism and then run:

```bash
flowcept --check-services
```

For a local Docker-based fallback, one possible option is:

```bash
docker run -d --name flowcept-mongo -p 27017:27017 mongo:7
docker run -d --name flowcept-redis -p 6379:6379 redis:7
```

If the services already exist, start them instead of creating new containers.

```bash
cd <prov-agent-loop-exps>
scripts/setup/create_venv.sh
.venv/bin/python scripts/setup/check_environment.py
```

The primary environment is `.venv` from `pyproject.toml`. Conda is optional. `check_environment.py` verifies Python imports, MongoDB, Redis, and the tutorial path.

Install the Flowcept provenance skill before DPL runs:

```bash
.venv/bin/python -m pip install -e .
scripts/setup/install_flowcept_skill.sh
```

The script copies the canonical skill from Flowcept's `resources/skills/agent-loop-provenance` directory into `~/.codex/skills/agent-loop-provenance/SKILL.md`. Start a new Codex session after installing or updating the skill.

## Conditions

- `baseline`: script-only ML workflow execution; no Codex provenance capture.
- `opl`: Codex adapter consumes JSONL with declared provenance disabled.
- `dpl`: Codex adapter consumes JSONL with declared provenance enabled; use the provenance skill in the Codex session.

## Local Smoke

Local smoke is intentionally small. It should run only:

- Step 1: Search workflow.
- Step 2: Data preparation plus search workflow.

This is not the full paper validation; it is the local check that provenance capture and analysis are wired correctly.

## Running Codex Sessions

For OPL and DPL, each experimental repetition must use a fresh Codex session and therefore a fresh Codex JSONL. Replaying the same JSONL multiple times is useful for adapter debugging, but it is not a paper repetition because it does not expose agent nondeterminism.

Paper-aligned repetitions:

- `repetition 1`: Codex session 1, JSONL 1, run manifest 1.
- `repetition 2`: Codex session 2, JSONL 2, run manifest 2.
- `repetition 3`: Codex session 3, JSONL 3, run manifest 3.

The Codex session JSONL is created only after the session starts. You can handle this in two ways.

### Replay After The Session Ends

This is the simplest local workflow. Run the Codex session first, then consume its JSONL afterward.

Start an OPL session:

```bash
codex "$(cat prompts/codex_opl.md)"
```

Start a DPL session after installing the skill:

```bash
codex "$(cat prompts/codex_dpl.md)"
```

Find the newest Codex session JSONL:

```bash
find "${CODEX_HOME:-$HOME/.codex}/sessions" -type f -name 'rollout-*.jsonl' -print0 | xargs -0 ls -t | head -1
```

Then create a run manifest and settings pointing at that JSONL:

```bash
.venv/bin/python scripts/run/create_manifest.py --condition dpl --repetition 1 --profile local_smoke --codex-jsonl /path/to/codex.jsonl
```

The command above does not run Codex, the workflow, or the adapter. It only creates:

- `runs/local/<run_id>/manifest.yaml`
- `runs/local/<run_id>/flowcept-settings.yaml`
- `runs/local/<run_id>/run.env`

Load the generated run variables instead of copying ids manually:

```bash
source runs/local/<run_id>/run.env
```

Consume the JSONL with the adapter:

```bash
.venv/bin/python scripts/capture/measure_ingestion.py --run-id "$PAL_RUN_ID" --duration-sec 5
```

This command starts the Flowcept Codex adapter using `runs/local/<run_id>/flowcept-settings.yaml`.
It consumes the configured Codex JSONL and writes the generated provenance records to the Mongo database named in `runs/local/<run_id>/manifest.yaml`.
It also writes `runs/local/<run_id>/ingestion_metrics.yaml`.

### Online Capture While Codex Runs

Use this when you want to measure ingestion while the session is still active.

First create the Codex session with a minimal prompt:

```bash
codex 'Use $agent-loop-provenance in this session'
```

In another terminal, find the newly created JSONL:

```bash
find "${CODEX_HOME:-$HOME/.codex}/sessions" -type f -name 'rollout-*.jsonl' -print0 | xargs -0 ls -t | head -1
```

Create the run manifest/settings with that JSONL, then start the adapter for a longer window:

```bash
.venv/bin/python scripts/run/create_manifest.py --condition dpl --repetition 1 --profile local_smoke --codex-jsonl /path/to/new/session.jsonl
source runs/local/<run_id>/run.env
.venv/bin/python scripts/capture/measure_ingestion.py --run-id "$PAL_RUN_ID" --duration-sec 100000
```

Return to the same Codex session and send the real experiment prompt from `prompts/codex_dpl.md`.

Run baseline locally:

```bash
.venv/bin/python scripts/run/run_local.py --condition baseline --repetition 1 --profile local_smoke
```

Replay or watch a Codex JSONL for OPL/DPL after creating the run:

```bash
.venv/bin/python scripts/capture/measure_ingestion.py --run-id <run_id> --duration-sec 5
```

Build query outputs and metrics:

```bash
.venv/bin/python scripts/analysis/run_query_suite.py --run-id "$PAL_RUN_ID"
.venv/bin/python scripts/analysis/build_metrics.py --run-id "$PAL_RUN_ID"
.venv/bin/python scripts/analysis/build_metrics.py --all
```

Export a run package, including the Mongo database collections:

```bash
.venv/bin/python scripts/capture/export_run.py --run-id "$PAL_RUN_ID"
```

`scripts/capture/export_mongo.py` is an explicit alias for the same run package export. The package is written to `runs/local/<run_id>/export/` and contains:

- `mongo/*.json`, one JSON dump per Mongo collection.
- `manifest.yaml`, `flowcept-settings.yaml`, Codex JSONL, and ingestion/runtime metrics when available.
- `analysis/` with query outputs and metrics if they were already generated before export.

## Moving A Run To Another Laptop

You can run the direct Mongo queries and later Flowcept Agent queries on another laptop, as long as that laptop has MongoDB and this experiment repo.

On the source machine, after ingestion and analysis:

```bash
.venv/bin/python scripts/capture/export_run.py --run-id <run_id>
```

Copy `runs/local/<run_id>/export/` to the target laptop.

On the target laptop:

```bash
cd <prov-agent-loop-exps>
scripts/setup/create_venv.sh
.venv/bin/python scripts/setup/check_environment.py
.venv/bin/python scripts/capture/import_run.py --package-dir /path/to/export --mongo-db imported_<run_id>
```

The import command restores the Mongo collections and registers `runs/local/<run_id>/manifest.yaml` with the imported database name, so the analysis scripts can run by `run_id`:

```bash
.venv/bin/python scripts/analysis/run_query_suite.py --run-id <run_id>
.venv/bin/python scripts/analysis/build_metrics.py --run-id <run_id>
```

For Flowcept Agent queries on another laptop, import the package first, then point the Flowcept/agent configuration at the imported Mongo database and use the prompts in `queries/agent_prompts/`.

## Outputs

Each run writes to `runs/local/<run_id>/`:

- `manifest.yaml`
- `flowcept-settings.yaml`
- `runtime_metrics.yaml` when the workflow runner is used
- `ingestion_metrics.yaml` when Codex JSONL capture/replay is used
- `analysis/measurement_table.csv`
- `analysis/query_completeness.csv`
- `analysis/query_outputs/Q1.json` through `Q8.json`
- `export/` with Mongo collections and run artifacts

Aggregated outputs across all local runs are written to:

- `runs/local/analysis/measurement_table.csv`
- `runs/local/analysis/condition_summary.csv`

## Local Metrics Collected

The local harness records the metrics that can be measured without Frontier access:

- Codex JSONL size and line count before/after ingestion.
- Adapter runtime and interruption status.
- Mongo collection counts before/after ingestion and inserted-record deltas.
- Approximate ingestion throughput in source lines/sec, bytes/sec, and Mongo records/sec.
- Observer process CPU time and RSS memory before/after adapter execution.
- Adapter-observed-to-DB-insert latency mean/p95/max when the Flowcept Codex adapter records `custom_metadata.flowcept_capture_observed_at` and the DB consumer records `utc_time_at_insertion`.
- Direct Mongo Q1-Q8 query latency summary after `run_query_suite.py`.
- Token totals discoverable from persisted model-invocation metadata.
- OPL vs DPL mean token overhead when both conditions have metrics.
- BSON footprint and class/entity counts from persisted Mongo records.

Frontier-only metrics such as Slurm node-hours, job states, allocation-level telemetry, and GPU activity are left as missing values locally and must be filled by the Frontier run package.

## Frontier

Install Flowcept's `resources/skills/agent-loop-provenance` into the Frontier Codex environment before DPL runs. Then use `prompts/frontier_handoff.md` in the Frontier Codex session.

Frontier should not stop at Step 2. It should run the full validation-scale campaign described in the paper: Dask data preparation and training, fixed seeds/search bounds, validation metrics/losses, checkpoints or model artifacts, Slurm job records, requested nodes, elapsed time/node-hours, and telemetry. It should run the same baseline/OPL/DPL capture conditions, then export the package described in `docs/artifact_contract.md`.
