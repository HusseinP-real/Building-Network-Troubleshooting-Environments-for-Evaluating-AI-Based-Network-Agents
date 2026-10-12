#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
./scripts/verify_healthy.sh >/dev/null || { echo 'ERROR: healthy baseline must pass before injection' >&2; exit 1; }
echo 'Stopping ospfd on sydr1, leaving interfaces UP'
# Stop FRR watchdog first, otherwise it may immediately respawn ospfd.
./scripts/device.sh sydr1 pkill -x watchfrr
./scripts/device.sh sydr1 pkill -x ospfd
sleep 55
echo 'Injection complete; run scripts/verify_fault.sh'
