#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pal_exps.config import profile_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or run a local condition matrix.")
    parser.add_argument("--conditions", nargs="+", default=["baseline", "opl", "dpl"])
    parser.add_argument("--profile", default="local_smoke")
    parser.add_argument("--repetitions", type=int, default=None)
    parser.add_argument("--create-only", action="store_true")
    args = parser.parse_args()
    reps = args.repetitions or int(profile_config(args.profile).get("repetitions", 3))
    failures = 0
    for condition in args.conditions:
        for repetition in range(1, reps + 1):
            real = [sys.executable, "-m", "pal_exps.local_run", "--condition", condition, "--profile", args.profile, "--repetition", str(repetition)]
            if args.create_only:
                real.append("--create-only")
            print(" ".join(real))
            result = subprocess.run(real)
            failures += int(result.returncode != 0)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
