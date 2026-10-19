#!/usr/bin/env bash
set -euo pipefail
BASE="$(cd "$(dirname "$0")/.." && pwd)"
[ "$#" -eq 2 ] || { echo "Usage: $0 inject|recover S01..S07 (S08: follow README)"; exit 2; }
action="$1"; id="$2"
[[ "$action" == "inject" || "$action" == "recover" ]] || exit 2
python3 - "$BASE/scenarios/$id/ground_truth.json" "$action" > /dev/null <<'PYS'
import sys,json
x=json.load(open(sys.argv[1])); assert x['id'] in [f'S{i:02d}' for i in range(1,9)]
PYS
if [[ "$id" == S06 ]]; then echo "Healthy false premise: no change to network"; exit 0; fi
if [[ "$id" == S08 ]]; then echo "Use S01 and S04 separately; see scenarios/S08/README.md"; exit 2; fi
readarray -t vals < <(python3 - "$BASE/scenarios/$id/ground_truth.json" "$action" <<'PYS'
import json,sys
x=json.load(open(sys.argv[1]));print(x['fault_device']);print(x['injection' if sys.argv[2]=='inject' else 'recovery'])
PYS
)
"$BASE/scripts/exec.sh" "${vals[0]}" bash -lc "${vals[1]}"
echo "$action $id finished. Verify data-plane/control-plane state before interpreting SADE output."
