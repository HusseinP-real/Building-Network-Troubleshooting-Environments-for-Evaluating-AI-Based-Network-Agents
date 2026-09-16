#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
LAB="$ROOT/topology_kathara/Kath6"

cleanup() {
  cd "$LAB" >/dev/null 2>&1 || true
  kathara lclean >/dev/null 2>&1 || true
}
trap cleanup EXIT

cd "$LAB"
echo "[1/6] Starting healthy Kathara lab..."
kathara lstart --noterminals
sleep 3

echo "[2/6] Healthy-state route on r1:"
kathara exec r1 "ip route show 10.2.0.0/24"

echo "[3/6] Healthy-state pc1 -> pc2 ping:"
kathara exec pc1 "ping -c 2 -W 1 10.2.0.10"

echo "[4/6] Injecting fault: remove r1's route to 10.2.0.0/24"
kathara exec r1 "ip route del 10.2.0.0/24 via 10.12.0.2"

echo "[5/6] Fault-state route table and ping (the ping is expected to fail):"
kathara exec r1 "ip route show 10.2.0.0/24"
kathara exec pc1 "ping -c 2 -W 1 10.2.0.10" || true

echo "[6/6] Applying canonical fix and verifying recovery:"
kathara exec r1 "ip route replace 10.2.0.0/24 via 10.12.0.2"
kathara exec pc1 "ping -c 2 -W 1 10.2.0.10"

echo "Demo complete. The lab will now be cleaned up."
