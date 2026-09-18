#!/bin/bash
set -u

SESSION_ID="${1:-${SESSION_ID:-}}"
if [ -z "$SESSION_ID" ]; then
  echo "Usage: $0 <SESSION_ID>"
  echo "or: SESSION_ID=<id> $0"
  exit 2
fi

OUT="02_extended_healthy_results.txt"

run() {
  echo "+ $*" | tee -a "$OUT"
  "$@" 2>&1 | tee -a "$OUT"
}

echo "==================================================" | tee "$OUT"
echo " EXTENDED ABILENE - HEALTHY VALIDATION"           | tee -a "$OUT"
echo " SESSION: $SESSION_ID"                            | tee -a "$OUT"
echo "==================================================" | tee -a "$OUT"

echo -e "\n[1] New devices" | tee -a "$OUT"
run uv run nika session containers --session_id "$SESSION_ID"

echo -e "\n[2] YUMAng interfaces" | tee -a "$OUT"
run uv run nika exec --session_id "$SESSION_ID" yumang ip -br addr

echo -e "\n[3] YUMAng IS-IS neighbour" | tee -a "$OUT"
run uv run nika exec --session_id "$SESSION_ID" yumang "vtysh -c 'show isis neighbor'"

echo -e "\n[4] SNVAng IS-IS neighbour" | tee -a "$OUT"
run uv run nika exec --session_id "$SESSION_ID" snvang "vtysh -c 'show isis neighbor'"

echo -e "\n[5] YUMAng routing table" | tee -a "$OUT"
run uv run nika exec --session_id "$SESSION_ID" yumang ip route

echo -e "\n[6] Local access: pc_yumang -> gateway" | tee -a "$OUT"
run uv run nika exec --session_id "$SESSION_ID" pc_yumang ping -c 3 10.254.0.49

echo -e "\n[7] Old router -> new loopback" | tee -a "$OUT"
run uv run nika exec --session_id "$SESSION_ID" atlam5 ping -c 3 10.255.0.13

echo -e "\n[8] Old PC -> new PC" | tee -a "$OUT"
run uv run nika exec --session_id "$SESSION_ID" pc_atlam5 ping -c 3 10.254.0.50

echo -e "\n[9] New PC -> old PC" | tee -a "$OUT"
run uv run nika exec --session_id "$SESSION_ID" pc_yumang ping -c 3 10.254.0.2

echo -e "\n[DONE] Output: $OUT"
