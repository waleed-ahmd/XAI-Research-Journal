#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PYTHON_BIN="$ROOT/harness/.venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then PYTHON_BIN=python3; fi
export PYTHONPATH="$ROOT/harness/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$PYTHON_BIN" -m harness.historical --repo "$ROOT" "$@"
