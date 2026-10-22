# Configuration changes and client demonstration

The validator executes native scenario definitions and restores them within its temporary lab. The concrete changes are:

| Parameter on Laptop0 | Healthy | Fault | Repair |
|---|---|---|---|
| Default gateway | 172.16.20.1 | 172.16.20.99 | `ip route replace default via 172.16.20.1` |
| OUTPUT ICMP rule to 192.168.100.1 | Tagged rule absent | Tagged DROP rule present | Delete precisely the `haosenpeng-compound-icmp` rule |

The original scenario's DROP rule matches ICMP to that destination, not every protocol. Injection checks before insertion and remains idempotent. Restoration removes only the experimental rule and does not flush the OUTPUT chain.

## Suggested client flow

1. Display the actual Kath3 diagram and explain the 32-device scope and selected demonstration paths.
2. Run `python3 tools/validate_client_demo.py --case compound`. Show healthy-state verification before injection.
3. Explain the gateway and filter changes when the compound stage is recorded. Compare the unaffected PC4 control.
4. Show the automatic gateway-only repair stage. PC4 recovers, but Router2 remains blocked. The tagged filter counter supplies additional evidence.
5. Show full recovery and cleanup, then open the generated JSON evidence.
6. Present a real three-cycle report from rehearsal and discuss the next topology/protocol priorities with the client.

For a manually paced, interactive version, use the existing [compound-fault walkthrough](../haosenpeng-compound-fault.md), which documents device commands and both repair orders. Do not reuse another team member's running lab. The new suite deliberately creates its own temporary copy.

NIKA/SADE execution should be described as pending unless the team supplies a verified new agent run. The progress slides' integration checkpoint requires an actual run trace; a successful manual network test does not satisfy it.
