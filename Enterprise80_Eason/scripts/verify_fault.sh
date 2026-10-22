#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
D=./scripts/device.sh
fail(){ echo "FAIL: $*" >&2; exit 1; }
echo '[1/4] Gateway still reachable'
$D sydpc1 ping -c 2 -W 2 10.10.10.1 || fail 'Gateway unreachable (unexpected)'
echo '[2/4] sydr1 interfaces remain addressed'
$D sydr1 ip -4 -br addr | grep -Fq '10.10.10.1/24' || fail 'LAN interface missing'
echo '[3/4] ospfd stopped'
if $D sydr1 pgrep -x ospfd >/dev/null; then fail 'ospfd is still running'; fi
echo '[4/4] Remote connectivity must fail'
if $D sydpc1 ping -c 3 -W 2 10.100.10.11 >/dev/null; then fail 'Remote ping still succeeds'; fi
echo 'PASS: injected fault produces expected symptoms'
