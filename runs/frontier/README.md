# Frontier Run Packages

Place Frontier run directories or exported Frontier packages here after they are returned by the Frontier Codex session.

Each package should follow `docs/artifact_contract.md` and can be imported locally with:

```bash
.venv/bin/python scripts/capture/import_run.py --package-dir runs/frontier/<package> --mongo-db <local_db_name>
```
