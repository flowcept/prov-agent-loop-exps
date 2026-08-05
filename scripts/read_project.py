#!/usr/bin/env python3
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PROJECT = yaml.safe_load((ROOT / "project.yaml").read_text())


def main(argv):
    if len(argv) < 2:
        raise SystemExit("usage: read_project.py <settings_path|tutorial_root|workflow_params_json|campaign_id> [step]")
    key = argv[1]
    if key == "settings_path":
        print(PROJECT["project"]["settings_path"])
    elif key == "tutorial_root":
        print(PROJECT["project"]["tutorial_root"])
    elif key == "workflow_params_json":
        print(json.dumps(PROJECT["workflow_params"], separators=(",", ":")))
    elif key == "campaign_id":
        if len(argv) != 3:
            raise SystemExit("campaign_id requires step1 or step2")
        print(PROJECT["campaigns"][argv[2]]["campaign_id"])
    else:
        raise SystemExit(f"unknown key: {key}")


if __name__ == "__main__":
    main(sys.argv)
