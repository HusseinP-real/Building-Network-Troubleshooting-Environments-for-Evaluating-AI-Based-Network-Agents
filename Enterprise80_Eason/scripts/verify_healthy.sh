#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
D=./scripts/device.sh
fail(){ echo "FAIL: $*" >&2; exit 1; }
echo '[1/6] sydr1 IPs'
ips="$($D sydr1 ip -4 -br addr)"
printf '%s\n' "$ips"
for ip in 10.255.1.1/30 10.255.1.9/30 10.10.10.1/24; do grep -Fq "$ip" <<< "$ips" || fail "sydr1 missing $ip"; done
echo '[2/6] OSPF running'
$D sydr1 pgrep -x ospfd >/dev/null || fail 'ospfd missing'
$D sydr1 vtysh -c 'show ip ospf' | grep -q 'OSPF Routing Process' || fail 'OSPF not configured'
echo '[3/6] OSPF neighbors (must include FULL)'
nb="$($D sydr1 vtysh -c 'show ip ospf neighbor')"; echo "$nb"
grep -q 'Full' <<< "$nb" || grep -q 'FULL' <<< "$nb" || fail 'No FULL neighbor'
echo '[4/6] DC route present at Sydney router'
$D sydr1 ip -4 route get 10.100.10.11 || fail 'No DC route'
echo '[5/6] Sydney -> DC'
$D sydpc1 ping -c 3 -W 2 10.100.10.11 || fail 'Sydney to DC failed'
echo '[6/6] Melbourne -> Brisbane'
$D melpc1 ping -c 3 -W 2 10.30.10.11 || fail 'Melbourne to Brisbane failed'
echo 'PASS: healthy baseline verified'
