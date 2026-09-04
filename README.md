# Kath6 — FaulT-Bench static-route fault example

This is a small proof-of-concept scenario designed to match the supplied FaulT-Bench organization:

- `topology_kathara/Kath6/` — healthy Kathara lab
- `dataset/Kath6_Q/base/` — one real-fault (`base`) scenario
- `scripts/manual_demo.sh` — manual healthy → inject → fail → fix demonstration

## Topology

```text
10.1.0.0/24                 10.12.0.0/30                10.2.0.0/24

 pc1 -------- r1 -------------------------------- r2 -------- pc2
10.1.0.10   .1          .1                 .2   .1        10.2.0.10
             eth0       eth1               eth0 eth1
```

Healthy routing:

- pc1 default gateway: `10.1.0.1`
- r1 route to right LAN: `10.2.0.0/24 via 10.12.0.2`
- r2 route to left LAN: `10.1.0.0/24 via 10.12.0.1`
- pc2 default gateway: `10.2.0.1`

## Injected fault

On `r1`, delete:

```bash
ip route del 10.2.0.0/24 via 10.12.0.2
```

Expected symptom: pc1 can still reach its local gateway, but cannot reach pc2.

## Canonical fix

```bash
ip route replace 10.2.0.0/24 via 10.12.0.2
```

## Manual Kathara test

From this example bundle:

```bash
./scripts/manual_demo.sh
```

Or run the lab directly:

```bash
cd topology_kathara/Kath6
kathara lstart --noterminals
kathara connect pc1
```

Clean up when finished:

```bash
kathara lclean
```

## Put it into FaulT-Bench

Copy/merge these two folders into the root of your FaulT-Bench clone:

```text
topology_kathara/Kath6/
dataset/Kath6_Q/base/kath6-r1-static-route-removed.txt
```

Then, from the directory that contains `fb.sh`, first confirm that your local FaulT-Bench version discovers the scenario:

```bash
./fb.sh list --scope base
```

Look for `kath6-r1-static-route-removed`.

Because the supplied File Library excerpts do not include the complete `lab.py` topology-resolution implementation or the complete CLI command table, this bundle does not assume an unverified FaulT-Bench `run ...` command. Use:

```bash
./fb.sh --help
```

and the help for the relevant run command in your clone before launching the agent evaluation.

## Why this is a useful first scenario

It isolates one fault and has an unambiguous ground truth. The healthy state is easy to verify, the injection is reversible, and the observable symptom changes immediately. After this works end-to-end, the same structure can be extended to OSPF, BGP, VLAN, ACL, DNS/DHCP, or multi-fault scenarios.
