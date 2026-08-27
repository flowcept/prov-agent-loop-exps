from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from .config import write_yaml
from .manifest import load_manifest, manifest_run_dir
from .mongo import collection_names, database_from_manifest


CAMPAIGN_RE = re.compile(r"pal:[A-Za-z0-9_.:-]+")


def campaigns_in_codex_jsonl(path: str | None) -> Counter[str]:
    counts: Counter[str] = Counter()
    if not path:
        return counts
    jsonl = Path(path)
    if not jsonl.exists():
        return counts
    with jsonl.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            counts.update(CAMPAIGN_RE.findall(line))
    return counts


def campaigns_in_db(manifest: dict[str, Any]) -> dict[str, Counter[str]]:
    db = database_from_manifest(manifest)
    result: dict[str, Counter[str]] = {}
    for collection in collection_names(db):
        counter: Counter[str] = Counter()
        for item in db[collection].aggregate(
            [
                {"$match": {"campaign_id": {"$exists": True, "$ne": None}}},
                {"$group": {"_id": "$campaign_id", "count": {"$sum": 1}}},
            ]
        ):
            counter[str(item["_id"])] = int(item["count"])
        result[collection] = counter
    return result


def validate_run(run_id_or_manifest: str) -> dict[str, Any]:
    manifest = load_manifest(run_id_or_manifest)
    expected = manifest.get("campaign_id")
    settings_path = Path(str(manifest.get("settings_path")))
    if not settings_path.is_absolute():
        from .paths import ROOT

        settings_path = ROOT / settings_path
    settings: dict[str, Any] = {}
    if settings_path.exists():
        settings = yaml.safe_load(settings_path.read_text(encoding="utf-8")) or {}
    jsonl_campaigns = campaigns_in_codex_jsonl(manifest.get("codex_jsonl"))
    db_campaigns = campaigns_in_db(manifest)
    db_all = Counter()
    for counter in db_campaigns.values():
        db_all.update(counter)

    errors: list[str] = []
    warnings: list[str] = []
    if not expected:
        errors.append("manifest_missing_campaign_id")
    settings_campaign = (settings.get("campaign") or {}).get("id")
    settings_db = ((settings.get("databases") or {}).get("mongodb") or {}).get("db")
    if settings_path.exists():
        if settings_campaign != expected:
            errors.append("settings_campaign_id_mismatch")
        if settings_db != manifest.get("mongo_db"):
            errors.append("settings_mongo_db_mismatch")
    else:
        errors.append("missing_settings_file")
    unexpected_jsonl = sorted(c for c in jsonl_campaigns if c != expected)
    if unexpected_jsonl:
        errors.append("codex_jsonl_mentions_other_campaign_ids")
    if expected and jsonl_campaigns and expected not in jsonl_campaigns:
        warnings.append("codex_jsonl_does_not_mention_manifest_campaign_id")
    unexpected_db = sorted(c for c in db_all if c != expected)
    if unexpected_db:
        errors.append("mongo_db_contains_other_campaign_ids")
    if expected and db_all and expected not in db_all:
        errors.append("mongo_db_has_no_records_for_manifest_campaign_id")

    run_path = manifest_run_dir(manifest)
    for required_file in ["manifest.yaml", "flowcept-settings.yaml", "run.env"]:
        if not (run_path / required_file).exists():
            errors.append(f"missing_run_file:{required_file}")
    if manifest.get("condition") in {"opl", "dpl"} and not manifest.get("codex_jsonl"):
        errors.append("missing_codex_jsonl")

    return {
        "ok": not errors,
        "run_id": manifest.get("run_id"),
        "condition": manifest.get("condition"),
        "campaign_id": expected,
        "mongo_db": manifest.get("mongo_db"),
        "settings_path": str(settings_path),
        "settings_campaign_id": settings_campaign,
        "settings_mongo_db": settings_db,
        "codex_jsonl_campaigns": dict(jsonl_campaigns),
        "mongo_campaigns_by_collection": {key: dict(value) for key, value in db_campaigns.items()},
        "errors": errors,
        "warnings": warnings,
    }


def validate_main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Validate run/campaign identity before export or analysis.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", default=None)
    args = parser.parse_args(argv)
    result = validate_run(args.run_id)
    if args.output:
        write_yaml(Path(args.output), result)
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["ok"]:
        raise SystemExit(2)
