"""Read saved test evidence and refresh the client report; never execute tests/models."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/client-delivery"
EVIDENCE = ROOT / "results/delivery"


def counts(passed=0, failed=0, errors=0, skipped=0):
    executed = passed + failed + errors
    total = executed + skipped
    return {
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "skipped": skipped,
        "executed": executed,
        "collected": total,
        "pass_rate": passed / executed if executed else None,
        "execution_rate": executed / total if total else None,
    }


def pct(value):
    return "N/A" if value is None else f"{value:.1%}"


def tex(value):
    escapes = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(escapes.get(c, c) for c in str(value))


def main():
    registry = json.loads((DOCS / "user-stories.json").read_text())
    cases = ET.parse(EVIDENCE / "offline-tests.xml").getroot().findall(".//testcase")
    offline = counts(
        passed=sum(
            not any(c.find(tag) is not None for tag in ("failure", "error", "skipped"))
            for c in cases
        ),
        failed=sum(c.find("failure") is not None for c in cases),
        errors=sum(c.find("error") is not None for c in cases),
        skipped=sum(c.find("skipped") is not None for c in cases),
    )
    browser_text = (EVIDENCE / "browser-tests.tap").read_text()
    workflows = re.findall(r"^    (not ok|ok) \d+ - (.+)$", browser_text, re.MULTILINE)
    browser = {
        **counts(
            passed=sum(status == "ok" for status, _ in workflows),
            failed=sum(status != "ok" for status, _ in workflows),
        ),
        "workflows": [
            {"name": name, "passed": status == "ok"} for status, name in workflows
        ],
        "execution": "real Chrome / real UI and HTTP / MOCK network and model executor",
    }
    live_paths = sorted(EVIDENCE.glob("live-*.json"))
    live = (
        json.loads(live_paths[-1].read_text())
        if live_paths
        else {"cycles": [], "pending": []}
    )
    cycles = live["cycles"]
    console = (
        (EVIDENCE / "live-console.log").read_text()
        if (EVIDENCE / "live-console.log").exists()
        else ""
    )
    live_summary = {
        **counts(
            passed=sum(row["passed"] for row in cycles),
            failed=sum(not row["passed"] for row in cycles),
        ),
        "cycles": cycles,
        "pending": live["pending"],
        "suite_finished": bool(re.search(r"Ran \d+ tests? in", console)),
        "model_evaluation": False,
        "evidence": str(live_paths[-1].relative_to(ROOT)) if live_paths else None,
    }
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    sources = [
        ROOT / "tools/sade_cases.json",
        ROOT / "tools/sade_benchmark.py",
        ROOT / "dashboard/server.py",
    ]
    result = {
        "recorded_at": datetime.now(ZoneInfo("Australia/Sydney")).isoformat(),
        "scope": "Current EnterpriseTopology delivery workflow; not exhaustive testing of every repository or topology",
        "base_revision": revision,
        "working_tree": "Includes local uncommitted changes; base revision alone is not the tested source snapshot",
        "source_sha256": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sources
        },
        "offline": offline,
        "browser": browser,
        "live": live_summary,
        "benchmark": {
            "rerun": False,
            "accuracy": None,
            "client_target": [0.5, 0.7],
            "working_primary_metric": "exact RCA correct / all attempted diagnoses; confirm with client",
            "status": "Not remeasured, as requested by the user",
        },
        "known_limits": [
            "Automatic SADE evaluation is adapted only for enterprise-75; other catalogs are not equivalent to executable automatic benchmarks.",
            "No new model-backed end-to-end evaluation, diagnostic accuracy measurement or paid API cost measurement.",
            "Client UAT, independent installation in the intended client environment, and final sign-off remain pending.",
            "No source-code line/branch coverage percentage, broad performance SLA, full accessibility conformance or cross-browser claim is made.",
            "Offline live-test skips are counted separately from the explicitly opted-in real-network suite; browser parent groups and pytest subtests are not extra test cases.",
        ],
        "fixed_findings": [
            "Repeated paths to the same result file previously inflated attempted counts; resolved paths are now deduplicated.",
            "Malformed saved report shapes previously crashed the report index; invalid entries are now skipped without hiding valid reports.",
        ],
    }
    (DOCS / "test-results.json").write_text(json.dumps(result, indent=2) + "\n")
    rows = [
        ("Offline + HTTP regression", offline),
        ("Browser workflows (MOCK executor)", browser),
        ("Real network cycles (no model)", live_summary),
    ]
    table = "\n".join(
        f"| {name} | {d['passed']} | {d['failed']} | {d['errors']} | {d['skipped']} | {pct(d['pass_rate'])} |"
        for name, d in rows
    )
    markdown = (
        f"""# Delivery validation record

