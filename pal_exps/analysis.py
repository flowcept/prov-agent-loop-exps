from __future__ import annotations

import argparse
import csv
import json
import time
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from .config import load_project, read_yaml, write_yaml
from .manifest import load_manifest, manifest_run_dir, validate_manifest
from .mongo import bson_size_estimate, collection_names, database
from .paths import DEFAULT_RUN_ROOT


DPL_ENTITY_TYPES = {"belief", "decision", "memory", "lesson_learned", "observation"}
REQUIRED_BY_QUERY = {
    "Q1": {"objective", "plan", "checkpoint", "model", "hyperparameter", "metric"},
    "Q2": {"plan", "plan_step", "loop_iteration", "observation", "decision"},
    "Q3": {"evaluation_criteria", "evaluation_result", "decision", "token_usage", "resource_usage"},
    "Q4": {"tool_invocation", "domain_data", "observation", "belief", "telemetry_data"},
    "Q5": {"model", "metric", "hyperparameter", "resource_usage", "token_usage"},
    "Q6": {"plan_step", "telemetry_data", "dask_task", "metric"},
    "Q7": {"human_agent", "ai_agent", "mandate", "approval", "delegation"},
    "Q8": {"observation", "belief", "memory", "lesson_learned", "plan", "decision"},
}


