#!/bin/bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
exec "$here/recomp/run.sh" "$here/recomp/work" "$@"
