#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pal_exps.local_run import create_run


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a run manifest and Flowcept settings without executing the workflow.")
    parser.add_argument("--condition", choices=["baseline", "opl", "dpl"], required=True)
    parser.add_argument("--repetition", type=int, default=1)
    parser.add_argument("--profile", default="local_smoke")
    parser.add_argument("--mongo-db", default=None)
    parser.add_argument("--codex-jsonl", default=None)
    parser.add_argument("--prompt-path", default=None)
    args = parser.parse_args()
    manifest = create_run(args.condition, args.repetition, args.profile, args.mongo_db, args.codex_jsonl, args.prompt_path)
    print(json.dumps({"run_id": manifest["run_id"], "manifest": f"runs/local/{manifest['run_id']}/manifest.yaml", "settings": manifest["settings_path"]}, indent=2))


if __name__ == "__main__":
    main()
