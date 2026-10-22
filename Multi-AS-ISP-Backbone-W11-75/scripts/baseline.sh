#!/usr/bin/env bash
set -u
BASE="$(cd "$(dirname "$0")" && pwd)"
fail=0
probe(){ echo "TEST $*"; "$BASE/exec.sh" "$@" || fail=$((fail+1)); }
# Check loopback reachability within IS-IS and OSPF, across the ASes via eBGP
probe as65010r1 ping -c 2 -W 2 10.10.255.4
probe as65100r1 ping -c 2 -W 2 10.40.255.5
probe as65010h1 ping -c 2 -W 3 10.50.1.34
probe as65100h1 ping -c 2 -W 3 10.20.1.34
probe as65200h9 ping -c 2 -W 3 10.30.1.2
probe as65010r1 vtysh -c "show isis neighbor"
probe as65100r1 vtysh -c "show ip ospf neighbor"
probe as65010r1 vtysh -c "show bgp summary"
echo "Command failures: $fail; inspect output too: BGP may still be converging."
[ "$fail" -eq 0 ]
