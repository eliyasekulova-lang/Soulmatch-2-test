#!/usr/bin/env bash
set -euo pipefail

# Build an offline wheelhouse on a networked machine, then copy it to restricted env.
# Usage:
#   ./scripts/build_wheelhouse.sh /tmp/soulmatch_wheels

OUT_DIR="${1:-/tmp/soulmatch_wheels}"
PY_BIN="${PY_BIN:-python3}"

mkdir -p "$OUT_DIR"

"$PY_BIN" -m pip install --upgrade pip wheel
"$PY_BIN" -m pip wheel -r requirements.txt -w "$OUT_DIR"

echo "[build-wheelhouse] built at: $OUT_DIR"
echo "Copy this folder to the restricted machine and run:"
echo "  ./scripts/setup_test_env.sh --wheelhouse $OUT_DIR"
