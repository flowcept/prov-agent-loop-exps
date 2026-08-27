from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from .config import load_project, read_yaml, utc_now, write_yaml
from .manifest import load_manifest, manifest_run_dir
from .mongo import collection_names, database, database_from_manifest, dump_collection, restore_collection, write_json
from .paths import DEFAULT_RUN_ROOT, ROOT
from .validation import validate_run


def _copy_file_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _copy_tree_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)


def _copy_run_files(run_path: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    ignore = shutil.ignore_patterns("export", "__pycache__", "*.pyc")
    shutil.copytree(run_path, dst, ignore=ignore)


def export_package(
    run_id: str,
    output_dir: str | None = None,
    output_root: str | None = None,
    allow_invalid: bool = False,
) -> Path:
    manifest = load_manifest(run_id)
    run_path = manifest_run_dir(manifest)
    if output_dir:
        out = Path(output_dir)
    elif output_root:
        out = Path(output_root) / manifest["run_id"]
    else:
        out = run_path / "export"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    validation = validate_run(run_id)
    write_yaml(out / "validation.yaml", validation)
    if not validation["ok"] and not allow_invalid:
        raise ValueError(
            "Run failed validation; refusing to export as a valid package. "
            f"Errors: {validation['errors']}. Use --allow-invalid to export for debugging."
        )
    write_yaml(out / "manifest.yaml", manifest)
    for name in ["flowcept-settings.yaml", "search_config.yaml", "run_summary.md", "runtime_metrics.yaml", "ingestion_metrics.yaml", "ingestion_metrics.partial.yaml"]:
        src = run_path / name
        _copy_file_if_exists(src, out / name)
    _copy_tree_if_exists(run_path / "analysis", out / "analysis")
    _copy_run_files(run_path, out / "run_files")
    if manifest.get("codex_jsonl") and Path(manifest["codex_jsonl"]).exists():
        shutil.copy2(manifest["codex_jsonl"], out / "codex.jsonl")
    db = database_from_manifest(manifest)
    mongo_dir = out / "mongo"
    for collection in collection_names(db):
        docs = dump_collection(db, collection)
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
    run_root = manifest.get("run_root")
    if run_root and Path(run_root).is_absolute():
        manifest["original_run_root"] = run_root
        manifest["run_root"] = str(DEFAULT_RUN_ROOT.relative_to(ROOT))
    write_yaml(package / "imported_manifest.yaml", manifest)
    registered_manifest: str | None = None
    if register_run:
        run_path = manifest_run_dir(manifest)
        write_yaml(run_path / "manifest.yaml", manifest)
        registered_manifest = str((run_path / "manifest.yaml").resolve())
        for name in ["flowcept-settings.yaml", "search_config.yaml", "run_summary.md", "runtime_metrics.yaml", "ingestion_metrics.yaml", "ingestion_metrics.partial.yaml"]:
            _copy_file_if_exists(package / name, run_path / name)
        _copy_tree_if_exists(package / "analysis", run_path / "analysis")
        _copy_file_if_exists(package / "codex.jsonl", run_path / "codex.jsonl")
    return {"collections": counts, "registered_manifest": registered_manifest}


def export_main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Export a run package with Mongo data and run artifacts.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--output-root", default=None, help="Export to <output-root>/<run_id>.")
    parser.add_argument("--allow-invalid", action="store_true", help="Export even if run/campaign validation fails. Use only for debugging.")
    args = parser.parse_args(argv)
    print(export_package(args.run_id, args.output_dir, output_root=args.output_root, allow_invalid=args.allow_invalid))


def import_main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Import a run package into a local Mongo database.")
    parser.add_argument("--package-dir", required=True)
    parser.add_argument("--mongo-db", required=True)
    parser.add_argument(
        "--no-register-run",
        action="store_true",
        help="Restore Mongo only; do not register a run manifest for analysis scripts.",
    )
    args = parser.parse_args(argv)
    print(
        json.dumps(
            import_package(args.package_dir, args.mongo_db, register_run=not args.no_register_run),
            indent=2,
            sort_keys=True,
        )
    )
