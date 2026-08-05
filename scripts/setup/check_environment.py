#!/usr/bin/env python3
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def check_import(name: str) -> dict:
    try:
        mod = importlib.import_module(name)
        return {"ok": True, "module": name, "file": getattr(mod, "__file__", None)}
    except Exception as exc:
        return {"ok": False, "module": name, "error": repr(exc)}


def main() -> int:
    try:
        import yaml
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"PyYAML is not installed: {exc}", "hint": "Run scripts/setup/create_venv.sh first."}, indent=2))
        return 2
    try:
        from pymongo import MongoClient
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"pymongo is not installed: {exc}", "hint": "Run scripts/setup/create_venv.sh first."}, indent=2))
        return 2
    project = yaml.safe_load((ROOT / "project.yaml").read_text()) or {}
    mongo = project.get("mongo", {})
    result = {
        "python": sys.version,
        "executable": sys.executable,
        "imports": [check_import(name) for name in ["flowcept", "pymongo", "yaml", "pandas", "pyarrow", "psutil"]],
        "mongo": {"ok": False, "host": mongo.get("host", "localhost"), "port": mongo.get("port", 27017)},
        "redis": {"ok": False, "host": "localhost", "port": 6379},
        "tutorial_root_exists": Path(project.get("project", {}).get("tutorial_root", "")).exists(),
    }
    try:
        client = MongoClient(mongo.get("host", "localhost"), int(mongo.get("port", 27017)), serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        result["mongo"]["ok"] = True
    except Exception as exc:
        result["mongo"]["error"] = repr(exc)
    try:
        import redis

        redis.Redis(host="localhost", port=6379, socket_connect_timeout=2).ping()
        result["redis"]["ok"] = True
    except Exception as exc:
        result["redis"]["error"] = repr(exc)
    print(json.dumps(result, indent=2, sort_keys=True))
    ok = result["mongo"]["ok"] and result["redis"]["ok"] and result["tutorial_root_exists"] and all(item["ok"] for item in result["imports"])
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
