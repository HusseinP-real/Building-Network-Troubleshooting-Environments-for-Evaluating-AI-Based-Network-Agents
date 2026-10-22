# Wrong Default Gateway Fault Scenario

## Overview

This scenario provides a reproducible network troubleshooting case using the existing Kath3 topology.

A wrong default gateway is injected into `laptop0`. The fault is designed so that the laptop can still communicate with its local gateway, while communication with remote networks fails.

The scenario includes:

- a verified healthy baseline;
- controlled fault injection;
- runtime fault evidence;
- recovery and verification;
- structured ground truth;
- multiple user-ticket variants;
- automated scenario execution; and
- automated validation.

The scenario has been tested successfully in the Kath3 environment.

---

## 1. Scenario Configuration

| Item | Value |
|---|---|
| Topology | Kath3 |
| Affected device | `laptop0` |
| Interface | `eth0` |
| Device IP | `172.16.20.10` |
| Correct default gateway | `172.16.20.1` |
| Injected wrong gateway | `172.16.20.254` |
| Local connectivity target | `172.16.20.1` |
| Remote connectivity target | `192.168.100.1` |
| Fault category | Endpoint routing misconfiguration |
| Fault type | Wrong default gateway |

The Kath3 topology was successfully deployed before this scenario was executed.

---

## 2. Healthy Baseline

Before fault injection, `laptop0` uses the correct default route:

```text
default via 172.16.20.1 dev eth0
172.16.20.0/24 dev eth0 proto kernel scope link src 172.16.20.10
```

Two connectivity tests are used.

### Local connectivity

```text
laptop0 -> 172.16.20.1
```

Observed result:

```text
4 packets transmitted, 4 received, 0% packet loss
```

### Remote connectivity

```text
laptop0 -> 192.168.100.1
```

Observed result:

```text
4 packets transmitted, 4 received, 0% packet loss
```

Therefore, both local and remote connectivity are confirmed before the fault is introduced.

---

## 3. Fault Injection

The correct default route is removed and replaced with an incorrect gateway:

```bash
ip route del default
ip route add default via 172.16.20.254 dev eth0
```

The routing table then becomes:

```text
default via 172.16.20.254 dev eth0
172.16.20.0/24 dev eth0 proto kernel scope link src 172.16.20.10
```

This changes only the default route on `laptop0`.

---

## 4. Fault Verification

After the wrong gateway is injected, local connectivity is tested again.

### Local gateway

```text
laptop0 -> 172.16.20.1
```

Observed result:

```text
4 packets transmitted, 4 received, 0% packet loss
```

The local network is therefore still reachable.

### Remote network

```text
laptop0 -> 192.168.100.1
```

Observed result:

```text
Destination Host Unreachable

4 packets transmitted, 0 received, +4 errors, 100% packet loss
```

This produces the intended troubleshooting symptom:

```text
Local connectivity:  PASS
Remote connectivity: FAIL
```

The result helps distinguish the fault from a complete interface failure or local network outage.

---

## 5. Ground Truth

The expected diagnosis is:

```text
Affected device:    laptop0
Affected interface: eth0
Fault type:         wrong default gateway
Correct gateway:    172.16.20.1
Incorrect gateway:  172.16.20.254
```

### Root cause

`laptop0` has an incorrect default route. Traffic for remote networks is sent toward `172.16.20.254` instead of the correct gateway `172.16.20.1`.

The structured ground truth is stored in:

```text
ground_truth.json
```

This can later be used to compare an AI troubleshooting agent's diagnosis against the known fault.

---

## 6. Recovery

The incorrect route is removed and the correct default gateway is restored:

```bash
ip route del default
ip route add default via 172.16.20.1 dev eth0
```

The recovered routing table is:

```text
default via 172.16.20.1 dev eth0
172.16.20.0/24 dev eth0 proto kernel scope link src 172.16.20.10
```

### Recovery verification

Local connectivity:

```text
4 packets transmitted, 4 received, 0% packet loss
```

Remote connectivity:

```text
4 packets transmitted, 4 received, 0% packet loss
```

The recovery therefore restores the expected healthy network behaviour.

---

## 7. Observed Fault Lifecycle

The complete tested lifecycle is:

