# Kath3 Wrong Default Gateway Verification

## Contributor
Kairos Liu

## Purpose
This records a controlled fault test performed on the existing FaulT-Bench `Kath3` topology. The test verifies a healthy baseline, injects a wrong default gateway on `laptop0`, observes the resulting loss of remote connectivity, and restores the correct configuration.

## Existing topology used
`FaulT-Bench/topology_kathara/Kath3`

Relevant observed addresses:
- `laptop0`: `172.16.20.10/24`
- correct default gateway / `router0` VLAN 20 interface: `172.16.20.1`
- remote test destination: `192.168.100.1`

`router0` was also inspected with `ip addr`, `ip route`, and `vtysh -c "show ip route"`. Its routing table contained connected and RIP-learned routes, including a route to `192.168.100.0/24` via `10.16.1.2`.

## Healthy baseline
On `laptop0`, the original route was:

```text
default via 172.16.20.1 dev eth0
172.16.20.0/24 dev eth0 proto kernel scope link src 172.16.20.10
```

With the correct gateway, the remote destination was reachable:

```text
ping -c 4 192.168.100.1
4 packets transmitted, 4 received, 0% packet loss
```

## Fault injection
The correct default route was removed and replaced with an incorrect gateway:

```bash
ip route del default
ip route add default via 172.16.20.254 dev eth0
```

The resulting route was:

```text
default via 172.16.20.254 dev eth0
172.16.20.0/24 dev eth0 proto kernel scope link src 172.16.20.10
```

## Fault verification
The local router interface remained reachable:

```text
ping -c 4 172.16.20.1
4 packets transmitted, 4 received, 0% packet loss
```

However, the remote destination failed:

```text
ping -c 4 192.168.100.1
Destination Host Unreachable
4 packets transmitted, 0 received, 100% packet loss
```

This demonstrates that local subnet connectivity still worked while traffic requiring the default gateway failed.

## Recovery
The incorrect route was removed and the correct gateway restored:

```bash
ip route del default
ip route add default via 172.16.20.1 dev eth0
```

After recovery:

```text
ping -c 4 192.168.100.1
4 packets transmitted, 4 received, 0% packet loss
```

## Ground truth
- Fault present: Yes
- Fault type: Wrong default gateway
- Affected node: `laptop0`
- Affected interface: `eth0`
- Incorrect gateway: `172.16.20.254`
- Correct gateway: `172.16.20.1`
- Expected symptom: local subnet remains reachable, but remote networks are unreachable
- Required fix: restore the default route through `172.16.20.1`

## Reproduction sequence
From the `Kath3` directory, start the existing topology and connect to `laptop0`. Then use the fault injection and recovery commands above. Clean the Kathara lab after testing.

This folder documents the test; it does not duplicate or modify the existing Kath3 topology files.
