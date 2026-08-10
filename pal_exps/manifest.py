from __future__ import annotations

from pathlib import Path
from shlex import quote
from typing import Any

from .config import git_commit, load_project, make_run_id, profile_config, python_env, utc_now, write_text, write_yaml
from .paths import DEFAULT_RUN_ROOT, FRONTIER_RUN_ROOT, ROOT


REQUIRED_FIELDS = [
    "run_id",
    "condition",
    "repetition",
    "profile",
    "campaign_id",
    "mongo_db",
    "run_root",
    "settings_path",
    "start_time",
    "status",
]


def default_run_root_for_profile(profile: str) -> Path:
    try:
        configured = profile_config(profile).get("run_root")
        if configured:
            return Path(configured)
    except FileNotFoundError:
        pass
    return FRONTIER_RUN_ROOT if profile.startswith("frontier") else DEFAULT_RUN_ROOT


def resolve_run_root(run_root: str | Path | None, profile: str | None = None) -> Path:
    root = Path(run_root) if run_root else default_run_root_for_profile(profile or "")
    if not root.is_absolute():
        root = ROOT / root
    return root


def relative_to_repo(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def manifest_run_dir(manifest: dict[str, Any]) -> Path:
    return resolve_run_root(manifest.get("run_root"), manifest.get("profile")) / manifest["run_id"]


def build_manifest(
    condition: str,
    repetition: int,
    profile: str,
    mongo_db: str | None = None,
    codex_jsonl: str | None = None,
    prompt_path: str | None = None,
    run_id: str | None = None,
    run_root: str | None = None,
) -> dict[str, Any]:
    project = load_project()
    rid = run_id or make_run_id(condition, repetition, profile)
    db_name = mongo_db or f"pal_{rid}"
    campaign_id = f"pal:{profile}:{condition}:r{repetition}:{rid}"
    root = resolve_run_root(run_root, profile)
    rdir = root / rid
    run_root_label = relative_to_repo(root)
    return {
        "run_id": rid,
        "condition": condition,
        "repetition": repetition,
        "profile": profile,
        "campaign_id": campaign_id,
        "mongo_db": db_name,
        "run_root": run_root_label,
        "codex_jsonl": codex_jsonl,
        "settings_path": relative_to_repo(rdir / "flowcept-settings.yaml"),
        "prompt_path": prompt_path,
        "start_time": utc_now(),
        "end_time": None,
        "status": "created",
        "repo_commits": {
            "experiment_repo": git_commit(ROOT),
            "flowcept_git_url": project["project"].get("flowcept_git_url"),
            "flowcept_git_branch": project["project"].get("flowcept_git_branch"),
        },
        "constraints": {
            "max_requested_nodes": 10,
            "campaign_wall_time_minutes": 30,
            "agent_token_budget": None,
            "validation_loss_threshold": None,
        },
        "artifacts": {
            "search_config_path": relative_to_repo(rdir / "search_config.yaml"),
            "run_summary_path": relative_to_repo(rdir / "run_summary.md"),
        },
        "environment": python_env(),
        "notes": [],
    }


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    return [field for field in REQUIRED_FIELDS if not manifest.get(field)]


def save_manifest(manifest: dict[str, Any], root: Path | None = None) -> Path:
    run_path = (root / manifest["run_id"]) if root else manifest_run_dir(manifest)
    path = run_path / "manifest.yaml"
    write_yaml(path, manifest)
    save_run_env(manifest, run_path=run_path)
    return path


def save_run_env(manifest: dict[str, Any], run_path: Path | None = None) -> Path:
    resolved_run_path = run_path or manifest_run_dir(manifest)
    path = resolved_run_path / "run.env"
    settings_path = Path(str(manifest.get("settings_path")))
    if not settings_path.is_absolute():
        settings_path = ROOT / settings_path
    search_config_path = Path(str((manifest.get("artifacts") or {}).get("search_config_path")))
    if not search_config_path.is_absolute():
        search_config_path = ROOT / search_config_path
    run_summary_path = Path(str((manifest.get("artifacts") or {}).get("run_summary_path")))
    if not run_summary_path.is_absolute():
        run_summary_path = ROOT / run_summary_path
    manifest_path = resolved_run_path / "manifest.yaml"
    values = {
        "PAL_RUN_ID": manifest.get("run_id"),
        "PAL_CAMPAIGN_ID": manifest.get("campaign_id"),
        "PAL_MONGO_DB": manifest.get("mongo_db"),
        "PAL_RUN_DIR": str(resolved_run_path.resolve()),
        "PAL_RUN_ENV": str(path.resolve()),
        "PAL_MANIFEST_PATH": str(manifest_path.resolve()),
        "PAL_CODEX_JSONL": manifest.get("codex_jsonl"),
        "PAL_PROMPT_PATH": manifest.get("prompt_path"),
        "PAL_SEARCH_CONFIG": str(search_config_path.resolve()),
        "PAL_RUN_SUMMARY": str(run_summary_path.resolve()),
        "FLOWCEPT_SETTINGS_PATH": str(settings_path.resolve()),
    }
    lines = [
        "# Source this file to reuse the exact run/campaign/settings generated by create_manifest.py.",
    ]
    for key, value in values.items():
        if value is None:
            continue
        lines.append(f"export {key}={quote(str(value))}")
    write_text(path, "\n".join(lines) + "\n")
    return path


def load_manifest(path_or_run_id: str) -> dict[str, Any]:
    from .config import read_yaml

    candidate = Path(path_or_run_id)
    if candidate.exists():
        return read_yaml(candidate)
    for root in (DEFAULT_RUN_ROOT, FRONTIER_RUN_ROOT):
        path = root / path_or_run_id / "manifest.yaml"
        if path.exists():
            return read_yaml(path)
    return read_yaml(DEFAULT_RUN_ROOT / path_or_run_id / "manifest.yaml")
