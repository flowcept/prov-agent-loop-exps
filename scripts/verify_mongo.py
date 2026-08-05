#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

import yaml
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
PROJECT = yaml.safe_load((ROOT / "project.yaml").read_text())


def compact_doc(doc):
    return {k: doc.get(k) for k in ("workflow_id", "task_id", "name", "type", "subtype", "campaign_id", "parent_workflow_id", "workflow_id") if k in doc}


def main():
    parser = argparse.ArgumentParser(description="Verify Flowcept Mongo persistence for a local LLM tutorial campaign.")
    parser.add_argument("--step", choices=["step1", "step2"], required=True)
    parser.add_argument("--campaign-id", default=None)
    parser.add_argument("--mongo-db", default=None)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON only.")
    args = parser.parse_args()

    campaign_id = args.campaign_id or PROJECT["campaigns"][args.step]["campaign_id"]
    expected = yaml.safe_load((ROOT / PROJECT["campaigns"][args.step]["config"]).read_text())["workflow"]
    mongo = PROJECT["mongo"]

    client = MongoClient(mongo["host"], int(mongo["port"]), serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    mongo_db = args.mongo_db or mongo["db"]
    db = client[mongo_db]

    workflows = list(db[mongo["collections"]["workflows"]].find({"campaign_id": campaign_id}, {"_id": 0}))
    workflow_ids = [w.get("workflow_id") for w in workflows if w.get("workflow_id")]
    tasks = list(db[mongo["collections"]["tasks"]].find({"workflow_id": {"$in": workflow_ids}}, {"_id": 0})) if workflow_ids else []
    objects = list(db[mongo["collections"]["objects"]].find({"workflow_id": {"$in": workflow_ids}}, {"_id": 0})) if workflow_ids else []
    workflow_names = sorted({w.get("name") for w in workflows if w.get("name")})

    missing = [name for name in expected["expected_workflows"] if name not in workflow_names]
    ok = not missing and len(tasks) >= int(expected["min_tasks"])
    result = {
        "ok": ok,
        "step": args.step,
        "campaign_id": campaign_id,
        "mongo_db": mongo_db,
        "workflow_count": len(workflows),
        "task_count": len(tasks),
        "object_count": len(objects),
        "workflow_names": workflow_names,
        "workflow_ids": workflow_ids,
        "missing_expected_workflows": missing,
        "sample_workflows": [compact_doc(w) for w in workflows[:5]],
        "sample_tasks": [compact_doc(t) for t in tasks[:5]],
    }

    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if ok else 2)


if __name__ == "__main__":
    main()