Recorded: {result["recorded_at"]}. Base revision: `{revision}` plus the current local changes. Exact hashes of key sources are in `test-results.json`.

{result["scope"]}.

| Evidence group | Passed | Failed | Error | Skipped | Pass / executed |
|---|---:|---:|---:|---:|---:|
{table}

Offline execution proportion: **{offline["executed"]}/{offline["collected"]} ({pct(offline["execution_rate"])})**. The 11 opt-in live tests are deliberately skipped in the offline command; real-network cycles are reported separately. Do not count these two invocations as different implementations of the same requirement. Browser statistics count leaf workflows only.

Real-network suite finished: **{live_summary["suite_finished"]}**. Pending owned faults in its latest saved evidence: **{live_summary["pending"]}**. A partial/in-progress live record is not a complete-suite claim.

## How to interpret the rates

Pass rate = passed / (passed + failed + errors). Skipped and not-run cases are shown separately. No aggregate rate mixes unit cases, browser workflows, health assertions and network cycles. A 100% rate applies only to the declared executed scope. It does not establish complete requirement coverage, absence of defects or client acceptance. The supplied rubric specifies no mandatory 100% threshold.

## Findings fixed during validation

"""
        + "\n".join("- " + item for item in result["fixed_findings"])
        + "\n\n## Known limits and pending acceptance\n\n"
        + "\n".join("- " + item for item in result["known_limits"])
        + f"""

## Agent accuracy

No benchmark or model request was rerun for this report. The client-reported **50%-70% diagnostic accuracy** is a difficulty target, not the software-test pass threshold. This report does not claim the target was met. Exact RCA over all attempts is the proposed primary interpretation; full correctness and scored-only rates remain separate. Confirm the primary metric and reference experiment with the client.

## Evidence

- `results/delivery/offline-tests.xml` and `offline-tests.log`
- `results/delivery/browser-tests.tap`
- `{live_summary["evidence"]}` and `results/delivery/live-console.log`
- `docs/client-delivery/user-stories.json`: provenance, acceptance criteria, implementation limits and test links
"""
    )
    (DOCS / "test-results.md").write_text(markdown)
    story_md = [
        "# User stories and acceptance criteria",
        "",
        registry["scope_note"],
        "",
    ]
    for story in registry["stories"]:
        story_md += [
            f"## {story['id']} - {story['title']}",
            "",
            story["story"],
            "",
            f"Source: `{story['source']}`. Implementation: `{story['implementation']}`. Client acceptance: `{story['client_acceptance']}`.",
            "",
            *[f"- {criterion}" for criterion in story["acceptance_criteria"]],
            "",
            "Evidence: " + "; ".join("`" + item + "`" for item in story["tests"]),
            "",
        ]
    (DOCS / "user-stories.md").write_text("\n".join(story_md))

    latex_rows = "\n".join(
        f"{tex(name)} & {d['passed']} & {d['failed'] + d['errors']} & {d['skipped']} & {tex(pct(d['pass_rate']))} \\\\"
        for name, d in rows
    )
    story_rows = "\n".join(
        f"{s['id']} & {tex(s['title'])} & {'Client feedback' if s['source'].startswith('client') else 'Team proposal'} \\\\"
        for s in registry["stories"]
    )
    cycle_rows = "\n".join(
        f"{tex(c['scenario'])} & {'Pass' if c['passed'] else 'Fail'} & {'Verified' if c['restored'] else 'Unverified'} & {c['seconds']:.1f} \\\\"
        for c in cycles
    )
    document = (
        r"""\documentclass[10pt,a4paper]{article}
