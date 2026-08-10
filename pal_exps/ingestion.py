from __future__ import annotations

import argparse
import signal
import time
from pathlib import Path

from .codex_capture import start_adapter
from .config import load_project, utc_now, write_yaml
from .manifest import load_manifest, manifest_run_dir
from .mongo import collection_names, database


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


def replay_or_watch(run_id: str, duration_sec: float, snapshot_interval_sec: float = 30.0) -> Path:
    manifest = load_manifest(run_id)
    campaign_id = manifest.get("campaign_id")
    run_path = manifest_run_dir(manifest)
    final_path = run_path / "ingestion_metrics.yaml"
    partial_path = run_path / "ingestion_metrics.partial.yaml"
    before_counts = mongo_counts(manifest["mongo_db"], campaign_id=campaign_id)
    source_stats_before = jsonl_stats(manifest.get("codex_jsonl"))
    resource_before = process_resource_snapshot()
    started = time.perf_counter()
    started_at = utc_now()
    stop_requested = False
    last_snapshot = 0.0

    def build_metrics(adapter_metrics: dict, final: bool) -> dict:
        elapsed = time.perf_counter() - started
        resource_after = process_resource_snapshot()
        after_counts = mongo_counts(manifest["mongo_db"], campaign_id=campaign_id)
        source_stats_after = jsonl_stats(manifest.get("codex_jsonl"))
        line_delta = source_stats_after["lines"] - source_stats_before["lines"]
        byte_delta = source_stats_after["bytes"] - source_stats_before["bytes"]
        inserted_delta = sum(after_counts.get(k, 0) - before_counts.get(k, 0) for k in set(before_counts) | set(after_counts))
        return {
            "run_id": manifest["run_id"],
            "condition": manifest["condition"],
            "campaign_id": manifest.get("campaign_id"),
            "mongo_db": manifest["mongo_db"],
            "codex_jsonl": manifest.get("codex_jsonl"),
            "settings_path": manifest["settings_path"],
            "started_at": started_at,
            "ended_at": utc_now() if final else None,
            "ingestion_wall_time_sec": elapsed,
            "adapter_buffer_records": adapter_metrics.get("adapter_buffer_records"),
            "adapter_elapsed_sec": adapter_metrics.get("adapter_elapsed_sec", elapsed),
            "interrupted": adapter_metrics.get("interrupted", False),
            "stopped_by_signal": adapter_metrics.get("stopped_by_signal", stop_requested),
            "final": final,
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
                "ingestion_metrics.partial.yaml is updated while the adapter is running.",
                "True per-event log-visible-to-DB-ack latency requires adapter-level timestamp instrumentation.",
            ],
        }

    def write_snapshot(adapter_metrics: dict) -> None:
        write_yaml(partial_path, build_metrics(adapter_metrics, final=False))

    def on_tick(adapter_metrics: dict) -> None:
        nonlocal last_snapshot
        now = time.perf_counter()
        if now - last_snapshot >= snapshot_interval_sec:
            last_snapshot = now
            write_snapshot(adapter_metrics)

    def request_stop(signum, _frame) -> None:
        nonlocal stop_requested
        stop_requested = True
        write_snapshot({"adapter_buffer_records": None, "adapter_elapsed_sec": time.perf_counter() - started, "stopped_by_signal": True, "signal": signum})

    previous_sigterm = signal.getsignal(signal.SIGTERM)
    previous_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    write_snapshot({"adapter_buffer_records": 0, "adapter_elapsed_sec": 0.0})
    try:
        adapter_metrics = start_adapter(
            manifest["settings_path"],
            duration_sec=duration_sec,
            campaign_id=manifest.get("campaign_id"),
            should_stop=lambda: stop_requested,
            on_tick=on_tick,
        )
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm)
        signal.signal(signal.SIGINT, previous_sigint)
    metrics = build_metrics(adapter_metrics, final=True)
    write_yaml(final_path, metrics)
    return final_path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Replay/watch a Codex JSONL through the Flowcept adapter and measure ingestion time.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--duration-sec", type=float, default=5.0)
    parser.add_argument("--snapshot-interval-sec", type=float, default=30.0)
    args = parser.parse_args(argv)
    print(replay_or_watch(args.run_id, args.duration_sec, snapshot_interval_sec=args.snapshot_interval_sec))


if __name__ == "__main__":
    main()
