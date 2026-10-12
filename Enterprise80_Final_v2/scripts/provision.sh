#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
LAB="topology_kathara/Enterprise80"

# macOS ships Bash 3.2: deliberately avoid commands introduced after Bash 3.2.
DEVICE_COUNT=$(find "$LAB" -maxdepth 1 -name '*.startup' | wc -l | tr -d ' ')
if [ "$DEVICE_COUNT" -ne 80 ]; then
  echo "ERROR: expected 80 startup files, found $DEVICE_COUNT" >&2
  exit 1
fi

CANDIDATES=$(docker ps --format '{{.Names}}' | grep -E '^kathara_.*_sydr1_' || true)
CANDIDATE_COUNT=$(printf '%s\n' "$CANDIDATES" | grep -c . || true)
if [ "$CANDIDATE_COUNT" -ne 1 ]; then
  echo "ERROR: expected exactly one running sydr1 container, found $CANDIDATE_COUNT" >&2
  printf '%s\n' "$CANDIDATES" >&2
  exit 1
fi
PREFIX=${CANDIDATES%_sydr1_*}

container_for() {
  device=$1
  matches=$(docker ps --format '{{.Names}}' | grep -F "${PREFIX}_${device}_" || true)
  count=$(printf '%s\n' "$matches" | grep -c . || true)
  if [ "$count" -ne 1 ]; then
    echo "ERROR: expected one running $device in scenario $PREFIX, found $count" >&2
    return 1
  fi
  printf '%s\n' "$matches"
}

find "$LAB" -maxdepth 1 -name '*.startup' -print | sort | while IFS= read -r startup; do
  dev=$(basename "$startup" .startup)
  c=$(container_for "$dev") || exit 1
  echo "[CONFIG] $dev"
  docker exec -i "$c" bash -se < "$startup"
done

echo "[CONFIG] complete: 80 devices provisioned. Allow OSPF to converge before verification."
