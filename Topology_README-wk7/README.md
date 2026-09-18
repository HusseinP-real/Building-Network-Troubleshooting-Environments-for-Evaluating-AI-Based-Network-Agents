# SOFT3888 – NIKA Abilene Topology Extension and IS-IS Fault Scenario

## 1. Project Overview

This deliverable extends the original NIKA `isp_abilene` network topology and creates a reproducible network troubleshooting scenario for evaluating AI-based network agents.

The original Abilene topology provided by NIKA contains:

- 12 routers
- 12 edge hosts
- IS-IS Level-2 as the Interior Gateway Protocol
- Kathara as the network emulation backend

This work extends the topology by adding one synthetic site:

- New router: `yumang`
- New host: `pc_yumang`
- New backbone link: `SNVAng_YUMAng`

After the extension, the topology contains:

- 13 routers
- 13 edge hosts
- 26 running containers in total

The extension is implemented at the topology source level instead of manually modifying a running container. This means the scenario is reproducible: whenever the topology is deployed again, NIKA automatically regenerates the new router, host, IP addressing, IS-IS configuration and Kathara environment.

The scenario also includes a controlled IS-IS configuration fault, validation of its impact, and full recovery.

The complete workflow is:

```text
Original NIKA Abilene Topology
        ↓
Source-Level Topology Extension
        ↓
Healthy-State Validation
        ↓
IS-IS Configuration Fault Injection
        ↓
Adjacency and Route Failure
        ↓
End-to-End Connectivity Failure
        ↓
Configuration Recovery
        ↓
IS-IS Reconvergence
        ↓
Connectivity Restored
```

---

## 2. Purpose of This Scenario

The goal of this scenario is not only to extend an existing NIKA topology, but also to create a benchmark case that can later be used to evaluate AI-based network troubleshooting agents.

The scenario provides:

- a reproducible network environment
- a known healthy state
- a known fault
- ground-truth root cause
- observable symptoms
- user-ticket variants
- deterministic validation steps
- recovery verification

This allows an AI agent to be evaluated on tasks such as:

- fault detection
- fault localisation
- root-cause analysis
- interpretation of user reports
- troubleshooting
- recovery recommendation

---

## 3. Important Note About YUMAng

`YUMAng` is a synthetic benchmark extension.

It is not intended to represent a historical node from the real Abilene network.

The original Abilene topology is used as a stable and reproducible baseline. The new site is added specifically to create an extensible benchmark scenario for testing network troubleshooting behaviour.

---

## 4. Repository Structure

A recommended delivery structure is:

```text
SOFT3888_Abilene_YUMAng_Deliverable/
│
├── README.md
│
├── scripts/
│   ├── 01_extend_abilene.py
│   ├── 02_verify_healthy.sh
│   ├── 03_inject_and_verify_fault.sh
│   └── 04_recover_and_verify.sh
│
├── docs/
│   ├── ground_truth.json
│   ├── user_tickets.json
│   ├── demo_runbook.md
│   └── delivery_notes.md
│
└── evidence/
    ├── 01_original_baseline.txt
    ├── 02_extended_healthy.txt
    ├── 03_fault.txt
    ├── 04_recovery_final.txt
    ├── 04_recovery_initial_too_early.txt
    └── 05_recovery_convergence_diagnosis.txt
```

---

## 5. Original NIKA Topology

The base environment used in this scenario is:

```text
isp_abilene
```

Important characteristics:

```text
Backend: Kathara
IGP: IS-IS
IS-IS level: Level-2
Original routers: 12
Original edge hosts: 12
Original total containers: 24
```

Examples of existing routers include:

```text
atlam5
atlang
chinng
dnvrng
hstnng
iplsng
kscyng
losang
nycmng
snvang
sttlng
washng
```

Each router also has an associated edge host such as:

```text
pc_atlam5
pc_atlang
pc_snvang
pc_washng
```

---

## 6. How NIKA Builds the Abilene Environment

The topology is data-driven.

The original Abilene topology is defined in:

```text
src/nika/net_env/isp/sndlib/abilene/network.xml
```

The general generation process is:

```text
network.xml
    ↓
NIKA loads nodes and links
    ↓
IGP plan is compiled
    ↓
router names are generated
    ↓
loopback addresses are allocated
    ↓
backbone /31 links are allocated
    ↓
edge /30 networks are allocated
    ↓
FRR configuration is generated
    ↓
IS-IS configuration is generated
    ↓
Kathara containers are created
```

This is important because the extension does not require manually creating Docker or Kathara containers.

