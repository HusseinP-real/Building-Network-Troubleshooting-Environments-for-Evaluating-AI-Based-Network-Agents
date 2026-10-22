# Abilene Topology Changes

## Base Topology

The base topology is NIKA's `isp_abilene` scenario, sourced from:

`src/nika/net_env/isp/sndlib/abilene/network.xml`

The original topology contains:

- 12 routers
- 12 edge hosts

## Changes Made

A synthetic site named `YUMAng` was added to extend the original topology.

### New Router

- Node ID: `YUMAng`
- Runtime device name: `yumang`
- Loopback: `10.255.0.13/32`

### New Host

- Host name: `pc_yumang`
- Address: `10.254.0.50/30`
- Gateway: `10.254.0.49`

### New Backbone Link

- Link ID: `SNVAng_YUMAng`
- Connected routers: `SNVAng <-> YUMAng`
- SNVAng address: `10.0.0.30/31`
- YUMAng address: `10.0.0.31/31`

## Extended Topology Size

After the modification:

- 13 routers
- 13 edge hosts
- 26 containers

## Purpose

The YUMAng site is a synthetic benchmark extension and is not intended to represent a historical Abilene PoP.

The extension was created to support reproducible network fault scenarios and AI-based network troubleshooting evaluation.
