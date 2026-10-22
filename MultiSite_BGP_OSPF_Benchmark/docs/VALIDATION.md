# Validation Summary and Evidence Register

**Evidence date:** 12 October 2026 (user-reported macOS local testing).

| ID | Test / observation | Reported result | Evidence strength |
|---|---|---|---|
| V-01 | Static generator and topology validation | PASS: 80 nodes, 68 collision domains, 92 distinct IPs, 20 routed P2P links | Console output provided |
| V-02 | Python unit tests | 8/8 PASS | Console output provided |
| V-03 | Live e1 addressing / forwarding | Five correctly addressed e1 interfaces and `ip_forward=1` | Console output provided |
| V-04 | e1–a1 eBGP | Established; one IPv4 prefix received | FRR output provided |
| V-05 | e1 OSPF adjacencies | Four neighbors in `Full/DR` | FRR output provided |
| V-06 | Healthy baseline | 18/18 PASS | Console output provided |
| V-07 | F01 injection–impact–control–repair | `passed: true` and post-repair 18/18 PASS | Console JSON/output provided |
| V-08 | F02 fault and restoration | User reported passing without errors | User confirmation; raw log not attached |
| V-09 | F03 fault and restoration | User reported passing without errors | User confirmation; raw log not attached |
| V-10 | SADE execution and scoring | Not performed | Not yet available |

## Recommended evidence filenames

```text
results/evidence/
  baseline.txt
  bgp_e1.txt
  ospf_e1.txt
  F01_console.txt
  F02_console.txt
  F03_console.txt
  environment.txt
results/
  baseline_latest.json
  F01_latest.json
  F02_latest.json
  F03_latest.json
```

These are recommended **names**, not claims that the files are already populated. Preserve original test logs and avoid adding API keys or sensitive local paths to the repository.

## Quality interpretation

A passing 18/18 baseline validates the **18 selected functional probes**, not full correctness of every node. F01–F03 establish operational fault-control and recovery coverage; they are not equivalent to an AI diagnosis accuracy experiment. Planned SADE runs should include independent agent traces and blinded ground-truth comparison.
