# Independent Enterprise Network Lab

The `haosenpeng` branch contains an independently authored network troubleshooting lab. The previous client benchmark and project-skills documents have been removed from this branch's current tree. They remain in Git history and on the team's other branches.

The lab has **10 routers, 15 switches, 9 endpoints, and 57 links**, with multi-area OSPF, VLANs, STP, VRRP, centralized DHCP/DNS, access policies, and three reversible fault experiments.

## Run

With Docker running, Python 3 and Kathara installed:

```bash
cd enterprise-topology
python3 lab.py build
python3 lab.py start
```

To stop this lab:

```bash
python3 lab.py stop
```

## Documentation

- [Setup, commands, and fault experiments](enterprise-topology/README.md)
- [Topology and addressing design](enterprise-topology/docs/design.md)
- [Recorded runtime validation](enterprise-topology/docs/validation.md)

Recorded validation passed 99 health checks and 20 fault assertions. These reports describe the original local test run; cloning the repository does not start containers or guarantee they are currently running. The backend is an HTTP dependency simulator, and NIKA/LLM evaluation integration is not included.

This branch's removal of the old client files is intentional. Merging it into another branch will propose those deletions there as well.