\usepackage[margin=22mm]{geometry}
\usepackage[T1]{fontenc}
\usepackage{lmodern,booktabs,tabularx,longtable,array,xcolor,enumitem,fancyhdr,hyperref}
\definecolor{accent}{HTML}{B74814}
\hypersetup{colorlinks=true,urlcolor=accent,linkcolor=accent}
\pagestyle{fancy}\fancyhf{}\fancyhead[L]{\small P20 Network Troubleshooting Benchmark}\fancyhead[R]{\small Delivery review}\fancyfoot[C]{\thepage}
\setlength{\headheight}{14pt}\setlength{\parindent}{0pt}\setlength{\parskip}{6pt}
\setlist[itemize]{leftmargin=*,itemsep=3pt,topsep=3pt}
\renewcommand{\arraystretch}{1.2}
\begin{document}
{\color{accent}\Large\bfseries Client Delivery and Validation Report}\par
\textbf{SOFT3888\_TU14\_04 \quad | \quad 23 October 2026, Australia/Sydney}\par
\textbf{Status: delivery-review draft; client acceptance pending.}\par
Project title above is a working title. Confirm the formal course project name, recipient, final agreed scope and deployment environment before sign-off.

\section*{1. Delivery position}
The deliverable provides a web interface for inspecting network topologies, selecting fault scenarios and configuring an agent benchmark. The current automatic SADE execution adapter supports \texttt{enterprise-75}. Other displayed topologies have varying manual or catalog support and must not be presented as completed automatic benchmark integrations.

This report records software validation, requirement provenance, limitations and handover actions. At the team's request, no model benchmark was rerun and no new agent accuracy is asserted. Offline fixtures and synthetic model answers are used to test software behavior; they are not agent-performance observations.

\subsection*{Recorded test results}
\begin{tabularx}{\textwidth}{@{}Xrrrr@{}}\toprule
Evidence group & Pass & Fail/error & Skip & Pass rate \\
\midrule
"""
        + latex_rows
        + r"""
\bottomrule\end{tabularx}

Pass rate is passed divided by executed cases (passed + failed + errors). Skipped/not-run work is separate. The supplied rubric does not prescribe a 100\% threshold. A perfect scoped result does not imply complete coverage or client acceptance; failures in core execution, scoring or recovery require particular attention.

"""
        + f"Offline execution proportion: {offline['executed']}/{offline['collected']} ({tex(pct(offline['execution_rate']))}). Browser counts exclude the parent test group; pytest subtests are not additional independent cases.\n"
        + r"""

\subsection*{Evidence and version}
Raw evidence is under \texttt{EnterpriseTopology/results/delivery/}. The companion \texttt{test-results.json} records source hashes, timestamps and individual network cycles. The tested tree includes existing local changes; the base commit alone is not the source snapshot.
"""
        + "\nBase revision: \\texttt{"
        + revision[:12]
        + "}.\n"
        + r"""
\newpage
\section*{2. Requirements and acceptance basis}
The team reported the client's feedback on 23 October: select a topology and fault on the web page, then run a benchmark; intended agent diagnostic accuracy is approximately 50--70\%. The original meeting date/minutes have not been independently verified. Newly documented team proposals are explicitly separate from that feedback.

\begin{tabularx}{\textwidth}{@{}lXl@{}}\toprule
ID & User goal & Provenance \\
\midrule
"""
        + story_rows
        + r"""
\bottomrule\end{tabularx}

\subsection*{Acceptance conditions that matter most}
\begin{itemize}
\item Selecting a topology updates its map and applicable fault catalog, with matching execution support. A topology/fault mismatch must be rejected.
\item For an adapted target, submitted configuration reaches the intended runner. Baseline, actual fault state, results and verified recovery must be traceable.
\item Diagnosis fields, explanations and repair recommendations are scored separately. Wrong or additional root causes must not receive exact-match credit. Unknown judgement remains unknown.
\item A healthy control causes no injection. Redundant failures may preserve application access; state and unaffected-path checks are still required.
\item Full multi-topology automatic evaluation, client UAT and independent installation are not established by passing UI tests.
\end{itemize}

The full story statements, per-story acceptance criteria, current implementation limits and named regression evidence are in \texttt{user-stories.md} and \texttt{user-stories.json}. No overall story-completion percentage is asserted because the final client-approved denominator and acceptance decisions are pending.

\newpage
\section*{3. Test approach and observed findings}
\subsection*{Software contracts and HTTP integration}
Independent literal diagnosis examples exercise correct answers, wrong interfaces, contradictory scalar/structured fields, duplicate causes, malformed outputs, healthy false positives and missing quality judgements. Summary tests cover empty data, all-attempt denominators, separate configurations and duplicate input paths. HTTP tests use real loopback servers, validate configuration and scope, preserve saved report identity, reject malformed input and prevent unsupported automatic targets from launching the enterprise runner.

