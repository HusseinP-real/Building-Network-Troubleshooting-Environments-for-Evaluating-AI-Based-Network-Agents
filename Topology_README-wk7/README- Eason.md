# NIKA Complex Enterprise OSPF — Installation and Run Guide

This package replaces the implementation of NIKA's existing `ospf_enterprise_static` scenario with one fixed 75-node topology. It deliberately retains:

- scenario id: `ospf_enterprise_static`
- Python class: `OSPFEnterpriseStatic`
- Kathara backend

Therefore the existing NIKA scenario registry does not need a new entry.

## 1. Install / prepare NIKA

From the NIKA repository root:

```bash
uv sync --extra kathara
```

You also need Docker and Kathara working normally.

## 2. Back up the original scenario

From the NIKA repository root:

```bash
cp src/nika/net_env/kathara/intradomain_routing/ospf_enterprise/lab_static.py \
   src/nika/net_env/kathara/intradomain_routing/ospf_enterprise/lab_static.py.original
```

If your checkout stores this class in a slightly different file, locate it with:

```bash
grep -R "class OSPFEnterpriseStatic" -n src/nika/net_env
```

Then use the returned file as the replacement target.

## 3. Replace `lab_static.py`

Copy the supplied `lab_static.py` over NIKA's original file:

```bash
cp /path/to/nika_complex_enterprise_patch/lab_static.py \
   src/nika/net_env/kathara/intradomain_routing/ospf_enterprise/lab_static.py
```

No `net_env_pool.py` edit should be necessary because the scenario id and class name are unchanged.

## 4. Confirm NIKA still discovers the scenario

```bash
uv run nika env list
```

Confirm that `ospf_enterprise_static` is present.

## 5. Deploy the topology

Normal command:

```bash
uv run nika env run ospf_enterprise_static
```

Some newer NIKA registries may expose the original scenario through a size selector. The replacement class accepts that argument but intentionally always creates the same 75-node topology. If your CLI says a size is required, run:

```bash
uv run nika env run ospf_enterprise_static -s l
```

## 6. Inspect the running lab

```bash
uv run nika session inspect -c
```

You should see 75 nodes:

- 15 routers
- 7 switches
- 48 PCs
- 5 web servers

Key nodes include:

```text
router_core_1
router_core_2
router_core_3
router_a_abr
router_b_abr
router_c_abr
router_dc_abr
router_a_dist_1
router_a_dist_2
...
pc_a1_01 ... pc_c2_08
web_server_1 ... web_server_5
```

## 7. Healthy-state checks

Wait a few seconds for OSPF to converge, then run:

```bash
uv run nika exec router_core_1 vtysh -c "show ip ospf neighbor"
uv run nika exec router_a_abr vtysh -c "show ip route ospf"
uv run nika exec pc_a1_01 ping -c 3 10.40.10.11
uv run nika exec pc_b2_08 ping -c 3 10.10.10.11
uv run nika exec pc_c2_08 ping -c 3 10.20.10.11
```

Or run the included helper:

```bash
bash /path/to/nika_complex_enterprise_patch/health_check.sh
```

## 8. Inject faults without SADE

You do not need an agent for this stage. The manual workflow is:

```text
nika env run
    -> health check
    -> nika failure describe
    -> nika failure inject
    -> nika exec / nika failure ps
    -> nika session close
```

Example:

```bash
uv run nika failure describe link_down
uv run nika failure inject link_down \
  --set host_name=router_core_1 \
  --set intf_name=eth0

uv run nika failure ps
uv run nika exec router_core_1 ip link show eth0
uv run nika exec pc_a1_01 ping -c 5 10.40.10.11
```

## 9. Reset between test cases

The safest way to return to the healthy baseline is to redeploy:

```bash
uv run nika session close -y
uv run nika env run ospf_enterprise_static
```

If your installation requires a size argument, use `-s l` on the second command.

## 10. Restore original NIKA topology (if needed)

```bash
mv src/nika/net_env/kathara/intradomain_routing/ospf_enterprise/lab_static.py.original \
   src/nika/net_env/kathara/intradomain_routing/ospf_enterprise/lab_static.py
```

## IP plan

| Area | Purpose | Networks |
|---|---|---|
| 0 | Core / ABR uplinks | `10.0.0.0/24` broken into `/30`s |
| 10 | Campus A | `10.10.0.0/24`, user LANs `10.10.10.0/24`, `10.10.20.0/24` |
| 20 | Campus B | `10.20.0.0/24`, user LANs `10.20.10.0/24`, `10.20.20.0/24` |
| 30 | Campus C | `10.30.0.0/24`, user LANs `10.30.10.0/24`, `10.30.20.0/24` |
| 40 | Data centre | `10.40.0.0/24`, server LAN `10.40.10.0/24` |

Web servers:

```text
web_server_1 = 10.40.10.11
web_server_2 = 10.40.10.12
web_server_3 = 10.40.10.13
web_server_4 = 10.40.10.14
web_server_5 = 10.40.10.15
```