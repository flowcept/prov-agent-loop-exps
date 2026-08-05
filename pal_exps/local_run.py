from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from .config import load_project, profile_config, read_yaml, utc_now, write_yaml
from .manifest import build_manifest, save_manifest
from .settings import deep_merge, generate_settings


def tutorial_command(manifest: dict, step: int) -> list[str]:
    project = load_project()
    tutorial_root = Path(project["project"]["tutorial_root"])
    params = dict(manifest["workflow_params"])
    profile = profile_config(manifest["profile"])
    params.update(profile.get("workflow_params", {}))
    condition = manifest["condition"]
    with_flowcept = "true"
    with_persistence = "true"
    if condition == "baseline":
        with_flowcept = "true"
        with_persistence = "true"
    return [
        sys.executable,
        str(tutorial_root / "llm_train_campaign.py"),
        "--campaign-id",
        manifest["campaign_id"],
        "--with-flowcept",
        with_flowcept,
        "--with-persistence",
        with_persistence,
        "--workflow-params",
        json.dumps(params),
    ]


def apply_step_settings(manifest: dict, step: int) -> None:
    project = load_project()
    config_key = f"step{step}"
    step_config_path = Path(project["campaigns"][config_key]["config"])
    settings_path = Path(manifest["settings_path"])
    settings = read_yaml(settings_path)
    step_config = read_yaml(step_config_path)
    settings = deep_merge(settings, step_config.get("flowcept_settings", {}))
    write_yaml(settings_path, settings)


def run_workflow(manifest: dict, step: int = 2) -> int:
    run_path = Path("runs/local") / manifest["run_id"]
    run_path.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["FLOWCEPT_SETTINGS_PATH"] = manifest["settings_path"]
    project = load_project()
    tutorial_root = Path(project["project"]["tutorial_root"])
    log_path = run_path / f"workflow_step{step}.log"
    started = time.perf_counter()
    timeout_sec = int(project.get("experiment", {}).get("local_smoke_timeout_sec", 600))
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.run(
            tutorial_command(manifest, step),
            cwd=str(tutorial_root),
            env=env,
            text=True,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=timeout_sec,
        )
    elapsed = time.perf_counter() - started
    metrics = {"workflow_wall_time_sec": elapsed, "returncode": proc.returncode, "log_path": str(log_path)}
    write_yaml(run_path / "runtime_metrics.yaml", metrics)
    return proc.returncode


def create_run(condition: str, repetition: int, profile: str, mongo_db: str | None, codex_jsonl: str | None, prompt_path: str | None) -> dict:
    manifest = build_manifest(condition, repetition, profile, mongo_db=mongo_db, codex_jsonl=codex_jsonl, prompt_path=prompt_path)
    save_manifest(manifest)
    generate_settings(condition, manifest)
    return manifest


def run_local(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Create and optionally execute a local PROV-Agent-Loop experiment run.")
    parser.add_argument("--condition", choices=["baseline", "opl", "dpl"], required=True)
    parser.add_argument("--repetition", type=int, default=1)
    parser.add_argument("--profile", default="local_smoke")
    parser.add_argument("--mongo-db", default=None)
    parser.add_argument("--codex-jsonl", default=None)
    parser.add_argument("--prompt-path", default=None)
    parser.add_argument("--step", type=int, choices=[1, 2], default=2)
    parser.add_argument("--create-only", action="store_true")
    args = parser.parse_args(argv)

    manifest = create_run(args.condition, args.repetition, args.profile, args.mongo_db, args.codex_jsonl, args.prompt_path)
    apply_step_settings(manifest, args.step)
    if args.create_only:
        manifest["status"] = "created"
    else:
        manifest["status"] = "running"
        save_manifest(manifest)
        try:
            code = run_workflow(manifest, args.step)
            manifest["status"] = "finished" if code == 0 else "failed"
        except subprocess.TimeoutExpired as exc:
            manifest["status"] = "failed"
            manifest.setdefault("notes", []).append(f"Workflow step {args.step} timed out after {exc.timeout} seconds.")
        manifest["end_time"] = utc_now()
    save_manifest(manifest)
    print(json.dumps({"run_id": manifest["run_id"], "manifest": f"runs/local/{manifest['run_id']}/manifest.yaml", "status": manifest["status"]}, indent=2))


if __name__ == "__main__":
    run_local()
