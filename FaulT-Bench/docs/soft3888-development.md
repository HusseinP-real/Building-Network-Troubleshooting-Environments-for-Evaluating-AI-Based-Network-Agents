# SOFT3888 development and validation

## Scope and status

The first deliverable is `Kath5_Jiayuan_75Devices` (75 devices, 43 collision
domains). It passed two fresh full normal/fault/recovery cycles before the
41-device Clos prototype was built and tested. That prototype did not meet
the required 75–100 device range and is superseded as Topology 2 by
`NIKA_Clos_Jiayuan_92Devices` (92 devices, 228 collision domains). The latter
exports the existing NIKA DCClosService(l) reference (88 devices) and adds
four service/management nodes. See its own reports for actual validation. No LLM result is implied by a lab-validation
report. Paid SADE runs require user-supplied API credentials.

Implemented in this development pass:

- Correct the R1/R2 collision-domain A mismatch: R2 uses 12.1.1.2/8 and
  advertises 12.0.0.0/8, matching R1. Remove R3's unused duplicate 30/8 address
  and advertisement; R1 retains that prefix. Device/link counts are unchanged.
- Start authoritative Internal DNS and a real HTTP page on intapp1 from
  persistent startup configuration. Explicit service-control scripts support
  repeatable fault injection and recovery without editing the healthy base.
- Management zone: mgmt2 receives UDP syslog on 1514 and exposes read-only
  `/health` and `/events` on TCP 9100. Only sources in 192.168.241.0/24 may
  read this HTTP endpoint. This is an isolated lab management service, not a
  production authentication system. mgmt3 runs active DNS/HTTP probes.
- Four custom faults in `dataset/jiayuan75_Q/custom/`, a separate manifest,
  strict baseline/post-injection checks, and machine-readable repair sections.
- Explicit role inventory for SADE/MCP/ReAct, without changing upstream SADE
  files or renaming existing devices. Custom reachability uses fixed destinations declared in roles.json and at most
  four concurrent execs. All agents use the same sampling; this is not an exhaustive matrix.

## Runtime prerequisites discovered in this cloud machine

1. Docker 28.4.0 uses **vfs**. The original ~536/547 MB images cannot fit 75
   complete container copies in the 32 GiB disk. The new explicit host image
   uses the full Python standard library, and the flattened router image is ~392 MB. The router keeps the
   exact original FRR 10.5.3 binaries from a digest-pinned upstream image.
   Hosts use a digest-pinned Debian 12 base and signature-verified APT packages.
The first full-image retry also exceeded this machine's actual vfs storage
   allocation despite its apparent image-size estimate. On vfs, use
   `python tools/prepare_soft3888_runtime.py`: it creates per-device root images
   (~6/10 MB) and one read-only `/usr` tree per role. Kathara's supported
   explicit volume mounts share program bytes; `/etc`, `/var`, `/run`, routes,
   processes and service data remain per-device. Source image IDs, device-image
   IDs and a SHA-256 tree digest are checked before deployment. Device-specific
   application scripts are under writable `/opt/soft3888`, not shared `/usr`.
   Diagnostic commands run as container root; optional non-root tools relying
   on file capabilities are not validated by this copy-based runtime.
2. The official Kathara network plugin requires `/dev/net/tun`. Its absence
   blocked the initial run; the standard device node was restored in this
   machine. On other hosts this is an administrator prerequisite.
3. Use **umask 022 while Kathara packs/deploys lab files**. With cloud umask
   077, PyFilesystem packs directories as 700; copying the device tree can
   make `/` unsearchable by FRR/dnsmasq users. The deployment worker sets 022.
4. This Python installation provides Kathara's API, not a `kathara` CLI.
   The new validator uses the actual supported API throughout.

Images are built with:

```sh
python tools/build_soft3888_images.py
python tools/prepare_soft3888_runtime.py  # vfs-backed machines
```

