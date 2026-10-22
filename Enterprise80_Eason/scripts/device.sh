#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "$#" -lt 2 ]; then
  echo 'Usage: scripts/device.sh DEVICE COMMAND [ARGS...]' >&2
  exit 2
fi
dev=$1
shift
refs=$(docker ps --format '{{.Names}}' | grep -E '^kathara_.*_sydr1_' || true)
ref_count=$(printf '%s\n' "$refs" | grep -c . || true)
if [ "$ref_count" -ne 1 ]; then
  echo "ERROR: sydr1 container not unique/running (found $ref_count)" >&2
  exit 1
fi
prefix=${refs%_sydr1_*}
found=$(docker ps --format '{{.Names}}' | grep -F "${prefix}_${dev}_" || true)
found_count=$(printf '%s\n' "$found" | grep -c . || true)
if [ "$found_count" -ne 1 ]; then
  echo "ERROR: $dev not unique/running in scenario $prefix (found $found_count)" >&2
  exit 1
fi
exec docker exec "$found" "$@"
