# Run Artifact Contract

Every run package should contain:

- `manifest.yaml`
- `flowcept-settings.yaml`
- `mongo/*.json`
- `codex.jsonl` for OPL and DPL
- workflow stdout/stderr logs
- adapter logs or ingestion metrics
- observer CPU/memory and throughput metrics when generated locally
- Slurm stdout/stderr for Frontier runs
- Slurm/node-hour/telemetry summaries for Frontier runs
- metrics and query outputs when already generated

The standard exporter is:

```bash
.venv/bin/python scripts/capture/export_run.py --run-id <run_id>
```

`scripts/capture/export_mongo.py` is an explicit alias for the same package export. It exports Mongo collections plus the run artifacts needed to reproduce direct query results on another machine.

The standard importer is:

```bash
.venv/bin/python scripts/capture/import_run.py --package-dir /path/to/export --mongo-db imported_<run_id>
```

By default, import restores Mongo and writes `runs/local/<run_id>/manifest.yaml` with the imported Mongo database name, so `run_query_suite.py --run-id <run_id>` and `build_metrics.py --run-id <run_id>` work on the target machine.

The manifest must include:

- `run_id`
- `condition`
- `repetition`
- `profile`
- `campaign_id`
- `mongo_db`
- `codex_jsonl`
- `settings_path`
- `prompt_path`
- `start_time`
- `end_time`
- `status`
- `repo_commits`
- `workflow_params`
- `search_bounds`
- `environment`
- `notes`

Mongo exports must preserve workflow ids, task ids, campaign ids, agent ids, parent ids, timestamps, used/generated entity payloads, and UI compatibility fields.
