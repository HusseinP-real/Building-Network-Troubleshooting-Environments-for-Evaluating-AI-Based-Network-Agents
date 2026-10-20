# XP Learning Summary and Individual Learning Plan

**Unit:** SOFT3888 Software Development Project  
**Project ID:** P20  
**Project:** Building Network Troubleshooting Environments for Evaluating AI-Based Network Agents  
**Submission type:** Individual learning summary  
**Date:** 14 August 2026

> This document records my individual understanding of Extreme Programming (XP) and the tools, knowledge, and skills assigned to me for Project P20. The wider team allocation is maintained separately.

## 1. Project Context

Project P20 aims to build a realistic evaluation framework for AI-based network troubleshooting agents. The project will use **Kathara** to emulate enterprise network topologies and create reproducible network faults. It will also simulate reports from end users, network engineers, and expert operators, with different levels of accuracy and technical detail. Each scenario will contain ground-truth annotations describing whether a fault exists and, if so, its type and location. These environments will then be used to evaluate an AI troubleshooting agent such as **SADE**, while extending or complementing the existing **NIKA** network-agent benchmark.

The project therefore combines four areas: network emulation, fault and dataset construction, LLM-agent evaluation, and reproducible software engineering.

## 2. What I Learned About Extreme Programming

Extreme Programming is an agile software development approach designed for projects where requirements may change and frequent feedback is valuable. Rather than completing a large design before implementation, an XP team delivers small working increments, tests continuously, collaborates closely with the customer, and improves the design through refactoring.

### 2.1 XP Values

| Value | Meaning in practice | Application to P20 |
|---|---|---|
| **Communication** | Share requirements, progress, design decisions, and blockers frequently. | Confirm scenario realism, fault definitions, and evaluation expectations with the client and team. |
| **Simplicity** | Implement the simplest solution that meets the current requirement. | Begin with one small topology, one reproducible fault, and one evaluation path before adding complex enterprise scenarios. |
| **Feedback** | Use tests, demonstrations, client review, and team review to learn quickly. | Demonstrate executable network scenarios and inspect agent traces and scores every iteration. |
| **Courage** | Raise risks, remove weak solutions, and revise assumptions when evidence shows a problem. | Report unreliable ground truth, unrealistic faults, unstable environments, or misleading metrics early. |
| **Respect** | Value each member's contribution and protect the shared codebase. | Review constructively, document decisions, follow coding standards, and avoid breaking reproducible experiments. |

### 2.2 XP Practices Relevant to the Project

- **Planning game and user stories:** translate client goals into small, prioritised stories with testable acceptance criteria.
- **Small releases:** deliver a runnable vertical slice each week instead of waiting for a complete benchmark.
- **Simple and incremental design:** add topology types, faults, personas, and metrics only after the core pipeline works.
- **Pair programming:** work with another programmer on difficult topology definitions, fault injection, agent integration, or evaluation logic.
- **Test-first development:** define the expected healthy and faulty network state before implementing the scenario.
- **Continuous integration:** automatically run formatting, unit tests, schema checks, and lightweight scenario validation for every pull request.
- **Refactoring:** remove duplicated topology or fault configuration while preserving behaviour through regression tests.
- **Collective ownership:** keep code and documentation understandable so any team member can improve a scenario.
- **Coding standards:** use consistent Python style, configuration schemas, naming conventions, and Git practices.
- **Customer involvement:** review scope, scenario realism, priorities, and evidence with the client every week.
- **Sustainable pace:** plan achievable weekly work and expose overload or blockers through tracking rather than relying on last-minute effort.

### 2.3 Roles Used by Our Team

The roles rotate during the project so that members experience both technical and coordination responsibilities.

| Role | Main responsibilities |
|---|---|
| **Tracker** | Tracks stories, estimates, progress, velocity, blockers, risks, and whether completed work has evidence. Keeps the project board and status information current. |
| **Manager** | Coordinates the iteration, meetings, resources, and task ownership; removes organisational blockers; ensures that the XP process is followed. The manager supports the team rather than acting as a command-and-control boss. |
| **Customer Liaison** | Maintains communication with the client, prepares questions, clarifies user stories and acceptance criteria, records decisions, and prevents unconfirmed assumptions from becoming requirements. |
| **Programmer** | Designs, implements, reviews, tests, and refactors the software and experiment configurations. Works in small increments and shares ownership of the codebase. |
| **Tester** | Defines acceptance and regression tests, checks reproducibility, verifies fault injection and ground truth, records defects, and confirms that completed stories satisfy their criteria. |
| **Doomsayer** | Challenges optimistic assumptions and identifies failure modes, dependencies, safety issues, schedule risks, weak evidence, and misleading evaluation conclusions. Each concern should be accompanied by evidence or a practical mitigation. |

### 2.4 How I Would Apply XP to P20

A suitable first vertical slice is:

1. Define a user story for evaluating one troubleshooting case.
2. Create a small Kathara topology with a known healthy state.
3. Define an acceptance test for connectivity and expected routing behaviour.
4. Inject one reproducible fault and verify its type and location.
5. Create a small set of reports from different user personas, including an incomplete or inaccurate report.
6. Store machine-readable ground truth for the scenario.
7. Run a baseline agent and capture its actions, diagnosis, and final answer.
8. Score the result with deterministic metrics and review the trace.
9. Demonstrate the slice to the client, collect feedback, and use it to plan the next iteration.

This workflow gives the team early evidence that the environment, dataset, agent interface, and evaluation logic can work together.

## 3. Tools, Knowledge, and Skills I Need

### 3.1 Technical Learning Areas