```text
HEALTHY
default gateway = 172.16.20.1
local  -> PASS
remote -> PASS

        |
        v

FAULT INJECTION
default gateway = 172.16.20.254

        |
        v

FAULT STATE
local  -> PASS
remote -> FAIL (100% packet loss)

        |
        v

RECOVERY
default gateway = 172.16.20.1

        |
        v

RECOVERED STATE
local  -> PASS
remote -> PASS
```

This lifecycle was reproduced successfully in the live Kathara environment.

---

## 8. Automated Scenario Execution

The complete scenario can be executed using:

```bash
./kairos_wrong_gateway/run_scenario.sh
```

The script:

1. discovers the running `laptop0` Kathara container;
2. restores the correct gateway for the healthy baseline;
3. verifies local and remote connectivity;
4. injects the wrong default gateway;
5. verifies the expected fault symptoms;
6. restores the correct gateway; and
7. verifies recovery.

The script records raw runtime output in:

```text
evidence/01_healthy_raw.txt
evidence/02_fault_raw.txt
evidence/03_recovery_raw.txt
```

---

## 9. Automated Validation

The recorded runtime evidence can be checked using:

```bash
./kairos_wrong_gateway/validate_scenario.sh
```

The validator checks:

1. the healthy gateway is correct;
2. healthy local connectivity succeeds;
3. healthy remote connectivity succeeds;
4. the wrong gateway is injected;
5. the local network remains reachable during the fault;
6. remote connectivity fails during the fault;
7. the correct gateway is restored; and
8. remote connectivity is restored.

The latest validation result was:

```text
[PASS] Healthy gateway is correct
[PASS] Healthy local connectivity succeeds
[PASS] Healthy remote connectivity succeeds
[PASS] Wrong gateway was injected
[PASS] Local network remains reachable during fault
[PASS] Remote connectivity fails during fault
[PASS] Correct gateway is restored
[PASS] Remote connectivity is restored

8 checks passed
0 checks failed
SCENARIO RESULT: PASS
```

---

## 10. Evidence

Raw runtime evidence is stored in:

```text
evidence/01_healthy_raw.txt
evidence/02_fault_raw.txt
evidence/03_recovery_raw.txt
```

Additional validation summaries are stored in:

```text
evidence/01_healthy.txt
evidence/02_fault.txt
evidence/03_recovery.txt
```

The raw evidence is generated directly from the automated scenario execution.

---

## 11. User Ticket Variants

The file:

```text
user_tickets.json
```

contains multiple descriptions of the same underlying network problem.

The current variants include:

- general user report;
- technical user report;
- vague user report; and
- misleading user report.

For example, a user may report that local resources are accessible but remote services cannot be reached without explicitly mentioning the default gateway.

These variants allow the same ground-truth fault to later be presented to an AI troubleshooting agent using different levels of information.

---

## 12. Deliverable Structure

```text
kairos_wrong_gateway/
├── README.md
├── ground_truth.json
├── user_tickets.json
├── run_scenario.sh
├── validate_scenario.sh
└── evidence/
    ├── 01_healthy.txt
    ├── 01_healthy_raw.txt
    ├── 02_fault.txt
    ├── 02_fault_raw.txt
    ├── 03_recovery.txt
    └── 03_recovery_raw.txt
```

---

## 13. Reproduction

Start the Kath3 topology first:

```bash
python -m kathara lstart
```

Then execute the scenario:

```bash
./kairos_wrong_gateway/run_scenario.sh
```

Validate the generated evidence:

```bash
./kairos_wrong_gateway/validate_scenario.sh
```

A successful run should finish with:

```text
8 checks passed
0 checks failed
SCENARIO RESULT: PASS
```

---

## 14. Current Scope and Future Integration

The current deliverable demonstrates a complete reproducible fault lifecycle:

```text
healthy baseline
      ->
controlled fault injection
      ->
fault verification
      ->
ground truth
      ->
recovery
      ->
recovery verification
      ->
automated validation
```

NIKA/SADE or another AI troubleshooting agent is not integrated into this scenario yet.

The scenario is prepared for later agent evaluation. An agent can be given one of the user-ticket variants and access to the troubleshooting environment. Its detected fault type, affected device, localisation, root cause, and proposed recovery can then be compared against `ground_truth.json`.
