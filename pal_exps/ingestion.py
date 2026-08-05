from __future__ import annotations

import argparse
import time
from pathlib import Path

from .codex_capture import start_adapter
from .config import load_project, utc_now, write_yaml
from .manifest import load_manifest
from .mongo import collection_names, database
from .paths import DEFAULT_RUN_ROOT


def jsonl_stats(path: str | None) -> dict:
    if not path:
        return {"path": None, "exists": False, "bytes": 0, "lines": 0}
    jsonl = Path(path)
    if not jsonl.exists():
        return {"path": path, "exists": False, "bytes": 0, "lines": 0}
    with jsonl.open("rb") as fh:
        lines = sum(1 for _ in fh)
    return {"path": str(jsonl), "exists": True, "bytes": jsonl.stat().st_size, "lines": lines}


def mongo_counts(db_name: str, campaign_id: str | None = None) -> dict[str, int]:
    project = load_project()
    db = database(project["mongo"], db_name)
    counts = {}
    for name in collection_names(db):
        if campaign_id and db[name].count_documents({"campaign_id": {"$exists": True}}):
            counts[name] = db[name].count_documents({"campaign_id": campaign_id})
        else:
            counts[name] = db[name].count_documents({})
    return counts


def process_resource_snapshot() -> dict:
    try:
        import psutil

        proc = psutil.Process()
        children = proc.children(recursive=True)
        processes = [proc, *children]
        rss_bytes = 0
        cpu_times_user = 0.0
        cpu_times_system = 0.0
        for item in processes:
            try:
                mem = item.memory_info()
                times = item.cpu_times()
            except psutil.Error:
                continue
            rss_bytes += mem.rss
            cpu_times_user += getattr(times, "user", 0.0)
            cpu_times_system += getattr(times, "system", 0.0)
        return {
            "rss_bytes": rss_bytes,
            "cpu_user_sec": cpu_times_user,
            "cpu_system_sec": cpu_times_system,
            "process_count": len(processes),
        }
    except Exception as exc:
        return {"error": repr(exc)}


def resource_delta(before: dict, after: dict, elapsed_sec: float) -> dict:
    if before.get("error") or after.get("error"):
        return {"error": before.get("error") or after.get("error")}
    cpu_delta = (
        after.get("cpu_user_sec", 0.0)
        + after.get("cpu_system_sec", 0.0)
        - before.get("cpu_user_sec", 0.0)
        - before.get("cpu_system_sec", 0.0)
    )
    return {
        "rss_start_bytes": before.get("rss_bytes"),
        "rss_end_bytes": after.get("rss_bytes"),
        "rss_delta_bytes": after.get("rss_bytes", 0) - before.get("rss_bytes", 0),
        "cpu_time_delta_sec": cpu_delta,
        "cpu_percent_one_core_equivalent": (cpu_delta / elapsed_sec * 100.0) if elapsed_sec else None,
        "process_count_start": before.get("process_count"),
        "process_count_end": after.get("process_count"),
    }


def replay_or_watch(run_id: str, duration_sec: float) -> Path:
    manifest = load_manifest(run_id)
    campaign_id = manifest.get("campaign_id")
    before_counts = mongo_counts(manifest["mongo_db"], campaign_id=campaign_id)
    source_stats_before = jsonl_stats(manifest.get("codex_jsonl"))
    resource_before = process_resource_snapshot()
    started = time.perf_counter()
    started_at = utc_now()
    adapter_metrics = start_adapter(
        manifest["settings_path"],
        duration_sec=duration_sec,
        campaign_id=manifest.get("campaign_id"),
    )
    elapsed = time.perf_counter() - started
    ended_at = utc_now()
    resource_after = process_resource_snapshot()
    after_counts = mongo_counts(manifest["mongo_db"], campaign_id=campaign_id)
    source_stats_after = jsonl_stats(manifest.get("codex_jsonl"))
    line_delta = source_stats_after["lines"] - source_stats_before["lines"]
    byte_delta = source_stats_after["bytes"] - source_stats_before["bytes"]
    inserted_delta = sum(after_counts.get(k, 0) - before_counts.get(k, 0) for k in set(before_counts) | set(after_counts))
    metrics = {
        "run_id": manifest["run_id"],
        "condition": manifest["condition"],
        "campaign_id": manifest.get("campaign_id"),
        "mongo_db": manifest["mongo_db"],
        "codex_jsonl": manifest.get("codex_jsonl"),
        "settings_path": manifest["settings_path"],
        "started_at": started_at,
        "ended_at": ended_at,
        "ingestion_wall_time_sec": elapsed,
        "adapter_buffer_records": adapter_metrics["adapter_buffer_records"],
        "adapter_elapsed_sec": adapter_metrics["adapter_elapsed_sec"],
        "interrupted": adapter_metrics["interrupted"],
        "source_jsonl_before": source_stats_before,
        "source_jsonl_after": source_stats_after,
        "source_jsonl_line_delta": line_delta,
        "source_jsonl_byte_delta": byte_delta,
        "mongo_counts_before": before_counts,
        "mongo_counts_after": after_counts,
        "mongo_counts_delta": {
            key: after_counts.get(key, 0) - before_counts.get(key, 0)
            for key in sorted(set(before_counts) | set(after_counts))
        },
        "mongo_inserted_delta_total": inserted_delta,
        "mongo_inserted_delta_total_filtered": inserted_delta,
        "throughput": {
            "source_lines_per_sec": (line_delta / elapsed) if elapsed else None,
            "source_bytes_per_sec": (byte_delta / elapsed) if elapsed else None,
            "mongo_records_per_sec": (inserted_delta / elapsed) if elapsed else None,
        },
        "observer_resources": resource_delta(resource_before, resource_after, elapsed),
        "notes": [
            "ingestion_wall_time_sec is process/runtime duration for this adapter run.",
            "True per-event log-visible-to-DB-ack latency requires adapter-level timestamp instrumentation.",
        ],
    }
    path = DEFAULT_RUN_ROOT / manifest["run_id"] / "ingestion_metrics.yaml"
    write_yaml(path, metrics)
    return path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Replay/watch a Codex JSONL through the Flowcept adapter and measure ingestion time.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--duration-sec", type=float, default=5.0)
    args = parser.parse_args(argv)
    print(replay_or_watch(args.run_id, args.duration_sec))


if __name__ == "__main__":
    main()
