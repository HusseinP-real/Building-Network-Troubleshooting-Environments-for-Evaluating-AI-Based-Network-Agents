#!/usr/bin/env bash
set -euo pipefail

SCENARIO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_ROOT="$(cd "$SCENARIO_DIR/../.." && pwd)"

cd "$LAB_ROOT"

echo "Injecting DNS record misconfiguration..."

python3 lab.py exec infra bash -c '
set -e

CONFIG=/etc/dnsmasq.conf
BACKUP=/tmp/kairos_dnsmasq.conf.backup

CORRECT="address=/app.enterprise.test/10.30.10.10"
WRONG="address=/app.enterprise.test/10.30.10.99"

if grep -Fxq "$WRONG" "$CONFIG"; then
    echo "Fault is already injected."
    exit 0
fi

if ! grep -Fxq "$CORRECT" "$CONFIG"; then
    echo "Unexpected DNS configuration. Injection cancelled." >&2
    exit 1
fi

cp "$CONFIG" "$BACKUP"
sed -i "s|$CORRECT|$WRONG|" "$CONFIG"

pkill -TERM dnsmasq
sleep 2
dnsmasq --conf-file="$CONFIG"

pgrep -x dnsmasq >/dev/null
grep -Fxq "$WRONG" "$CONFIG"
'

echo "DNS fault injection completed."
