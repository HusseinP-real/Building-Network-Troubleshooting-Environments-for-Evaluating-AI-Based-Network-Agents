# DNS Record Misconfiguration Scenario

**Developer:** Kairos Liu
**Base topology:** EnterpriseTopology (75 devices, copied from main)
**Branch:** Kairos_Liu
**Status:** Automated fault injection, validation and recovery completed; benchmark integration pending.

## Overview

This scenario simulates an incorrect DNS A-record configuration
in the enterprise network.

The DNS server (`infra`, 10.40.20.10) normally resolves
`app.enterprise.test` to `10.30.10.10`.

A configuration error changes this record to `10.30.10.99`.
As a result, clients cannot access the application by its
hostname, although the application remains reachable by its
correct IP address.

## Environment

- Network emulator: Kathara and Docker
- Topology: 75 devices
- Routing: OSPF
- DNS service: dnsmasq
- DNS server: infra (10.40.20.10)
- Test client: office
- Application: app.enterprise.test (10.30.10.10)

## Manual Validation Results

| Test | Healthy | Fault | Recovery |
|---|---|---|---|
| Application DNS record | 10.30.10.10 | 10.30.10.99 | 10.30.10.10 |
| Application via hostname | HTTP 200 | Connection failed | HTTP 200 |
| Application via correct IP | HTTP 200 | HTTP 200 | Not separately tested |
| DMZ DNS resolution | Correct | Correct | Not separately tested |
| Full health checks | 222/222 PASS | Not run | 222/222 PASS |

The faulty hostname request produced curl status code `000`,
indicating that no HTTP response was received.

## Fault Injection

The following changes were tested manually in the running
infra container:

1. Back up `/etc/dnsmasq.conf`.
2. Replace the application DNS address from `10.30.10.10`
   with `10.30.10.99`.
3. Restart dnsmasq to reload the configuration.
4. Verify the incorrect DNS resolution and failed hostname access.

## Recovery

1. Restore the original dnsmasq configuration.
2. Restart dnsmasq.
3. Confirm the correct application DNS record and HTTP access.
4. Run the full topology health check.

The recovery health check passed all 222 checks.

## Automated Validation

Three scripts have been implemented:

- `inject.sh`: injects the incorrect DNS A record.
- `repair.sh`: restores the correct DNS configuration.
- `validate.sh`: tests Healthy, Fault and Recovery automatically.

Run from the EnterpriseTopology directory:

1. Start the network using `python3 lab.py start`.
2. Run `./scenarios/kairos_dns_record/validate.sh`.
3. Stop the network using `python3 lab.py stop` when finished.

## Automated Test Results

| Test | Result |
|---|---|
| Healthy DNS | 10.30.10.10 |
| Healthy HTTP | 200 |
| Fault DNS | 10.30.10.99 |
| Fault hostname HTTP | 000 (no HTTP response) |
| Direct IP HTTP during fault | 200 |
| Recovery DNS | 10.30.10.10 |
| Recovery HTTP | 200 |
| Recovery health checks | 222/222 PASS |

Full automated validation completed successfully on 18 October 2026.

## Evidence

- `evidence/healthy.txt`
- `evidence/injection.txt`
- `evidence/fault.txt`
- `evidence/repair.txt`
- `evidence/recovery.txt`
- `evidence/recovery_health.txt` (earlier manual test)

## Benchmark Metadata

- `ground_truth.json`: fault location, root cause and repair criteria.
- `user_tickets.json`: four user reports with different levels of detail.

Both JSON files passed syntax validation.

## Remaining Work

- Test repeated injection and recovery cycles.
- Check compatibility with the team Benchmark and Dashboard.
- Evaluate AI Agent diagnosis performance.

## Integration Notes

This scenario uses the EnterpriseTopology network structure
from the main branch but is developed independently on
Kairos_Liu.

It has not yet been integrated with the team's benchmark
or SADE evaluation workflow.
