# Deployment, Operation and Reproduction Guide

## Requirements

- macOS or Linux host with sufficient Docker Desktop resources for 80 Linux containers.
- Docker daemon, Kathara CLI, Python 3.9+.
- Images `kathara/frr:10` and `kathara/base:latest` (first run may require pulling them).
- Keep the project directory in one stable location **throughout a running experiment**; Kathara mounts project files into containers.

## 1. Preflight

```bash
cd ~/Desktop/MultiSite_BGP_OSPF_Benchmark    # change to your actual path
pwd -P
chmod +x run_mac.sh
./run_mac.sh
kathara check
docker info >/dev/null && echo 'Docker OK'
```

On the developer's confirmed test, `./run_mac.sh` generated **80 nodes**, **68 collision domains**, **20 P2P routed links**, passed **8 unit tests**, and found **92 distinct IPs**. The actual numbers come from this release, not generic Kathara defaults.

## 2. Start and verify

```bash
python3 lab.py start
kathara exec -d "$PWD" e1 "ip -br addr"
kathara exec -d "$PWD" e1 "vtysh -c 'show bgp summary'"
kathara exec -d "$PWD" e1 "vtysh -c 'show ip ospf neighbor'"
python3 lab.py check
```

Allow routing to converge before `check`. The expected baseline summary for the verified prototype is `Baseline: 18/18 passed`.

### What baseline checks actually test

- Four enterprise-edge BGP-neighbor established assertions (`e1`–`e4`).
- Twelve ICMP probes: HQ, Branch A, Branch B and DC hosts to the DC service host and the two simulated ISP service hosts.
- Two HTTP service probes to `198.18.10.10:8080` and `198.18.20.10:8080`.

They are **not** a full mesh between all 80 nodes.

## 3. Fault experiments

After baseline passes, run one scenario at a time:

```bash
python3 lab.py test-fault F01 --settle-seconds 35
python3 lab.py check
python3 lab.py test-fault F02 --settle-seconds 35
python3 lab.py check
python3 lab.py test-fault F03 --settle-seconds 35
python3 lab.py check
```

`test-fault` checks healthy preconditions, applies the fault, waits for protocol convergence, checks an expected affected path and an unaffected control path, attempts recovery and verifies the affected path is restored. It writes `results/F01_latest.json`, etc. **Inspect each returned `passed` value and exit code.**

If using manual injection (`python3 lab.py inject F01`), always run the corresponding repair (`python3 lab.py repair F01`) before baseline. Do not leave the lab faulted between trials.

## 4. Save raw evidence

```bash
mkdir -p results/evidence
python3 lab.py check | tee results/evidence/baseline.txt
kathara exec -d "$PWD" e1 "vtysh -c 'show bgp summary'" > results/evidence/bgp_e1.txt
kathara exec -d "$PWD" e1 "vtysh -c 'show ip ospf neighbor'" > results/evidence/ospf_e1.txt
kathara --version > results/evidence/kathara_version.txt
python3 --version > results/evidence/python_version.txt 2>&1
```

Record `git rev-parse HEAD`, host OS, Docker and image versions, scenario ID, times, and whether each run was repeated. Capture console fault output or the actual `results/FXX_latest.json` files for reproducible evidence. Do not invent or edit raw logs to make tests look successful.

## 5. Stop only this project

```bash
python3 lab.py stop
```

Do not use `kathara wipe`, a blanket container purge, or `docker system prune` as the normal teardown method: they could disrupt other Kathara/NIKA labs.

## 6. Troubleshooting notes from the first live deployment

| Symptom | Observed issue / safe approach |
|---|---|
| `./run_mac.sh: permission denied` | `chmod +x run_mac.sh` or `bash run_mac.sh` |
| Router interfaces are UP but have no IP | Early startup had a blocked `sysctl -w`; current generator applies `net.ipv4.ip_forward=1` at container creation |
| FRR shows `bgpd is not running` | Check device startup log and `/etc/frr/daemons`; avoid masking incomplete startup |
| `kathara exec` cannot find a running node | Ensure stable working directory; use `-d "$PWD"`, and inspect active Kathara lab rather than assuming a container name |
| Docker/Kathara reports inconsistent state | Stop this lab with `kathara lclean -d "$PWD"`; inspect resources before attempting any global cleanup |
| BGP `Active` | Check peer IP, interface address, FRR daemons and neighbor; `State/PfxRcd` numeric means established |
| Baseline failure | Fix the specific failed check; do not treat ordinary connectivity failure as successful fault testing |

**Operational note:** the original deployment had setup problems that were resolved before the reported 18/18 healthy baseline and all-three-fault success. The `RECOVERY` utility is for abnormal partial starts; it is **not** part of the standard successful path.
