from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from .config import load_project, read_yaml, utc_now, write_yaml
from .manifest import load_manifest
from .mongo import collection_names, database, dump_collection, restore_collection, write_json
from .paths import DEFAULT_RUN_ROOT


def _copy_file_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _copy_tree_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)


def export_package(run_id: str, output_dir: str | None = None) -> Path:
    manifest = load_manifest(run_id)
    project = load_project()
    run_path = DEFAULT_RUN_ROOT / manifest["run_id"]
    out = Path(output_dir) if output_dir else run_path / "export"
    out.mkdir(parents=True, exist_ok=True)
    write_yaml(out / "manifest.yaml", manifest)
    for name in ["flowcept-settings.yaml", "runtime_metrics.yaml", "ingestion_metrics.yaml"]:
        src = run_path / name
        _copy_file_if_exists(src, out / name)
    _copy_tree_if_exists(run_path / "analysis", out / "analysis")
    if manifest.get("codex_jsonl") and Path(manifest["codex_jsonl"]).exists():
        shutil.copy2(manifest["codex_jsonl"], out / "codex.jsonl")
    db = database(project["mongo"], manifest["mongo_db"])
    mongo_dir = out / "mongo"
    for collection in collection_names(db):
        docs = dump_collection(db, collection)
        campaign_id = manifest.get("campaign_id")
        if campaign_id and any("campaign_id" in doc for doc in docs):
            docs = [doc for doc in docs if doc.get("campaign_id") == campaign_id]
        write_json(mongo_dir / f"{collection}.json", docs)
    return out


def import_package(package_dir: str, db_name: str, register_run: bool = True) -> dict[str, object]:
    project = load_project()
    package = Path(package_dir)
    db = database(project["mongo"], db_name)
    counts: dict[str, int] = {}
    for path in sorted((package / "mongo").glob("*.json")):
        docs = json.loads(path.read_text(encoding="utf-8"))
        counts[path.stem] = restore_collection(db, path.stem, docs, preserve_ids=True)
    manifest = read_yaml(package / "manifest.yaml")
    original_mongo_db = manifest.get("mongo_db")
    manifest["mongo_db"] = db_name
    manifest["original_mongo_db"] = original_mongo_db
    manifest["imported_as_mongo_db"] = db_name
    manifest["imported_from_package"] = str(package.resolve())
    manifest["imported_at"] = utc_now()
    write_yaml(package / "imported_manifest.yaml", manifest)
    registered_manifest: str | None = None
    if register_run:
        run_path = DEFAULT_RUN_ROOT / manifest["run_id"]
        write_yaml(run_path / "manifest.yaml", manifest)
        registered_manifest = str((run_path / "manifest.yaml").resolve())
        for name in ["flowcept-settings.yaml", "runtime_metrics.yaml", "ingestion_metrics.yaml"]:
            _copy_file_if_exists(package / name, run_path / name)
        _copy_tree_if_exists(package / "analysis", run_path / "analysis")
        _copy_file_if_exists(package / "codex.jsonl", run_path / "codex.jsonl")
    return {"collections": counts, "registered_manifest": registered_manifest}


def export_main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Export a run package with Mongo data and run artifacts.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args(argv)
    print(export_package(args.run_id, args.output_dir))


def import_main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Import a run package into a local Mongo database.")
    parser.add_argument("--package-dir", required=True)
    parser.add_argument("--mongo-db", required=True)
    parser.add_argument(
        "--no-register-run",
        action="store_true",
        help="Restore Mongo only; do not create runs/local/<run_id>/manifest.yaml for analysis scripts.",
    )
    args = parser.parse_args(argv)
    print(
        json.dumps(
            import_package(args.package_dir, args.mongo_db, register_run=not args.no_register_run),
            indent=2,
            sort_keys=True,
        )
    )