The builder reuses existing images. `--rebuild` refreshes them explicitly.
It does not prune unrelated images, containers or caches. When the cloud
proxy is configured, the builder resolves its hostname for the build network
and temporarily mounts the public CA bundle; TLS and APT signatures remain
verified. No credentials or environment dumps are written to the repository.
APT versions may advance on a later rebuild; preserve the image ID and
installed versions in an experiment's evidence when reproducing a result.

## Execute validation

From the repository root, use the prepared Python environment:

```sh
source /workspace/venvs/faultbench/bin/activate
python -m unittest discover -s tools -p 'test_*.py'
python tools/validate_soft3888.py Kath5_Jiayuan_75Devices --repeats 2
python tools/validate_soft3888.py NIKA_Clos_Jiayuan_92Devices --repeats 2
python -m faultbench bench --manifest faultbench/benchmarks/jiayuan75.csv --agents sade --dry-run
```

The validator copies the topology to a unique temporary directory and
registers a unique API lab name. It checks disk capacity before deployment,
waits for actual connectivity/services, then validates each fault, repeated
injection, explicit recovery and the complete healthy baseline. Each cycle
is a fresh deployment; it does not operate on somebody else's running lab.
Reports include source/scenario hashes, image IDs/digests, raw outputs, real
exit codes, failed convergence attempts, and exact-lab cleanup results.
Reports are saved after each stage, including failures. A deployment worker
is killed before cleanup on timeout, avoiding late thread-created leftovers.

Evidence goes to `docs/validation/soft3888/`. `passed: true` is meaningful only
for the precise configuration hashes in that report. Historical failed
attempts are retained and must not be counted as successful acceptance.

## Evaluation and reference boundaries

Custom scenarios do not modify `base80.csv`, the published dataset index,
`final_results/`, or historical scores. `[FIX]` remains the human/judge repair
reference. Additional `[RECOVERY]` and `[RECOVERY-CHECK]` sections are executed
by the standalone validator; the agent benchmark remains diagnostic-only.
The main harness now honors provided `[PRE-CHECK]` blocks, requires nonempty
post-injection checks, and refuses to run an agent after failed injection.
Legacy scenarios without a PRE-CHECK retain their old settle-only baseline;
that is not a claim of validated health.

Strict checks deliberately fail previously advisory/unknown expectations.
Empty/zero grep results accept grep's no-match status only, not timeouts or
arbitrary errors. New custom scenarios declare `Validation: strict`, so a
malformed check line cannot silently disappear.

References: repository-local FaulT-Bench scenarios; the SADE checkout at
`aa8488a09ddb3a57e08f8137afd04bc87886e734`; NIKA's OSPF enterprise and Clos
implementations contained there. Current upstream NIKA has different APIs;
no claim of current-upstream native compatibility is made. Access to
YasodGinige/OwnTopologies was unavailable during inspection. The supplied
arXiv identifier and the current upstream README's identifier differ and
still require bibliographic verification.

## EIGRP scenario decision based on actual experiments

The initial candidate removed R21's Internal LAN `network` statement. In the
pinned FRR 10.5.3 runtime, R12 retained its learned forwarding entry and the
full-lab ping still succeeded. A separate three-device experiment confirmed
that removing the statement and restarting R21 also left the peer's stale
entry. Neither attempt is counted as successful outage injection. Evidence:
`validation/soft3888/eigrp-runtime-behavior.json` and the failed full-lab report.

The formal case is therefore **R21 AS101 vs R12 AS100**, not missing-LAN
advertisement. A three-device real-network experiment demonstrated adjacency
loss, intact local-LAN connectivity, and recovery after restoring AS100:
`validation/soft3888/eigrp-as-mismatch-behavior.json`. The formal 75-device
validator separately tests this case. The ticket reports a control-plane
alarm and does not invent a total application outage; cached forwarding may
continue working. Injection changes only the copied container configuration
and reloads FRR; repeat injection is guarded and a fresh deployment remains
AS100. The old R13/Extended sample is retained as historical work, not claimed
as a validated 75-device hot-withdrawal scenario.


## Cold-start and inter-area stability