\subsection*{Browser workflows}
Real Chrome exercises the actual UI/HTTP/lease coordinator with a visibly labelled MOCK executor: selected-fault submission and report display; synchronized topology selection; partial compound injection and recovery; healthy controls; keyboard selection and mobile layout. Tested viewports are 1440\,$\times$\,1000 and 390\,$\times$\,844. These checks do not establish real agent diagnosis, comprehensive accessibility conformance or cross-browser compatibility.

\subsection*{Real network evidence}
Opt-in Kathara tests use the existing EnterpriseTopology environment and its process-shared lease. They verify actual state, intended application symptoms, unaffected controls and full post-repair baseline. Only attempted fault components are repaired; uncertain recovery retains pending intent. No model API is called.

\begin{tabularx}{\textwidth}{@{}Xllr@{}}\toprule
Saved cycle & Result & Recovery & Seconds \\
\midrule
"""
        + cycle_rows
        + r"""
\bottomrule\end{tabularx}
"""
        + "\nSuite completion recorded: \\textbf{"
        + str(live_summary["suite_finished"])
        + "}. Pending owned faults in saved evidence: \\texttt{"
        + tex(str(live_summary["pending"]))
        + "}. An incomplete suite is reported only as its executed subset.\n"
        + r"""

\subsection*{Defects corrected}
Repeated references to the same result file previously inflated attempt counts; resolved paths are now deduplicated. Malformed saved-report structures previously broke the report index; invalid entries no longer prevent valid reports from loading. Final regression results above are recorded after these corrections.

\newpage
\section*{4. Diagnostic difficulty and metric interpretation}
The 50--70\% figure is a client-reported \textbf{agent diagnostic difficulty target}, not a threshold for software-test success. A benchmark may correctly process an incorrect diagnosis: that is a software pass and an agent mistake. Conversely, a correct diagnosis lost or mis-scored by the software is a software failure.

The proposed primary diagnostic metric is \textbf{exact RCA correct / all attempted diagnoses}, with scored-only accuracy, failures, healthy false positives, full correctness and uncertainty reported separately. Confirm whether the client instead intends full correctness, which also requires explanation and repair credit.

For a defensible existing result, retain the model/version, manifest/hash, scorer, prompt, tools, turn budget, seed, repetition count, case/category composition and denominator. Do not mix configurations into a single comparison, discard failed attempts or treat repeated ticket variants as independent physical fault mechanisms. Confidence intervals require caution when trials share the same scenarios.

No model experiment was rerun for this report. Accordingly, this report makes \textbf{no new claim that 50--70\% was achieved}. Scores must be reported as observed even outside the desired range. Any future difficulty calibration should be declared on development cases, with a fixed evaluation set retained for the final comparison.

\section*{5. Remaining limitations and client review}
\begin{itemize}
\item Automatic evaluation across every displayed topology remains incomplete. Current automatic support is limited to EnterpriseTopology; other catalogs and adapters have explicit boundaries.
\item A fresh model-backed end-to-end run, agent accuracy and API cost were not measured in this validation.
\item No source-code line/branch coverage percentage or agreed performance SLA is claimed. Measured cycle durations are observations, not performance acceptance results.
\item Deployment in the client's intended environment, independent installation, client UAT and formal sign-off remain pending.
\end{itemize}

\subsection*{Handover and review record}
Provide the source revision plus local changes, dependency/prerequisite instructions, dashboard startup guide, topology support matrix, native operating/recovery guides, scenario and scoring contracts, story registry and raw test evidence. Review the formal project identity, access permissions, target environment, primary accuracy metric and acceptance criteria with the client. Capture decisions and remaining defects in the project wiki and final meeting record.

\begin{tabularx}{\textwidth}{@{}lX@{}}\toprule
Review item & Client record \\
\midrule
Recipient and review date & To be completed \\
Agreed final requirements & To be confirmed; team proposals are not assumed accepted \\
Accepted limitations / open actions & To be recorded at review \\
Deployment / UAT result & Pending \\
Client acceptance / sign-off & Pending \\
\bottomrule\end{tabularx}
\end{document}
"""
    )
    (DOCS / "report/main.tex").write_text(document)
    print(
        json.dumps(
            {
                "offline": offline,
                "browser": {k: v for k, v in browser.items() if k != "workflows"},
                "live_cycles": len(cycles),
                "live_finished": live_summary["suite_finished"],
                "report": str(DOCS / "report/main.tex"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
