#!/usr/bin/env bash
set -euo pipefail

FLOWCEPT_ROOT="${FLOWCEPT_ROOT:-}"
if [[ -z "${FLOWCEPT_ROOT}" ]]; then
  ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
  FLOWCEPT_ROOT="$("${PYTHON:-python3}" - "${ROOT_DIR}/project.yaml" <<'PY'
from pathlib import Path
import sys

import yaml

project = yaml.safe_load(Path(sys.argv[1]).read_text()) or {}
configured = project.get("project", {}).get("flowcept_source")
if configured and Path(configured).exists():
    print(configured)
    raise SystemExit(0)

try:
    import flowcept
except Exception:
    raise SystemExit(1)

print(Path(flowcept.__file__).resolve().parents[2])
PY
)"
fi

SOURCE_DIR="${FLOWCEPT_ROOT}/resources/skills/agent-loop-provenance"
SOURCE_SKILL="${SOURCE_DIR}/AGENT_LOOP_PROVENANCE_SKILL.md"
TARGET_DIR="${CODEX_HOME:-${HOME}/.codex}/skills/agent-loop-provenance"

if [[ ! -f "${SOURCE_SKILL}" ]]; then
  echo "Flowcept agent-loop skill not found at: ${SOURCE_SKILL}" >&2
  echo "Set FLOWCEPT_ROOT to a Flowcept checkout containing resources/skills/agent-loop-provenance." >&2
  exit 2
fi

mkdir -p "${TARGET_DIR}"
cp "${SOURCE_SKILL}" "${TARGET_DIR}/SKILL.md"
cp -R "${SOURCE_DIR}/agents" "${TARGET_DIR}/"
cp -R "${SOURCE_DIR}/references" "${TARGET_DIR}/"

echo "Installed agent-loop-provenance skill at ${TARGET_DIR}"
echo "Start a new Codex session after installing or updating the skill."