A later fresh deployment exposed datastore-lock messages during FRR's parallel
initial configuration and EIGRP hello scheduling delays under excessive probe
fanout. Address the extension interfaces before starting FRR, disable unused
ospfd on R12, and reapply the integrated configuration serially on the EIGRP
routers. Readiness is based on real probes, not a fixed sleep. The custom MCP
inventory now uses a bounded four-command fanout and fixed destinations; it
preserves the upstream packet-result schema and does not modify SADE source.

This kernel also rejects dummy interfaces. R12/R13 retain their planned stub
prefixes using isolated veth pairs only when dummy creation is unavailable.
No extra Kathara devices or collision domains are added.

Cross-region testing found R8 sometimes missing EIGRP-side external prefixes
even while its virtual-link neighbor was Full. A runtime trial of a default
via its existing upstream R5 (58.1.1.1) restored Branch B DNS/HTTP and reverse
traffic. This fallback is now explicit in r8.startup; specific OSPF routes keep
priority. This documents observed behavior and a validated workaround, not a
claim that the precise upstream FRR defect has been proven. Evidence is in
`validation/soft3888/r8-fallback-diagnosis.json`. The trial's surrounding run
was aborted and is not counted as a pristine acceptance run. The strengthened
baseline includes Branch B/Internal traffic and DNS/HTTP, both DMZ web hosts,
and a remote stub-prefix check.

## Agent credentials and context

The agent context checks were executed without inference: SADE's own skill
context and the separate CC-Baseline directory both pass isolation checks.
Empty read-only `.git` sandbox guards under `/tmp` and `/workspace` are no
longer misclassified as real repositories; nonempty Git metadata is still
handled conservatively. No instruction files or user memories were removed.

The current cloud process has no Anthropic/OpenAI API key. `load_env` accepts
`FAULTBENCH_OPENAI_API_KEY` as an in-memory alias for the SDK's standard name,
because the cloud proxy reserves `OPENAI_` secret target names. Existing
`OPENAI_API_KEY` bindings take precedence. Enter values securely in environment
settings, never in chat or committed files. SADE/CC need Anthropic; judging and
ReAct need OpenAI. Tool smoke tests do not spend model tokens and are not agent
performance evaluations. No model score should be reported until inference
and judge calls have actually executed.


## Deliverables and compatibility

| Deliverable | Protocol/service diversity | Core faults | Baseline checks |
|---|---|---|---|
| Kath5_Jiayuan_75Devices | OSPF, EIGRP, DNS, HTTP, syslog/management API | OSPF missing advertisement, EIGRP AS mismatch, wrong DNS A record, stopped HTTP | 31 |
| NIKA_Clos_Jiayuan_92Devices | retained NIKA 4-Pod Super-Spine/Spine/Leaf eBGP, 4 DNS, 28 HTTP, added DHCP/HAProxy/management | BGP AS mismatch, outbound prefix filtering, wrong DHCP gateway, wrong backend ports | 99 |

Each has its own four-case CSV manifest, explicit role inventory, persistent
healthy service configuration, strict checks, Ground Truth and runtime repair.
The second topology's design and run commands are in
[its README](../topology_kathara/NIKA_Clos_Jiayuan_92Devices/README.md).
An additional NIKA92 compound case is kept in a separate manifest/experiment recipe;
it does not change the core four-case evaluation set. Run it using:

```sh
python tools/validate_soft3888.py NIKA_Clos_Jiayuan_92Devices --experiment faultbench/experiments/nika92_compound.json --repeats 2
```

The compound validator explicitly checks both partial repair orders, not just
the combined outage. Consult [the results index](soft3888-validation-results.md)
for its executed status. Core reports are separate from baseline-only and
compound experiment reports. Source, case and optional recipe hashes identify
the precise configuration tested; harness hashes describe the validator at run
time. Later documentation/optional experiment support does not retroactively
turn earlier failures into passes.

`[TRIGGER]` models an explicit stimulus such as DHCP renewal after server
configuration changes. The main diagnostic harness runs it after injection
and refuses inference if it fails. The validator runs it again after repair.
Repair sections are for reproducibility; benchmark agents remain diagnostic,
and do not receive permission to alter the live network.

