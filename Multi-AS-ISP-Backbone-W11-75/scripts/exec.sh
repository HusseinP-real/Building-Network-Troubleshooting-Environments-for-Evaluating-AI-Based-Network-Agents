#!/usr/bin/env bash
set -euo pipefail
D="$(cd "$(dirname "$0")/../lab" && pwd)"
[ "$#" -ge 2 ] || { echo "Usage: $0 DEVICE COMMAND [ARG...]"; exit 2; }
kathara exec -d "$D" "$@"
