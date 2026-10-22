#!/usr/bin/env bash
set -euo pipefail

SCENARIO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_ROOT="$(cd "$SCENARIO_DIR/../.." && pwd)"

cd "$LAB_ROOT"

echo "Repairing DNS record misconfiguration..."

python3 lab.py exec infra bash -c '
set -e

CONFIG=/etc/dnsmasq.conf
BACKUP=/tmp/kairos_dnsmasq.conf.backup

CORRECT="address=/app.enterprise.test/10.30.10.10"
WRONG="address=/app.enterprise.test/10.30.10.99"

if grep -Fxq "$CORRECT" "$CONFIG"; then
    echo "DNS record is already correct."
elif grep -Fxq "$WRONG" "$CONFIG"; then
    if [ -f "$BACKUP" ] && grep -Fxq "$CORRECT" "$BACKUP"; then
        cp "$BACKUP" "$CONFIG"
    else
        sed -i "s|$WRONG|$CORRECT|" "$CONFIG"
    fi
else
    echo "Unexpected DNS configuration. Repair cancelled." >&2
    exit 1
fi

if pgrep -x dnsmasq >/dev/null; then
    pkill -TERM dnsmasq
fi

sleep 2
dnsmasq --conf-file="$CONFIG"

grep -Fxq "$CORRECT" "$CONFIG"
pgrep -x dnsmasq >/dev/null
'

echo "DNS recovery completed."
