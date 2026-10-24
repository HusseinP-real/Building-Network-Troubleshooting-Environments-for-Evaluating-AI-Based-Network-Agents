#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
LAB=topology_kathara/Enterprise80
echo '[START] 80 devices, no terminal windows'
kathara lstart --noterminals -d "$LAB"
echo '[CONFIG] explicit, checked provisioning'
./scripts/provision.sh
sleep 55
./scripts/verify_healthy.sh
./scripts/inject_fault.sh
./scripts/verify_fault.sh
./scripts/recover.sh
echo 'PASS: complete fault lifecycle'