First-topology DNS tests explicitly query the intended resolver; they do not
assert every legacy endpoint has a system default resolver. Its management
implementation is syslog plus restricted read-only HTTP and active probes;
SSH, SNMP and InfluxDB deployment are not claimed. The NIKA extension has explicit dual resolvers and client_0 acquires real DHCP
options while preserving its original address.

FaulT-Bench scenario parsing/manifests and actual SADE MCP diagnostic tools
have been exercised. The adapter preserves the pinned SADE checkout and
supports custom device names through explicit roles. NIKA provides design and
taxonomy references; upstream native loading/benchmark equivalence and model
accuracy still require separate integration evaluation. A successful network
acceptance test is not a SADE diagnosis score.

The excluded prototype's source and validation bundle remain local.
The current publication passed 47 tests in both the working checkout and a
separate export of indexed files without the prototype. Actual checks and
their reproduction limits are in
[release-verification.json](validation/soft3888/release-verification.json).
The original 3960 archived-run metric reproduction passed; this neither adds
new model runs to those results nor supplies scores for the custom topologies.

Cloud install/start instructions and API secret requirements were saved as a
configuration draft. The proxy-secret destinations added are
`api.anthropic.com` and `api.openai.com`. Saving the draft does not publish it
or create key values. Review/save the environment settings and publish before
relying on the configuration in a fresh task; fresh-task restoration is not
claimed as tested.


## Topology 2 correction and direct reference provenance

The 41-device prototype was undersized and is not an accepted deliverable.
Its source and reports remain local for history and reuse of service lifecycle
components. The replacement invokes the existing pinned NIKA constructor,
retains all 88 devices/228 links and router/AS/address values, then adds four
nodes on existing LANs (92 total). This is not the prototype with extra
clients. See reference-provenance.json and the independent reference-contract
tests for the exact export/adaptation boundaries. Four new case IDs and a
new nika92.csv manifest prevent old prototype results being counted as new
acceptance. Network results and LLM evaluation remain separate.

The replacement NIKA92 reference-contract suite brings the full regression
suite to34 tests (including two real-ping error parsing regressions). Actual output and the four-case SADE dry-run plan are saved
in [nika92-static-checks.json](validation/soft3888/nika92-static-checks.json).
The older test count is historical; see the release verification for the
current 47-test run. No upstream SADE source was edited.

The NIKA source assigns AS65000 to every Super-Spine, and the extension retains it.
It supports client-to-service paths but does not supply all external-client
prefixes to other Super-Spines through the fabric. A direct ping/route/HTTP
experiment confirms this inherited boundary. It is a documented normal-state
limitation, not an injected fault. Core NIKA92 reports used the earlier MCP
smoke check, which validated inventory and a representative successful ping
but did not reject upstream unknown ping parsing. The supplemental experiment
uses the strengthened adapter/smoke check; consult its own report and harness
hash for actual parseability and status counts. No unparsed result is turned
into an assumed successful ping.

NIKA92 core acceptance: two fresh deployments passed all four fault states,
repeated injection, recovery, the full99-check baseline after each repair,
and one-uplink failure/recovery. Reports: `NIKA_Clos_Jiayuan_92Devices-cycle1-soft3888-334b26835113.json`
and `NIKA_Clos_Jiayuan_92Devices-cycle2-soft3888-d44d6583784d.json` in the
evidence directory. Both cleanup results passed. The supplemental compound
run and strengthened MCP status parsing have separate evidence; they are not
substituted for the four-case core cycles.


NIKA92 supplemental acceptance also passed on one further fresh deployment:
`NIKA_Clos_Jiayuan_92Devices-cycle1-soft3888-b5401538db83.json`. Both partial
repair orders, final99-check baseline and cleanup passed. Updated MCP tools
recorded71 ok /7 down /0 unknown from78 actual sampled paths. The7 down paths
are the documented inherited external-client routing boundary. The pinned
upstream SADE source remains unchanged. Current acceptance links are in
[acceptance-index.json](validation/soft3888/acceptance-index.json); the old
41-device acceptance bundle is retained locally and excluded from publication.