def entities_from_payload(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    items = payload.get("entities")
    if isinstance(items, list):
        return [e for e in items if isinstance(e, dict)]
    return []


def load_docs(manifest: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    project = load_project()
    db = database(project["mongo"], manifest["mongo_db"])
    campaign_id = manifest.get("campaign_id")
    docs = {}
    for name in collection_names(db):
        collection_docs = list(db[name].find({}, {"_id": 0}))
        if campaign_id and any("campaign_id" in doc for doc in collection_docs):
            collection_docs = [doc for doc in collection_docs if doc.get("campaign_id") == campaign_id]
        docs[name] = collection_docs
    for expected in ["workflows", "tasks", "agents", "objects"]:
        docs.setdefault(expected, [])
    return docs


def task_subtype_counts(tasks: list[dict[str, Any]]) -> Counter:
    return Counter(t.get("subtype") or t.get("type") or "unknown" for t in tasks)


def workflow_subtype_counts(workflows: list[dict[str, Any]]) -> Counter:
    return Counter(w.get("subtype") or w.get("type") or "unknown" for w in workflows)


def entity_counts(docs: dict[str, list[dict[str, Any]]]) -> Counter:
    counts: Counter = Counter()
    for collection in docs.values():
        for doc in collection:
            for side in ("used", "generated"):
                for entity in entities_from_payload(doc.get(side)):
                    counts[entity.get("type", "unknown")] += 1
    return counts


def find_token_numbers(value: Any) -> Counter:
    counts: Counter = Counter()
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).lower()
            if isinstance(item, (int, float)):
                if normalized in {"prompt_tokens", "input_tokens", "prompt"}:
                    counts["prompt_tokens"] += item
                elif normalized in {"completion_tokens", "output_tokens", "response", "response_tokens"}:
                    counts["completion_tokens"] += item
                elif normalized in {"total_tokens", "tokens"}:
                    counts["total_tokens"] += item
            else:
                counts.update(find_token_numbers(item))
    elif isinstance(value, list):
        for item in value:
            counts.update(find_token_numbers(item))
    return counts


def token_usage(docs: dict[str, list[dict[str, Any]]]) -> dict[str, float]:
    counts: Counter = Counter()
    for collection in docs.values():
        for doc in collection:
            counts.update(find_token_numbers(doc.get("custom_metadata", {})))
            counts.update(find_token_numbers(doc.get("llm_usage", {})))
    if not counts.get("total_tokens"):
        counts["total_tokens"] = counts.get("prompt_tokens", 0) + counts.get("completion_tokens", 0)
    return dict(counts)


def insertion_latency_summary(docs: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    values = []
    by_collection: dict[str, list[float]] = {}
    for collection_name, collection_docs in docs.items():
        for doc in collection_docs:
            custom = doc.get("custom_metadata") or {}
            observed = custom.get("flowcept_capture_observed_at")
            inserted = doc.get("utc_time_at_insertion")
            if observed is None or inserted is None:
                continue
            try:
                latency = float(inserted) - float(observed)
            except Exception:
                continue
            if latency < 0:
                continue
            values.append(latency)
            by_collection.setdefault(collection_name, []).append(latency)
    if not values:
        return {"latency_sample_count": 0}
    values = sorted(values)
    p95_index = min(len(values) - 1, int(round((len(values) - 1) * 0.95)))
    result: dict[str, Any] = {
        "latency_sample_count": len(values),
        "latency_mean_sec": mean(values),
        "latency_p95_sec": values[p95_index],
        "latency_max_sec": values[-1],
    }
    for collection_name, collection_values in by_collection.items():
        sorted_values = sorted(collection_values)
        idx = min(len(sorted_values) - 1, int(round((len(sorted_values) - 1) * 0.95)))
        result[f"{collection_name}_latency_sample_count"] = len(sorted_values)
        result[f"{collection_name}_latency_p95_sec"] = sorted_values[idx]
    return result


def query_latency_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    rows = []
    with path.open("r", newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                rows.append(float(row["latency_ms"]))
            except Exception:
                continue
    if not rows:
        return {}
    rows = sorted(rows)
    p95_index = min(len(rows) - 1, int(round((len(rows) - 1) * 0.95)))
    return {
        "query_latency_mean_ms": mean(rows),
        "query_latency_p95_ms": rows[p95_index],
        "query_latency_max_ms": rows[-1],
    }


def evidence_concepts(docs: dict[str, list[dict[str, Any]]]) -> set[str]:
    tasks = docs.get("tasks", [])
    workflows = docs.get("workflows", [])
    agents = docs.get("agents", [])
    entities = entity_counts(docs)
    concepts = set(entities)
    task_subtypes = task_subtype_counts(tasks)
    workflow_subtypes = workflow_subtype_counts(workflows)
    if task_subtypes.get("tool_invocation", 0):
        concepts.add("tool_invocation")
    if task_subtypes.get("loop_iteration", 0):
        concepts.add("loop_iteration")
    if task_subtypes.get("plan_step_execution", 0):
        concepts.add("plan_step")
    if task_subtypes.get("evaluation", 0):
        concepts.add("evaluation")
    if workflow_subtypes.get("execution_plan", 0):
        concepts.add("plan")
    if any((a.get("subtype") or a.get("type")) == "human" or str(a.get("agent_id", "")).startswith("human:") for a in agents):
        concepts.add("human_agent")
    if any(str(a.get("agent_id", "")).startswith("codex:") or (a.get("subtype") or a.get("type")) in {"ai_agent", "codex"} for a in agents):
        concepts.add("ai_agent")
    for task in tasks:
        metadata = task.get("custom_metadata") or {}
        if metadata.get("llm_usage") or task.get("llm_usage"):
            concepts.add("token_usage")
        if task.get("source_agent_id"):
            concepts.add("delegation")
        used = task.get("used") or {}
        generated = task.get("generated") or {}
        if any(k in used or k in generated for k in ("metrics", "metric", "score")):
            concepts.add("metric")
        if any(k in used or k in generated for k in ("hyperparameters", "hyperparameter", "params")):
            concepts.add("hyperparameter")
    return concepts


def summarize_run(run_id_or_manifest: str) -> dict[str, Any]:
    manifest = load_manifest(run_id_or_manifest)
    docs = load_docs(manifest)
    storage = {}
    for name, collection_docs in docs.items():
        storage[name] = {"count": len(collection_docs), "bson_bytes": bson_size_estimate(collection_docs)}
    summary = {
        "run_id": manifest["run_id"],
        "condition": manifest["condition"],
        "mongo_db": manifest["mongo_db"],
        "manifest_missing_fields": validate_manifest(manifest),
        "collections": storage,
        "workflow_subtypes": dict(workflow_subtype_counts(docs["workflows"])),
        "task_subtypes": dict(task_subtype_counts(docs["tasks"])),
        "entity_types": dict(entity_counts(docs)),
        "token_usage": token_usage(docs),
        "insertion_latency": insertion_latency_summary(docs),
        "evidence_concepts": sorted(evidence_concepts(docs)),
    }
    return summary


def run_q(run_id_or_manifest: str, query_id: str) -> dict[str, Any]:
    started = time.perf_counter()
    manifest = load_manifest(run_id_or_manifest)
    docs = load_docs(manifest)
    concepts = evidence_concepts(docs)
    required = REQUIRED_BY_QUERY[query_id]
    present = sorted(required & concepts)
    missing = sorted(required - concepts)
    result = {
        "query_id": query_id,
        "run_id": manifest["run_id"],
        "condition": manifest["condition"],
        "answerable": not missing,
        "present_evidence": present,
        "missing_evidence": missing,
        "workflow_count": len(docs["workflows"]),
        "task_count": len(docs["tasks"]),
        "agent_count": len(docs["agents"]),
        "entity_counts": dict(entity_counts(docs)),
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
    }
    return result


def write_query_suite(run_id_or_manifest: str, output_dir: Path | None = None) -> Path:
    manifest = load_manifest(run_id_or_manifest)
    run_path = manifest_run_dir(manifest)
    out = output_dir or run_path / "analysis" / "query_outputs"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for qid in sorted(REQUIRED_BY_QUERY):
        result = run_q(manifest["run_id"], qid)
        rows.append(result)
        (out / f"{qid}.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    with (out.parent / "query_completeness.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["query_id", "answerable", "present_evidence", "missing_evidence", "latency_ms"])
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "query_id": row["query_id"],
                "answerable": row["answerable"],
                "present_evidence": ";".join(row["present_evidence"]),
                "missing_evidence": ";".join(row["missing_evidence"]),
                "latency_ms": row["latency_ms"],
            })
    return out


def write_metrics(run_id_or_manifest: str, output_dir: Path | None = None) -> Path:
    manifest = load_manifest(run_id_or_manifest)
    run_path = manifest_run_dir(manifest)
    out = output_dir or run_path / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    summary = summarize_run(manifest["run_id"])
    runtime = read_yaml(run_path / "runtime_metrics.yaml")
    ingestion = read_yaml(run_path / "ingestion_metrics.yaml")
    if not ingestion:
        ingestion = read_yaml(run_path / "ingestion_metrics.partial.yaml")
    query_latencies = query_latency_summary(out / "query_completeness.csv")
    observer = ingestion.get("observer_resources", {})
    throughput = ingestion.get("throughput", {})
    tokens = summary.get("token_usage", {})
    insertion_latency = summary.get("insertion_latency", {})
    run_record_total = sum(item["count"] for item in summary["collections"].values())
    row = {
        "run_id": summary["run_id"],
        "condition": summary["condition"],
        "mongo_db": summary["mongo_db"],
        "workflow_count": summary["collections"]["workflows"]["count"],
        "task_count": summary["collections"]["tasks"]["count"],
        "agent_count": summary["collections"]["agents"]["count"],
        "object_count": summary["collections"]["objects"]["count"],
        "total_bson_bytes": sum(v["bson_bytes"] for v in summary["collections"].values()),
        "workflow_wall_time_sec": runtime.get("workflow_wall_time_sec"),
        "ingestion_wall_time_sec": ingestion.get("ingestion_wall_time_sec"),
        "adapter_buffer_records": ingestion.get("adapter_buffer_records"),
        "mongo_inserted_delta_total": ingestion.get("mongo_inserted_delta_total_filtered", run_record_total),
        "source_jsonl_lines": (ingestion.get("source_jsonl_after") or {}).get("lines"),
        "source_jsonl_bytes": (ingestion.get("source_jsonl_after") or {}).get("bytes"),
        "source_lines_per_sec": throughput.get("source_lines_per_sec"),
        "mongo_records_per_sec": throughput.get("mongo_records_per_sec"),
        "observer_cpu_time_delta_sec": observer.get("cpu_time_delta_sec"),
        "observer_cpu_percent_one_core_equivalent": observer.get("cpu_percent_one_core_equivalent"),
        "observer_rss_end_bytes": observer.get("rss_end_bytes"),
        "insertion_latency_sample_count": insertion_latency.get("latency_sample_count"),
        "insertion_latency_mean_sec": insertion_latency.get("latency_mean_sec"),
        "insertion_latency_p95_sec": insertion_latency.get("latency_p95_sec"),
        "insertion_latency_max_sec": insertion_latency.get("latency_max_sec"),
        "prompt_tokens": tokens.get("prompt_tokens"),
        "completion_tokens": tokens.get("completion_tokens"),
        "total_tokens": tokens.get("total_tokens"),
        "query_latency_mean_ms": query_latencies.get("query_latency_mean_ms"),
        "query_latency_p95_ms": query_latencies.get("query_latency_p95_ms"),
        "query_latency_max_ms": query_latencies.get("query_latency_max_ms"),
        "frontier_slurm_node_hours": None,
        "frontier_gpu_activity": None,
        "task_subtypes": json.dumps(summary["task_subtypes"], sort_keys=True),
        "entity_types": json.dumps(summary["entity_types"], sort_keys=True),
    }
    path = out / "measurement_table.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return path


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def numeric(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return None


def write_all_metrics(root: Path = DEFAULT_RUN_ROOT) -> Path:
    out = root / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for manifest_path in sorted(root.glob("*/manifest.yaml")):
        manifest = load_manifest(str(manifest_path))
        run_path = manifest_run_dir(manifest)
        metrics_path = run_path / "analysis" / "measurement_table.csv"
        try:
            write_metrics(manifest["run_id"])
        except Exception:
            if not metrics_path.exists():
                continue
        rows.extend(read_csv_rows(metrics_path))
    table = out / "measurement_table.csv"
    if rows:
        fieldnames = sorted({key for row in rows for key in row})
        with table.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    else:
        table.write_text("", encoding="utf-8")

    by_condition: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_condition.setdefault(row.get("condition", "unknown"), []).append(row)
    summary_rows = []
    for condition, condition_rows in sorted(by_condition.items()):
        token_values = [numeric(row.get("total_tokens")) for row in condition_rows]
        token_values = [value for value in token_values if value is not None]
        ingestion_values = [numeric(row.get("ingestion_wall_time_sec")) for row in condition_rows]
        ingestion_values = [value for value in ingestion_values if value is not None]
        bson_values = [numeric(row.get("total_bson_bytes")) for row in condition_rows]
        bson_values = [value for value in bson_values if value is not None]
        summary_rows.append({
            "condition": condition,
            "run_count": len(condition_rows),
            "mean_total_tokens": mean(token_values) if token_values else None,
            "mean_ingestion_wall_time_sec": mean(ingestion_values) if ingestion_values else None,
            "mean_total_bson_bytes": mean(bson_values) if bson_values else None,
        })

    means = {row["condition"]: row for row in summary_rows}
    opl_tokens = means.get("opl", {}).get("mean_total_tokens")
    dpl_tokens = means.get("dpl", {}).get("mean_total_tokens")
    if opl_tokens is not None and dpl_tokens is not None:
        delta = dpl_tokens - opl_tokens
        pct = (delta / opl_tokens * 100.0) if opl_tokens else None
        summary_rows.append({
            "condition": "dpl_minus_opl",
            "run_count": "",
            "mean_total_tokens": delta,
            "mean_ingestion_wall_time_sec": None,
            "mean_total_bson_bytes": None,
            "token_overhead_percent": pct,
        })

    summary_path = out / "condition_summary.csv"
    fieldnames = sorted({key for row in summary_rows for key in row}) if summary_rows else ["condition"]
    with summary_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)
    return table


def build_metrics_main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build metrics and summary files for one run.")
    parser.add_argument("--run-id", required=False)
    parser.add_argument("--all", action="store_true", help="Aggregate metrics for registered local/imported analysis runs.")
    args = parser.parse_args(argv)
    if args.all:
        print(write_all_metrics())
        return
    if not args.run_id:
        parser.error("--run-id is required unless --all is set")
    print(write_metrics(args.run_id))


def query_suite_main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run Q1-Q8 direct Mongo query checks for one run.")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    print(write_query_suite(args.run_id))