The new topology information is added to the source topology, and NIKA handles the rest automatically.

---

## 7. Topology Extension

### 7.1 Added Router

The following node is added:

```text
YUMAng
```

At runtime, NIKA converts this into:

```text
yumang
```

### 7.2 Added Host

NIKA automatically creates:

```text
pc_yumang
```

The host is attached to the new router using an edge `/30` subnet.

### 7.3 Added Backbone Link

The new backbone link is:

```text
SNVAng <-> YUMAng
```

The synthetic site therefore behaves as a leaf site connected to the existing Abilene backbone through `snvang`.

Conceptually:

```text
Existing Abilene Backbone
          |
        SNVAng
          |
          |
        YUMAng
          |
      pc_yumang
```

---

## 8. Extended Topology Addresses

The extended topology uses the following addresses.

### YUMAng loopback

```text
10.255.0.13/32
```

### YUMAng backbone interface

```text
Interface: eth0
Address:   10.0.0.31/31
```

### SNVAng peer address

```text
10.0.0.30/31
```

### YUMAng edge interface

```text
Interface: eth1
Address:   10.254.0.49/30
```

### pc_yumang

```text
Interface: eth0
Address:   10.254.0.50/30
Gateway:   10.254.0.49
```

---

## 9. Extending the Topology

The extension script is:

```text
scripts/01_extend_abilene.py
```

Run it from the NIKA repository root:

```bash
python3 scripts/01_extend_abilene.py
```

The script:

1. creates a backup of the original `network.xml`
2. adds the `YUMAng` node
3. adds the `SNVAng_YUMAng` link
4. writes the modified topology back to the Abilene XML file

The script is designed to avoid duplicating the node or link if it is run more than once.

---

## 10. Deploying the Extended Topology

After modifying the source topology, deploy Abilene again:

```bash
uv run nika env run isp_abilene
```

NIKA returns a session ID, for example:

```text
session_id=20260917-144219-d8f5f8
```

Save this ID because it is required for all later commands.

To inspect all containers:

```bash
uv run nika session containers \
  --session_id 20260917-144219-d8f5f8
```

A successful extended deployment should contain:

```text
yumang
pc_yumang
```

The expected total is:

```text
13 routers
13 hosts
26 containers
```

---

## 11. Healthy-State Validation

The healthy-state validation script is:

```text
scripts/02_verify_healthy.sh
```

Run:

```bash
./scripts/02_verify_healthy.sh <SESSION_ID>
```

Example:

```bash
./scripts/02_verify_healthy.sh \
20260917-144219-d8f5f8
```

---

## 12. Healthy-State Success Criteria

The scenario is considered healthy only if all major checks succeed.

### 12.1 Devices exist

Both new devices must be running:

```text
yumang
pc_yumang
```

### 12.2 Interface configuration

Expected YUMAng interfaces:

```text
lo     10.255.0.13/32
eth0   10.0.0.31/31
eth1   10.254.0.49/30
```

Expected `pc_yumang` interface:

```text
eth0   10.254.0.50/30
```

### 12.3 IS-IS neighbour relationship

On `yumang`:

```text
snvang   eth0   Level 2   Up
```

On `snvang`:

```text
yumang   eth3   Level 2   Up
```

### 12.4 Routing table

`yumang` should contain many remote routes with:

```text
proto isis
```

For example:

```text
10.255.0.1 via 10.0.0.30 dev eth0 proto isis
```

### 12.5 Local host connectivity

```text
pc_yumang -> 10.254.0.49
```

Expected:

```text
0% packet loss
```

### 12.6 Existing router to new router

```text
atlam5 -> 10.255.0.13
```

Expected:

```text
0% packet loss
```

### 12.7 New router to existing router

```text
yumang -> 10.255.0.1
```

Expected:

```text
0% packet loss
```

### 12.8 Existing host to new host

```text
pc_atlam5 -> 10.254.0.50
```

Expected:

```text
0% packet loss
```

### 12.9 New host to existing host

```text
pc_yumang -> 10.254.0.2
```

Expected:

```text
0% packet loss
```

If all of these checks pass, the extension is considered successfully integrated into the existing IS-IS network.

---

## 13. Healthy-State Result

The extended topology was successfully validated.

The following were confirmed:

```text
YUMAng container running
pc_yumang container running

YUMAng ↔ SNVAng IS-IS adjacency = Up

Remote IS-IS routes learned

Existing router → new router = reachable
New router → existing router = reachable

Existing PC → new PC = reachable
New PC → existing PC = reachable
```

All end-to-end connectivity tests returned:

