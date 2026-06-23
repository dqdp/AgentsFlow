#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
AGENTSFLOW_UPSTREAM="${PROJECT_ROOT}/.agentsflow/upstream"
RUN_DIR="${PROJECT_ROOT}/Docs/agentsflow/runs/2026-06-17-add-calculator"

cd "${PROJECT_ROOT}"
PYTHONPATH=src python3 -m pytest tests
python3 "${AGENTSFLOW_UPSTREAM}/scripts/bdd_binding_check.py" \
  --bindings "${RUN_DIR}/behavior.bindings.yaml"
