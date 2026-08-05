#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_FILE="${ROOT_DIR}/project.yaml"
export FLOWCEPT_SETTINGS_PATH="$(python3 "${ROOT_DIR}/scripts/read_project.py" settings_path)"
TUTORIAL_ROOT="$(python3 "${ROOT_DIR}/scripts/read_project.py" tutorial_root)"
CAMPAIGN_ID="$(python3 "${ROOT_DIR}/scripts/read_project.py" campaign_id step1)"
WORKFLOW_PARAMS="$(python3 "${ROOT_DIR}/scripts/read_project.py" workflow_params_json)"
RUN_DIR="${ROOT_DIR}/runs/${CAMPAIGN_ID}"
mkdir -p "${RUN_DIR}"

cd "${TUTORIAL_ROOT}"
python llm_train_campaign.py \
  --campaign-id "${CAMPAIGN_ID}" \
  --with-flowcept true \
  --with-persistence true \
  --workflow-params "${WORKFLOW_PARAMS}" \
  2>&1 | tee "${RUN_DIR}/step1.log"