```text
0% packet loss
```

---

## 14. Fault Scenario

### 14.1 Fault Type

The selected fault is:

```text
IS-IS configuration omission on backbone interface
```

Fault location:

```text
Device: yumang
Interface: eth0
```

Fault command:

```text
no ip router isis NIKA
```

This removes IS-IS from the backbone interface.

---

## 15. Why This Fault Was Chosen

This fault is useful because it is not simply a physical link failure.

The interface itself remains operational.

Conceptually:

```text
eth0 = UP
IP address still configured
physical link still exists
```

But:

```text
IS-IS is no longer enabled
```

Therefore the fault isolates the routing control plane.

This creates a clearer troubleshooting scenario than simply shutting down the interface.

---

## 16. Fault Injection

The fault injection script is:

```text
scripts/03_inject_and_verify_fault.sh
```

Run:

```bash
./scripts/03_inject_and_verify_fault.sh <SESSION_ID>
```

Example:

```bash
./scripts/03_inject_and_verify_fault.sh \
20260917-144219-d8f5f8
```

The main configuration change is equivalent to:

```text
configure terminal
interface eth0
no ip router isis NIKA
end
```

---

## 17. Expected Fault Behaviour

After fault injection:

```text
YUMAng ↔ SNVAng IS-IS adjacency
        ↓
lost / unstable
```

Then:

```text
remote IS-IS routes
        ↓
removed
```

Then:

```text
remote reachability to YUMAng
        ↓
fails
```

And finally:

```text
remote access to pc_yumang
        ↓
fails
```

---

## 18. Observed Fault Result

The actual results matched the expected behaviour.

### Before fault

```text
snvang
Interface: eth0
Level: 2
State: Up
```

### After fault on YUMAng

YUMAng neighbour table became empty.

On SNVAng, YUMAng was no longer in a stable `Up` state.

### YUMAng routing table after fault

Only directly connected routes remained:

```text
10.0.0.30/31
10.254.0.48/30
```

Remote `proto isis` routes disappeared.

### Router reachability

```text
atlam5 -> 10.255.0.13
```

Result:

```text
Network is unreachable
```

### Host reachability

```text
pc_atlam5 -> 10.254.0.50
```

Result:

```text
100% packet loss
Destination Net Unreachable
```

---

## 19. Fault Root Cause

The ground-truth root cause is:

```text
IS-IS was disabled on yumang eth0.
```

More specifically:

```text
Device: yumang
Interface: eth0
Fault: missing "ip router isis NIKA"
```

Because `eth0` is YUMAng's only backbone connection, disabling IS-IS on this interface prevents YUMAng from participating correctly in the IS-IS topology.

As a result:

```text
adjacency fails
→ link-state information is no longer exchanged
→ remote routes disappear
→ remote forwarding fails
```

---

## 20. Ground Truth

The formal ground truth is stored in:

```text
docs/ground_truth.json
```

The ground truth describes:

- topology
- affected device
- affected interface
- fault category
- exact configuration error
- expected symptoms
- expected recovery action
- recovery success criteria

This file should be treated as the authoritative description of the scenario.

---

## 21. User Tickets

User-report variants are stored in:

```text
docs/user_tickets.json
```

The same network fault can be presented to an AI troubleshooting agent using reports with different levels of detail and accuracy.

Examples include:

### General user

```text
I can no longer reach services at the new Yuma site from the existing network.
```

### NOC engineer

```text
Remote reachability to the new YUMAng site is down.
The backbone interface is physically up, but the IS-IS adjacency
to SNVAng is not established.
```

### Incomplete report

```text
The new site seems offline from Atlanta.
```

### Partially misleading report

```text
It looks like the physical link to the new Yuma router may be down.
```

These variants allow the same ground-truth fault to be evaluated under different user-report quality conditions.

---

## 22. Difference Between User Ticket and Ground Truth

This distinction is important.

### User ticket

The user ticket represents:

```text
what the user or operator observes and reports
```

It may be:

- incomplete
- vague
- accurate
- misleading
- technically detailed

### Ground truth

Ground truth represents:

```text
what is actually wrong in the network
```

For this scenario:

```text
Ground truth:
IS-IS disabled on yumang eth0
```

The AI agent should ideally infer this root cause from the available network state and user report.

---

## 23. Recovery

The recovery action is:

```text
ip router isis NIKA
```

Applied to:

```text
yumang
interface eth0
```

Equivalent configuration:

```text
configure terminal
interface eth0
ip router isis NIKA
end
```

---

## 24. Recovery Script

Use:

