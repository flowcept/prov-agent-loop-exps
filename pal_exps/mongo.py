from __future__ import annotations

from pathlib import Path
from typing import Any

from pymongo import MongoClient

from .config import load_project, read_yaml
from .paths import ROOT


def client_from_config(mongo: dict[str, Any]) -> MongoClient:
    uri = mongo.get("uri")
    if uri:
        return MongoClient(uri, serverSelectionTimeoutMS=5000)
    return MongoClient(
        mongo.get("host", "localhost"),
        int(mongo.get("port", 27017)),
        serverSelectionTimeoutMS=5000,
    )


def database(mongo: dict[str, Any], db_name: str | None = None):
    client = client_from_config(mongo)
    client.admin.command("ping")
    return client[db_name or mongo.get("db", "flowcept")]


def mongo_config_from_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    settings_path = Path(str(manifest.get("settings_path") or ""))
    if settings_path and not settings_path.is_absolute():
        settings_path = ROOT / settings_path
    if settings_path and settings_path.exists():
        settings = read_yaml(settings_path)
        mongo = ((settings.get("databases") or {}).get("mongodb") or {}).copy()
        if mongo:
            mongo["db"] = manifest.get("mongo_db") or mongo.get("db")
            return mongo
    mongo = (load_project().get("mongo") or {}).copy()
    mongo["db"] = manifest.get("mongo_db") or mongo.get("db")
    return mongo


def database_from_manifest(manifest: dict[str, Any]):
    return database(mongo_config_from_manifest(manifest), manifest.get("mongo_db"))


def collection_names(db) -> list[str]:
    return sorted(name for name in db.list_collection_names() if not name.startswith("system."))


def dump_collection(db, collection: str, query: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    docs = list(db[collection].find(query or {}))
    for doc in docs:
        doc["_id"] = str(doc["_id"])
    return docs


def bson_size_estimate(docs: list[dict[str, Any]]) -> int:
    try:
        from bson import BSON

        return sum(len(BSON.encode(doc)) for doc in docs)
    except Exception:
        import json

        return sum(len(json.dumps(doc, default=str).encode("utf-8")) for doc in docs)


def restore_collection(db, collection: str, docs: list[dict[str, Any]], preserve_ids: bool = True) -> int:
    if not preserve_ids:
        for doc in docs:
            doc.pop("_id", None)
    db[collection].delete_many({})
    if not docs:
        return 0
    result = db[collection].insert_many(docs)
    return len(result.inserted_ids)


def write_json(path: Path, data: Any) -> None:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, default=str), encoding="utf-8")
