#!/bin/bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
work="${1:-$here/work}"
if [ "$#" -gt 0 ]; then shift; fi
exec python3 "$here/port.py" run --work "$work" -- "$@"
