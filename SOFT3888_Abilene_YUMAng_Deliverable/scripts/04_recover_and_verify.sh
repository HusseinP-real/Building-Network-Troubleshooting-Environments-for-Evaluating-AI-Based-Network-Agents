#!/bin/bash
set -u

SESSION_ID="${1:-${SESSION_ID:-}}"
if [ -z "$SESSION_ID" ]; then
  echo "Usage: $0 <SESSION_ID>"
  echo "or: SESSION_ID=<id> $0"
  exit 2
fi

OUT="04_recovery_final.txt"

echo "==================================================" | tee "$OUT"
echo " YUMANG IS-IS RECOVERY + VALIDATION"              | tee -a "$OUT"
echo " SESSION: $SESSION_ID"                            | tee -a "$OUT"
echo "==================================================" | tee -a "$OUT"

echo -e "\n[1] Restore IS-IS on yumang eth0" | tee -a "$OUT"
uv run nika exec --session_id "$SESSION_ID" yumang \
  "vtysh -c 'configure terminal' -c 'interface eth0' -c 'ip router isis NIKA' -c 'end'" \
  2>&1 | tee -a "$OUT"

echo -e "\n[2] Wait for adjacency" | tee -a "$OUT"
ADJ=0
for i in {1..18}; do
  NBR=$(uv run nika exec --session_id "$SESSION_ID" yumang \
    "vtysh -c 'show isis neighbor'" 2>&1)
  if echo "$NBR" | grep -Eq "snvang[[:space:]]+eth0[[:space:]]+2[[:space:]]+Up"; then
    echo "$NBR" | tee -a "$OUT"
    echo "[PASS] IS-IS adjacency restored (attempt $i)." | tee -a "$OUT"
    ADJ=1
    break
  fi
  echo "Waiting for adjacency... attempt $i/18" | tee -a "$OUT"
  sleep 5
done

if [ "$ADJ" -ne 1 ]; then
  echo "[FAIL] IS-IS adjacency did not restore within timeout." | tee -a "$OUT"
fi

echo -e "\n[3] Wait for remote route on yumang" | tee -a "$OUT"
LOCAL_RIB=0
for i in {1..18}; do
  ROUTES=$(uv run nika exec --session_id "$SESSION_ID" yumang ip route 2>&1)
  if echo "$ROUTES" | grep -q "10.255.0.1.*proto isis"; then
    echo "[PASS] YUMAng remote IS-IS routes restored (attempt $i)." | tee -a "$OUT"
    LOCAL_RIB=1
    break
  fi
  echo "Waiting for YUMAng RIB... attempt $i/18" | tee -a "$OUT"
  sleep 5
done

echo -e "\n[4] Wait for remote network to relearn yumang" | tee -a "$OUT"
REMOTE_RIB=0
for i in {1..18}; do
  ROUTES=$(uv run nika exec --session_id "$SESSION_ID" atlam5 ip route 2>&1)
  if echo "$ROUTES" | grep -q "10.255.0.13.*proto isis"; then
    echo "[PASS] Existing network relearned YUMAng loopback (attempt $i)." | tee -a "$OUT"
    REMOTE_RIB=1
    break
  fi
  echo "Waiting for remote RIB... attempt $i/18" | tee -a "$OUT"
  sleep 5
done

echo -e "\n[5] Final YUMAng routing table" | tee -a "$OUT"
uv run nika exec --session_id "$SESSION_ID" yumang ip route 2>&1 | tee -a "$OUT"

echo -e "\n[6] atlam5 -> yumang loopback (expected PASS)" | tee -a "$OUT"
uv run nika exec --session_id "$SESSION_ID" atlam5 ping -c 3 10.255.0.13 \
  2>&1 | tee -a "$OUT"

echo -e "\n[7] pc_atlam5 -> pc_yumang (expected PASS)" | tee -a "$OUT"
uv run nika exec --session_id "$SESSION_ID" pc_atlam5 ping -c 3 10.254.0.50 \
  2>&1 | tee -a "$OUT"

echo -e "\n[DONE] Output: $OUT"
