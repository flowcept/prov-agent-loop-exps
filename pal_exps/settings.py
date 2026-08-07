from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import condition_config, load_project, write_yaml


def base_flowcept_settings(mongo_db: str, condition: str, codex_jsonl: str | None = None) -> dict[str, Any]:
    declared = condition == "dpl"
    codex_enabled = condition in {"opl", "dpl"}
    return {
        "flowcept_version": "1.0.3",
        "log": {"log_file_level": "disable", "log_stream_level": "error"},
        "project": {
            "dump_buffer": {"enabled": True, "path": "flowcept-buffer.jsonl", "append_id_to_path": False, "append_workflow_id_to_path": False},
            "enrich_messages": False,
            "db_flush_mode": "online",
        },
        "telemetry_capture": {},
        "instrumentation": {"enabled": True, "torch": {"what": None, "children_mode": None, "epoch_loop": None, "batch_loop": None, "capture_epochs_at_every": 1, "register_workflow": False}},
        "experiment": {},
        "mq": {"enabled": True, "type": "redis", "host": "localhost", "port": 6379, "channel": "interception", "buffer_size": 50},
        "kv_db": {"enabled": True, "host": "localhost", "port": 6379},
        "web_server": {"host": "127.0.0.1", "port": 8008, "ui_enabled": True, "max_label_length": 30},
        "sys_metadata": {"environment_id": "local"},
        "extra_metadata": {},
        "db_buffer": {"insertion_buffer_time_secs": 5, "buffer_size": 50, "remove_empty_fields": False},
        "databases": {
            "mongodb": {"enabled": True, "host": "localhost", "port": 27017, "db": mongo_db, "create_collection_index": True},
            "lmdb": {"enabled": False},
        },
        "adapters": {
            "codex": {
                "kind": "codex",
                "file_path": codex_jsonl or "codex_events.jsonl",
                "watch_interval_sec": 1,
                "recursive": True,
                "include_developer_messages": True,
                "include_reasoning": True,
                "declared_provenance_enabled": declared,
            },
            "dask": {
                "kind": "dask",
                "worker_should_get_input": True,
                "scheduler_should_get_input": True,
                "worker_should_get_output": True,
                "scheduler_create_timestamps": True,
                "worker_create_timestamps": False,
            },
        },
        "agent": {"enabled": False},
        "campaign": {"condition": condition},
        "capture": {"codex_adapter_enabled": codex_enabled, "declared_provenance_enabled": declared},
    }


def deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def generate_settings(condition: str, manifest: dict[str, Any], output_path: Path | None = None) -> Path:
    project = load_project()
    mongo = project.get("mongo", {})
    settings = base_flowcept_settings(manifest["mongo_db"], condition, manifest.get("codex_jsonl"))
    settings["databases"]["mongodb"]["host"] = mongo.get("host", "localhost")
    settings["databases"]["mongodb"]["port"] = int(mongo.get("port", 27017))
    cond = condition_config(condition)
    settings = deep_merge(settings, cond.get("flowcept_settings", {}))
    settings["campaign"] = {
        **settings.get("campaign", {}),
        "id": manifest.get("campaign_id"),
        "run_id": manifest.get("run_id"),
        "condition": condition,
        "repetition": manifest.get("repetition"),
        "profile": manifest.get("profile"),
    }
    if condition == "baseline":
        settings["capture"]["codex_adapter_enabled"] = False
    path = output_path or Path(manifest["settings_path"])
    write_yaml(path, settings)
    return path