```text
scripts/04_recover_and_verify.sh
```

Run:

```bash
./scripts/04_recover_and_verify.sh <SESSION_ID>
```

Example:

```bash
./scripts/04_recover_and_verify.sh \
20260917-144219-d8f5f8
```

---

## 25. Important Recovery Behaviour

One important observation from this experiment is:

```text
IS-IS neighbour Up
```

does not necessarily mean:

```text
full forwarding recovery completed
```

During the first recovery attempt, the adjacency returned to `Up` before all IS-IS routes had been reinstalled.

Therefore recovery validation must check several stages:

```text
configuration restored
        ↓
adjacency restored
        ↓
link-state database synchronised
        ↓
SPF recalculated
        ↓
routes installed
        ↓
forwarding restored
```

The final recovery script therefore waits for routing convergence instead of relying on a fixed short delay.

---

## 26. Recovery Success Criteria

Recovery is considered complete only when all of the following are true.

### 26.1 IS-IS adjacency

```text
yumang -> snvang = Up
```

### 26.2 YUMAng relearns remote routes

For example:

```text
10.255.0.1 ... proto isis
```

must reappear in YUMAng's routing table.

### 26.3 Existing topology relearns YUMAng

Existing routers must relearn:

```text
10.255.0.13/32
```

and the new site's edge network:

```text
10.254.0.48/30
```

### 26.4 Router connectivity restored

```text
atlam5 -> 10.255.0.13
```

Expected:

```text
0% packet loss
```

### 26.5 Host connectivity restored

```text
pc_atlam5 -> 10.254.0.50
```

Expected:

```text
0% packet loss
```

---

## 27. Final Recovery Result

The final recovery validation succeeded.

The recovery script reported:

```text
[PASS] IS-IS adjacency restored
[PASS] YUMAng remote IS-IS routes restored
[PASS] Existing network relearned YUMAng loopback
```

Router-to-router test:

```text
atlam5 -> 10.255.0.13
3 transmitted
3 received
0% packet loss
```

Host-to-host test:

```text
pc_atlam5 -> 10.254.0.50
3 transmitted
3 received
0% packet loss
```

Therefore the complete fault lifecycle was successfully demonstrated:

```text
Healthy
→ Fault
→ Impact
→ Diagnosis
→ Recovery
→ Validation
```

---

## 28. Evidence Files

The `evidence/` directory contains terminal outputs captured during the experiment.

### Original baseline

```text
01_original_baseline.txt
```

Shows the original NIKA Abilene topology operating normally.

### Extended healthy state

```text
02_extended_healthy.txt
```

Shows:

- YUMAng interfaces
- YUMAng routes
- IS-IS neighbours
- end-to-end reachability

### Fault evidence

```text
03_fault.txt
```

Shows:

- pre-fault adjacency
- fault injection
- adjacency failure
- route loss
- connectivity failure

### Final recovery

```text
04_recovery_final.txt
```

Shows:

- adjacency restoration
- route restoration
- remote route relearning
- final successful pings

### Recovery investigation

Additional diagnostic evidence may include:

```text
04_recovery_initial_too_early.txt
05_recovery_convergence_diagnosis.txt
```

These demonstrate the distinction between adjacency recovery and full forwarding convergence.

---

## 29. Recommended Client Demo Flow

A short client demo can follow this sequence.

### Step 1 — Show the extended topology

Run:

```bash
uv run nika session containers \
--session_id <SESSION_ID>
```

Point out:

```text
yumang
pc_yumang
```

Explain:

> The original NIKA Abilene topology contains 12 routers and 12 edge hosts. We extended the source topology with a synthetic YUMAng site, resulting in 13 routers and 13 hosts.

### Step 2 — Show healthy IS-IS

Run:

```bash
uv run nika exec \
--session_id <SESSION_ID> \
yumang \
"vtysh -c 'show isis neighbor'"
```

Expected:

```text
snvang eth0 L2 Up
```

Explain:

> The new router successfully participates in the existing IS-IS Level-2 domain.

### Step 3 — Show healthy connectivity

Run:

```bash
uv run nika exec \
--session_id <SESSION_ID> \
pc_atlam5 \
ping -c 3 10.254.0.50
```

Expected:

```text
0% packet loss
```

### Step 4 — Inject the fault

Run:

```bash
./scripts/03_inject_and_verify_fault.sh <SESSION_ID>
```

Explain:

> We disable IS-IS only on YUMAng's backbone interface. The interface itself remains physically up, but routing information can no longer be exchanged correctly.

### Step 5 — Show the impact

Show:

