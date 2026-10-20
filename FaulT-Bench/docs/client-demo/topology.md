# Kath3 topology in the repository

The repository already implements a 32-device topology: 7 routers, 10 switches (including 2 multilayer switches), 10 PCs and 5 laptops. This inventory is derived from numeric interface assignments in `topology_kathara/Kath3/lab.conf`. It counts configured devices, not devices proven healthy at runtime.

The client demo uses this existing topology, rather than replacing it with the earlier standalone 12-device proposal. Existing interfaces, addressing and scenarios remain compatible.

## Connected segments

```mermaid
flowchart LR
  switch1 ---|"eth0 to eth0"| mswitch1
  switch1 ---|"eth1 to eth0"| pc4
  switch1 ---|"eth2 to eth0"| pc5
  switch1 ---|"eth3 to eth0"| laptop2
  switch1 ---|"eth4 to eth0"| laptop3
  switch1 ---|"eth7 to eth0"| laptop0
  switch2 ---|"eth1 to eth2"| mswitch1
  switch4 ---|"eth0 to eth0"| router4
  switch4 ---|"eth1 to eth0"| switch5
  switch4 ---|"eth2 to eth0"| switch6
  switch5 ---|"eth1 to eth0"| pc11
  switch5 ---|"eth2 to eth0"| pc12
  switch6 ---|"eth1 to eth0"| pc13
  switch6 ---|"eth2 to eth0"| pc14
  switch9 ---|"eth0 to eth1"| mswitch2
  switch10 ---|"eth0 to eth2"| mswitch2
  switch10 ---|"eth1 to eth0"| pc15
  switch10 ---|"eth2 to eth0"| pc16
  switch10 ---|"eth3 to eth0"| pc17
  switch10 ---|"eth4 to eth0"| pc18
  switch11 ---|"eth0 to eth3"| mswitch2
  switch11 ---|"eth1 to eth0"| laptop4
  switch11 ---|"eth2 to eth0"| laptop5
  mswitch1 ---|"eth4 to eth0"| router0
  mswitch2 ---|"eth0 to eth0"| router6
  mswitch2 ---|"eth4 to eth1"| router6
  router0 ---|"eth2 to eth2"| router1
  router0 ---|"eth4 to eth4"| router5
  router1 ---|"eth3 to eth2"| router2
  router2 ---|"eth4 to eth4"| router3
  router3 ---|"eth2 to eth2"| router6
  router3 ---|"eth5 to eth5"| router4
  router4 ---|"eth4 to eth5"| router5
```

Unused one-device collision domains are omitted from the diagram. A link in lab.conf does not prove it is administratively up or forwarding.

## Demonstrated path and protocols

Laptop0 `172.16.20.10` attaches to switch1 in VLAN20. Its path to Router0 crosses switch1 and mswitch1 over the configured VLAN trunk. Router0 uses `172.16.20.1` on eth0.20 and routes to VLAN10, where PC4 is `172.16.10.4`. RIP and existing static routes connect the WAN. The remote Router2 target is `192.168.100.1`.

The wider topology includes Location C on `192.168.200.0/24` and Location B VLAN50/51 on `172.18.50.0/24` and `172.18.51.0/24`. Wireless endpoints are represented as wired devices in the original lab. The automated demo probes the nominated Laptop0/PC4/Router2 paths; it does not claim exhaustive reachability or wireless emulation.

## Configuration boundary

The demo mutates only Laptop0's running default route and the rule tagged `haosenpeng-compound-icmp`. Healthy startup files remain the source of truth. The live validator copies the complete topology to a unique temporary directory, runs the cases there, then cleans only that copy.

The historical compound-fault documentation reports an intermittent RIP startup failure. A baseline failure must abort fault injection. This update does not claim to resolve that existing startup issue.
