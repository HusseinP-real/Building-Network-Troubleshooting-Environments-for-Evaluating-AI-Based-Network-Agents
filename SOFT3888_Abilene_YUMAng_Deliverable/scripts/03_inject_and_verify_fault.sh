#!/bin/bash
set -u

SESSION_ID="${1:-${SESSION_ID:-}}"
if [ -z "$SESSION_ID" ]; then
  echo "Usage: $0 <SESSION_ID>"
  echo "or: SESSION_ID=<id> $0"
  exit 2
fi

OUT="03_fault_results.txt"

echo "==================================================" | tee "$OUT"
echo " YUMANG IS-IS FAULT INJECTION + VALIDATION"       | tee -a "$OUT"
echo " SESSION: $SESSION_ID"                            | tee -a "$OUT"
echo "==================================================" | tee -a "$OUT"

echo -e "\n[1] Pre-fault neighbour state" | tee -a "$OUT"
uv run nika exec --session_id "$SESSION_ID" yumang \
  "vtysh -c 'show isis neighbor'" 2>&1 | tee -a "$OUT"

echo -e "\n[2] Injecting fault on yumang eth0" | tee -a "$OUT"
uv run nika exec --session_id "$SESSION_ID" yumang \
  "vtysh -c 'configure terminal' -c 'interface eth0' -c 'no ip router isis NIKA' -c 'end'" \
  2>&1 | tee -a "$OUT"

echo -e "\n[3] Waiting for route withdrawal" | tee -a "$OUT"
WITHDRAWN=0
for i in {1..18}; do
  ROUTE=$(uv run nika exec --session_id "$SESSION_ID" atlam5 ip route 2>&1)
  if ! echo "$ROUTE" | grep -q "10.255.0.13.*proto isis"; then
    echo "[PASS] Remote route to yumang withdrawn (attempt $i)." | tee -a "$OUT"
    WITHDRAWN=1
    break
  fi
  echo "Waiting... attempt $i/18" | tee -a "$OUT"
  sleep 5
done

if [ "$WITHDRAWN" -ne 1 ]; then
  echo "[WARN] Route withdrawal not observed within timeout." | tee -a "$OUT"
fi

echo -e "\n[4] YUMAng neighbour state after fault" | tee -a "$OUT"
uv run nika exec --session_id "$SESSION_ID" yumang \
  "vtysh -c 'show isis neighbor'" 2>&1 | tee -a "$OUT"

echo -e "\n[5] SNVAng neighbour state after fault" | tee -a "$OUT"
uv run nika exec --session_id "$SESSION_ID" snvang \
  "vtysh -c 'show isis neighbor'" 2>&1 | tee -a "$OUT"

echo -e "\n[6] YUMAng routing table after fault" | tee -a "$OUT"
uv run nika exec --session_id "$SESSION_ID" yumang ip route 2>&1 | tee -a "$OUT"

echo -e "\n[7] atlam5 -> yumang loopback (expected FAIL)" | tee -a "$OUT"
uv run nika exec --session_id "$SESSION_ID" atlam5 ping -c 3 10.255.0.13 \
  2>&1 | tee -a "$OUT" || true

echo -e "\n[8] pc_atlam5 -> pc_yumang (expected FAIL)" | tee -a "$OUT"
uv run nika exec --session_id "$SESSION_ID" pc_atlam5 ping -c 3 10.254.0.50 \
  2>&1 | tee -a "$OUT" || true

echo -e "\n[DONE] Output: $OUT"
