from __future__ import annotations

from .manifest import build_manifest, save_manifest
from .settings import generate_settings


def create_run(
    condition: str,
    repetition: int,
    profile: str,
    mongo_db: str | None,
    codex_jsonl: str | None,
    prompt_path: str | None,
    run_root: str | None = None,
) -> dict:
    manifest = build_manifest(
        condition,
        repetition,
        profile,
        mongo_db=mongo_db,
        codex_jsonl=codex_jsonl,
        prompt_path=prompt_path,
        run_root=run_root,
    )
    save_manifest(manifest)
    generate_settings(condition, manifest)
    return manifest
