#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   1) Offline wheelhouse install (recommended for restricted env):
#      ./scripts/setup_test_env.sh --wheelhouse /absolute/path/to/wheels
#   2) Internal mirror install:
#      PIP_INDEX_URL='https://<your-mirror>/simple' ./scripts/setup_test_env.sh
#   3) Direct PyPI (if network is open):
#      ./scripts/setup_test_env.sh

PY_BIN="${PY_BIN:-/usr/bin/python3}"
VENV_DIR="${VENV_DIR:-.venv-test}"
VENV_EXPLICIT=0
WHEELHOUSE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --python)
      PY_BIN="$2"
      shift 2
      ;;
    --venv)
      VENV_DIR="$2"
      VENV_EXPLICIT=1
      shift 2
      ;;
    --wheelhouse)
      WHEELHOUSE="$2"
      shift 2
      ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

if [[ "$VENV_EXPLICIT" -eq 0 && "$PWD" == *:* ]]; then
  VENV_DIR="/tmp/soulmatch-api-venv"
  echo "[setup-test-env] workspace path contains ':'; using absolute venv path: $VENV_DIR"
fi

if [[ "$VENV_DIR" != /* && "$PWD" == *:* ]]; then
  echo "[setup-test-env] relative venv path '$VENV_DIR' is not safe under a workspace containing ':'." >&2
  echo "[setup-test-env] pass --venv /tmp/<name> or another absolute path." >&2
  exit 2
fi

echo "[setup-test-env] python=$PY_BIN venv=$VENV_DIR"
"$PY_BIN" -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip setuptools wheel

if [[ -n "$WHEELHOUSE" ]]; then
  if [[ ! -d "$WHEELHOUSE" ]]; then
    echo "[setup-test-env] wheelhouse not found: $WHEELHOUSE" >&2
    exit 1
  fi
  echo "[setup-test-env] installing from wheelhouse: $WHEELHOUSE"
  python -m pip install --no-index --find-links "$WHEELHOUSE" -r requirements.txt
else
  echo "[setup-test-env] installing from index (PIP_INDEX_URL=${PIP_INDEX_URL:-<default>})"
  python -m pip install -r requirements.txt
fi

echo "[setup-test-env] done"
echo "[setup-test-env] run tests with:"
echo "  $VENV_DIR/bin/python -m scripts.run_identity_tests"
echo "[setup-test-env] run psychology validation with:"
echo "  $VENV_DIR/bin/python -m scripts.run_psychology_validation"
echo "[setup-test-env] inspect migration state with:"
echo "  $VENV_DIR/bin/python -m scripts.report_psychology_migration_state"
