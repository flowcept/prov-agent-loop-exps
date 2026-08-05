from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT_YAML = ROOT / "project.yaml"
DEFAULT_RUN_ROOT = ROOT / "runs" / "local"
