#!/usr/bin/env python3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pal_exps.local_run import run_local


if __name__ == "__main__":
    run_local()
