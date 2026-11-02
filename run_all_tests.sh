#!/usr/bin/env bash
# Course R6 entry point. Run in an environment containing Verilator 5.050,
# make, a C++ compiler, Python 3, NumPy and Pillow. Never installs dependencies.
set -eu
repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python_command=${PYTHON:-python3}
if ! command -v "$python_command" >/dev/null 2>&1; then
    printf '%s\n' 'FAIL ENVIRONMENT_BLOCKED: Python 3 is unavailable; set PYTHON to its executable.' >&2
    exit 2
fi
exec "$python_command" "$repo_dir/tools/lib/verilator_suite.py" "$@"
