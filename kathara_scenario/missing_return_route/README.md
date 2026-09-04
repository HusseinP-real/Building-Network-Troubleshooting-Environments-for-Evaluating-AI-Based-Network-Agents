# Missing Return Route Scenario

## Scenario ID: 01-04-09

routing_missing_return_route_001

## Topology

h1 --\
      LAN_A -- r1 -- TRANSIT -- r2 -- LAN_B -- h3
h2 --/

## Devices

- h1: 10.0.1.10/24
- h2: 10.0.1.20/24
- r1 eth0: 10.0.1.1/24
- r1 eth1: 10.0.12.1/30
- r2 eth0: 10.0.12.2/30
- r2 eth1: 10.0.2.1/24
- h3: 10.0.2.10/24

## Fault

r2 is missing the route to:

10.0.1.0/24

The correct route should be:

ip route add 10.0.1.0/24 via 10.0.12.1

## Expected Symptom

h1 and h2 cannot successfully communicate with h3.

For example:

ping 10.0.2.10

from h1 should fail.

## Diagnosis

Run on r2:

ip route

The routing table does not contain a route to:

10.0.1.0/24

## Fix

Run on r2:

ip route add 10.0.1.0/24 via 10.0.12.1

After applying the fix:

ping 10.0.2.10

from h1 should succeed.

## Ground Truth

- Fault exists: Yes
- Fault type: Missing static route
- Fault device: r2
- Affected network: 10.0.1.0/24
- Expected fix: Add route through 10.0.12.1