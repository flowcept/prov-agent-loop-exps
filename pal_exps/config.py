from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .paths import DEFAULT_RUN_ROOT, PROJECT_YAML, ROOT


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_project(path: Path = PROJECT_YAML) -> dict[str, Any]:
    data = read_yaml(path)
    data.setdefault("project", {})
    data.setdefault("mongo", {})
    data.setdefault("redis", {})
    data.setdefault("experiment", {})
    return data


def condition_config(condition: str) -> dict[str, Any]:
    path = ROOT / "configs" / "conditions" / f"{condition}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Unknown condition '{condition}': {path}")
    return read_yaml(path)


def profile_config(profile: str) -> dict[str, Any]:
    path = ROOT / "configs" / "profiles" / f"{profile}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Unknown profile '{profile}': {path}")
    return read_yaml(path)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def safe_id(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in value).strip("-")


def make_run_id(condition: str, repetition: int, profile: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return safe_id(f"{stamp}-{profile}-{condition}-r{repetition}")


def git_commit(path: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return None


def python_env() -> dict[str, Any]:
    return {
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "platform": sys.platform,
        "cwd": os.getcwd(),
    }


def run_dir(run_id: str, root: Path = DEFAULT_RUN_ROOT) -> Path:
    return root / run_id