| Area | What I need to learn | Why it is needed |
|---|---|---|
| **Computer networking** | TCP/IP layers, subnetting, switching, routing, DNS, DHCP, NAT, firewalls, packet paths, and common diagnostic commands. | Faults and ground truth must reflect real network behaviour. |
| **Linux troubleshooting** | Network namespaces, interfaces, routes, processes, logs, permissions, and tools such as `ip`, `ping`, `traceroute`, `ss`, `dig`, and `tcpdump`. | Kathara devices are containerised Linux environments and the agent will inspect them using operational tools. |
| **Docker and Kathara** | Container networking, Kathara lab structure, device startup configuration, topology deployment, command execution, cleanup, and reproducibility. | Kathara is the main network-emulation platform required by P20. |
| **Python and configuration** | Python modules, subprocess/API integration, structured logging, type hints, error handling, and YAML/JSON schemas. | Automation is required for scenario generation, fault injection, agent runs, and result collection. |
| **NIKA and SADE** | Benchmark structure, agent interface, scenario/fault representation, tool access, run lifecycle, traces, and output format. | P20 must complement the existing benchmark and evaluate an AI troubleshooting agent rather than build an isolated demo. |
| **LLM agents** | Tool use, observation-action loops, prompt/context design, stopping conditions, error recovery, and safe execution boundaries. | The evaluation must distinguish agent reasoning failures from environment or tool failures. |
| **Dataset and benchmark design** | Scenario taxonomy, ground-truth schema, difficulty levels, train/test separation, versioning, leakage prevention, and reproducibility. | The central deliverable is an evaluation dataset/framework, so the cases must be comparable and auditable. |
| **User-report simulation** | Persona definition, report accuracy, missing information, ambiguity, contradictions, and controlled generation. | Reports must represent end users, engineers, and experts without accidentally revealing the answer. |
| **Evaluation metrics** | Fault-existence accuracy, type classification, localisation, false-positive/negative rates, task success, tool efficiency, step count, time/cost, and robustness by report quality. | A single LLM judge or final-answer score would not provide sufficient diagnostic evidence. |
| **Testing and CI** | `pytest`, fixtures, unit/integration tests, deterministic seeds, schema validation, GitHub Actions, and regression testing. | Network labs and agent runs contain multiple failure sources and must remain reproducible as the benchmark grows. |
| **Git and documentation** | Branches, pull requests, reviews, issues, project board, README files, experiment records, and meeting evidence. | XP depends on collective ownership, frequent integration, and transparent progress. |
| **Security and research ethics** | Credential handling, sandboxing, least privilege, safe fault execution, anonymisation, and limitation statements. | Agents execute network tools, and evaluation results should not overstate reliability or expose secrets. |

## 4. Tasks Assigned to Me for Research and Learning

| Priority | Personal task | Evidence / output | Target |
|---|---|---|---|
| **P0** | Study the P20 brief and inspect the current NIKA and SADE repositories. Map the scenario, fault, agent, trace, and evaluation components. | One-page architecture note and a glossary of project terms. | Week 2 |
| **P0** | Set up Docker and Kathara, then deploy and clean up a minimal lab successfully. | Reproducible setup notes, commands, and screenshots/logs of a working lab. | Week 2-3 |
| **P0** | Refresh networking fundamentals and practise diagnosing connectivity, routing, DNS, and interface failures in Linux. | Troubleshooting checklist linking symptoms, commands, observations, and likely causes. | Week 3 |
| **P0** | Design one minimal benchmark case with a healthy baseline, one injected fault, and explicit ground truth. | Versioned scenario folder plus a machine-readable ground-truth file. | Week 3 |
| **P1** | Define a user-report schema and write example reports for an end user, network engineer, and expert operator at different accuracy levels. | Persona/report specification and a small reviewed example set. | Week 3-4 |
| **P1** | Propose an evaluation matrix covering diagnosis, localisation, false reports, tool use, efficiency, robustness, and reproducibility. | Metric definitions with calculation method and limitations. | Week 4 |
| **P1** | Run or integrate a baseline agent on the minimal case and capture a structured execution trace. | Run instructions, raw trace, diagnosis, score, and brief failure analysis. | Week 4 |
| **P1** | Add automated checks for schema validity, healthy-state behaviour, successful fault injection, and deterministic cleanup. | `pytest` tests and a lightweight CI workflow. | Week 4-5 |
| **P2** | Review security, cost, and reproducibility risks for agent execution and LLM-based evaluation. | Risk register entries with mitigations and owners. | Ongoing |

## 5. Personal Definition of Done

My research or implementation task is complete only when:

- the result is committed to the agreed GitHub location;
- setup and execution steps can be followed by another team member;
- assumptions, versions, and dependencies are documented;
- the relevant automated or manual tests pass;
- generated data includes a clear schema and provenance;
- results include raw evidence, not only a narrative conclusion;
- limitations and unresolved questions are recorded;
- the work has been reviewed through a pull request or team demonstration.

## 6. Expected Learning Outcome

By completing these tasks, I expect to understand how to construct reproducible network incidents, represent noisy human reports with reliable ground truth, integrate an AI troubleshooting agent, and evaluate it using evidence-based metrics. I will also practise XP through small releases, test-first work, continuous integration, client feedback, shared code ownership, and rotating project roles.

## References

1. Agile Alliance, [Extreme Programming](https://agilealliance.org/glossary/xp/).
2. Kathara, [Lightweight Container-based Network Emulation System](https://www.kathara.org/).
3. Kathara, [Command-line manual](https://www.kathara.org/man-pages/kathara.1.html).
4. NIKA, [A Network Arena for Benchmarking AI Agents on Network Troubleshooting](https://github.com/sands-lab/nika).
5. P20 project brief, *Building Network Troubleshooting Environments for Evaluating AI-Based Network Agents*, School of Computer Science, The University of Sydney, 2026.
