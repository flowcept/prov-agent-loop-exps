from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pal_exps.analysis import REQUIRED_BY_QUERY, run_q


QUERY_DESCRIPTIONS = {
    "Q1": "Reproduce the selected trained model end to end.",
    "Q2": "Explain plan evolution and execution divergence.",
    "Q3": "Verify constraints and stop/continue decisions.",
    "Q4": "Diagnose a failed or degraded training trial.",
    "Q5": "Find effort-quality Pareto candidates.",
    "Q6": "Locate resource bottlenecks and assess optimization.",
    "Q7": "Audit human authorization, delegation, and attribution.",
    "Q8": "Measure reuse of provenance-backed knowledge across sessions.",
}


def execute_query(query_id: str, run_id: str) -> dict[str, Any]:
    result = run_q(run_id, query_id)
    result["description"] = QUERY_DESCRIPTIONS[query_id]
    result["required_evidence"] = sorted(REQUIRED_BY_QUERY[query_id])
    return result


def main(query_id: str, argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=QUERY_DESCRIPTIONS[query_id])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", default=None)
    args = parser.parse_args(argv)
    result = execute_query(query_id, args.run_id)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)
