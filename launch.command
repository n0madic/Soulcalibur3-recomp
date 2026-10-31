#!/bin/bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$here/recomp/port.py" run --work "$here/recomp/work" -- "$@"
