#!/usr/bin/env bash
# run.sh — bootstrap .venv if needed, then launch the pycable GUI.
#
# Usage (from either dev or public tree):
#   cd <cpp>/cable/gui           # dev tree
#   cd ~/CableDynamics/cable/gui # public tree
#   ./run.sh
#
# Prerequisites: Python 3.12 (`brew install python@3.12`) and the cable_solver
# binary built either at <cpp>/cable/build_solver/cable_solver (dev) or
# ~/CableDynamics/build/cable_solver (public). solver_discovery.py finds
# either automatically.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3.12}"
VENV_DIR="${VENV_DIR:-$SCRIPT_DIR/.venv}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "error: $PYTHON_BIN not found on PATH." >&2
  echo "install it via:   brew install python@3.12" >&2
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "[run.sh] creating venv at $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

if ! python -c "import pycable" 2>/dev/null; then
  echo "[run.sh] installing pycable in editable mode"
  pip install --upgrade pip
  pip install -e .
fi

# Sanity-check the C++ binary. Warn but don't fail — the GUI can still show
# parameters; errors will surface when the user hits Run.
python - <<'PY' || true
from pycable.solver_discovery import find_cable_solver, CableSolverNotFound
try:
    path = find_cable_solver(must_exist=True)
    print(f"[run.sh] cable_solver = {path}")
except CableSolverNotFound as e:
    print(f"[run.sh] WARNING: {e}")
PY

exec python -m pycable