```text
IS-IS neighbour lost
remote routes disappear
remote ping fails
```

### Step 6 — Show ground truth and user ticket

Open:

```text
docs/ground_truth.json
docs/user_tickets.json
```

Explain:

> The ground truth stores the actual fault, while the user ticket represents what a user or operator reports. Different report qualities can be used with the same underlying fault.

### Step 7 — Recover

Run:

```bash
./scripts/04_recover_and_verify.sh <SESSION_ID>
```

Show:

```text
adjacency restored
routes restored
connectivity restored
```

---

## 30. How This Supports AI-Agent Evaluation

This scenario can support multiple evaluation dimensions.

### Fault detection

Did the agent recognise that the network is unhealthy?

### Localisation

Did the agent identify:

```text
device = yumang
interface = eth0
```

### Root-cause analysis

Did the agent identify:

```text
IS-IS disabled on the backbone interface
```

### Report interpretation

Can the agent diagnose the same fault when the user ticket is:

- detailed
- vague
- incomplete
- misleading

### Recovery recommendation

Can the agent recommend restoring:

```text
ip router isis NIKA
```

on:

```text
yumang eth0
```

### Validation

Can the agent distinguish between:

```text
adjacency recovery
```

and:

```text
complete routing and forwarding recovery
```

---

## 31. Reproducibility

The scenario is designed to be reproducible.

The intended process is:

```text
clean NIKA repository
        ↓
run topology-extension script
        ↓
deploy isp_abilene
        ↓
verify healthy state
        ↓
inject controlled fault
        ↓
capture evidence
        ↓
recover
        ↓
verify recovery
```

No manual Docker container creation is required.

This makes the scenario suitable for:

- repeated benchmark runs
- automated validation
- future AI-agent experiments
- comparison between troubleshooting methods

---

## 32. Known Practical Considerations

### Multiple NIKA sessions

Running many Kathara/NIKA environments simultaneously can consume significant Docker resources.

For this reason, old sessions should be closed before running a fresh benchmark.

Check sessions:

```bash
uv run nika session ps
```

Close an old session:

```bash
uv run nika session close \
--session_id <SESSION_ID>
```

### Recovery convergence time

Do not assume a fixed short delay is always sufficient.

IS-IS recovery may happen in stages:

```text
adjacency
→ LSDB synchronisation
→ SPF calculation
→ RIB installation
→ forwarding
```

The final recovery script therefore checks actual conditions rather than relying only on `sleep`.

---

## 33. Useful Commands

### List sessions

```bash
uv run nika session ps
```

### List containers

```bash
uv run nika session containers \
--session_id <SESSION_ID>
```

### Check YUMAng addresses

```bash
uv run nika exec \
--session_id <SESSION_ID> \
yumang \
ip -br addr
```

### Check YUMAng routes

```bash
uv run nika exec \
--session_id <SESSION_ID> \
yumang \
ip route
```

### Check IS-IS neighbour

```bash
uv run nika exec \
--session_id <SESSION_ID> \
yumang \
"vtysh -c 'show isis neighbor'"
```

### Check IS-IS database

```bash
uv run nika exec \
--session_id <SESSION_ID> \
yumang \
"vtysh -c 'show isis database'"
```

### Check IS-IS routes

```bash
uv run nika exec \
--session_id <SESSION_ID> \
yumang \
"vtysh -c 'show isis route'"
```

---

## 34. Suggested Git Commit

A suitable commit message is:

```text
feat: extend Abilene topology with YUMAng IS-IS fault scenario
```

A more detailed commit body could be:

```text
- add synthetic YUMAng router and edge host
- connect YUMAng to SNVAng
- validate IS-IS Level-2 convergence
- add healthy-state verification
- add reproducible IS-IS interface fault
- add recovery and convergence validation
- add ground truth and user-ticket variants
- add captured evidence and demo documentation
```

---

## 35. Final Result

This deliverable demonstrates a complete reproducible troubleshooting scenario built on top of NIKA.

The final scenario includes:

```text
Topology extension
        ✓

New router
        ✓

New host
        ✓

IS-IS integration
        ✓

Healthy end-to-end connectivity
        ✓

Controlled fault injection
        ✓

Adjacency loss
        ✓

Route withdrawal
        ✓

Connectivity failure
        ✓

Known ground truth
        ✓

Multiple user-report variants
        ✓

Configuration recovery
        ✓

Route reconvergence
        ✓

End-to-end connectivity recovery
        ✓
```

The scenario is therefore ready to be used as a benchmark building block for evaluating AI-based network troubleshooting agents.
