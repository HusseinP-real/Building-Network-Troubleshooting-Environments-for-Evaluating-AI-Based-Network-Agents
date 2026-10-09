"""Run SADE cases sequentially and summarize saved local RCA evaluations."""
from __future__ import annotations

import argparse
import io
import json
import sys
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sade_eval

ROOT = sade_eval.ROOT
RESULTS = ROOT / "results" / "sade"
AXES = ("detection_correct", "device_correct", "localization_correct",
        "fault_type_correct", "rca_exact")
AXIS_LABELS = {
    "detection_correct": "Anomaly detected",
    "device_correct": "Device correct",
    "localization_correct": "Resource correct",
    "fault_type_correct": "Fault type correct",
    "rca_exact": "Exact RCA",
}


def summarize(paths: list[Path]) -> dict:
    records = []
    for path in paths:
        data = json.loads(path.read_text())
        if data.get("case") not in sade_eval.CASES:
            continue
        scored = data.get("status") == "scored" and isinstance(data.get("score"), dict)
        row = {
            "case": data["case"], "timestamp": data.get("timestamp"),
            "model": data.get("model"), "status": data.get("status"),
            "injection_verified": data.get("injection_verified", False),
            "repair_verified": data.get("repair_verified", False),
            "result_path": str(path.resolve()),
            "wall_seconds": data.get("wall_seconds"),
            "tool_calls": data.get("agent", {}).get("tool_calls"),
            "usage": data.get("agent", {}).get("usage"),
            "error": data.get("error"),
            "score": {key: bool(data["score"].get(key)) for key in AXES} if scored else None,
        }
        records.append(row)
    records.sort(key=lambda row: (row["timestamp"] or "", row["case"]))
    by_case = {}
    for case in sade_eval.CASES:
        subset = [row for row in records if row["case"] == case]
        scored = [row for row in subset if row["score"] is not None]
        by_case[case] = {
            "attempted": len(subset), "scored": len(scored),
            "exact_rca_correct": sum(row["score"]["rca_exact"] for row in scored),
        }
    scored = [row for row in records if row["score"] is not None]
    summary = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "local enterprise-topology SADE evaluation; not official NIKA metrics",
        "attempted": len(records),
        "scored": len(scored),
        "errors": len(records) - len(scored),
        "complete_runs": sum(row["score"] is not None and row["injection_verified"]
                             and row["repair_verified"] for row in records),
        "injection_verified": sum(row["injection_verified"] for row in records),
        "repair_verified": sum(row["repair_verified"] for row in records),
        "metrics": {
            key: {"correct": sum(row["score"][key] for row in scored),
                  "denominator": len(records),
                  "rate": round(sum(row["score"][key] for row in scored) / len(records), 4)
                  if records else None,
                  "scored_denominator": len(scored),
                  "rate_scored": round(sum(row["score"][key] for row in scored) / len(scored), 4)
                  if scored else None}
            for key in AXES
        },
        "by_case": by_case,
        "runs": records,
    }
    return summary


def print_summary(summary: dict) -> None:
    def rate(value: float | None) -> str:
        return "n/a" if value is None else f"{value:.1%}"

    print("SADE local benchmark report")
    print("===========================")
    print(summary["scope"])
    print(f"Attempts: {summary['attempted']}  Scored: {summary['scored']}  "
          f"Complete: {summary['complete_runs']}  Errors: {summary['errors']}")
    print(f"Injection verified: {summary['injection_verified']}/{summary['attempted']}  "
          f"Repair verified: {summary['repair_verified']}/{summary['attempted']}")
    print("\nScoring                    Correct/attempts   Rate    Correct/scored   Rate")
    for key, metric in summary["metrics"].items():
        attempts = f"{metric['correct']}/{metric['denominator']}"
        scored = f"{metric['correct']}/{metric['scored_denominator']}"
        print(f"{AXIS_LABELS[key]:<26} {attempts:>8} {rate(metric['rate']):>8} "
              f"{scored:>16} {rate(metric['rate_scored']):>7}")
    print("\nExact RCA by case")
    for case, counts in summary["by_case"].items():
        if counts["attempted"]:
            print(f"  {case:<20} {counts['exact_rca_correct']}/{counts['attempted']} attempts")
    if summary["runs"]:
        print("\nIndividual runs")
        print("Case                 Model                Exact  Inject  Repair  Calls  Seconds")
        for row in summary["runs"]:
            exact = "yes" if row["score"] and row["score"]["rca_exact"] else "no"
            inject = "yes" if row["injection_verified"] else "no"
            repair = "yes" if row["repair_verified"] else "no"
            calls = row["tool_calls"] if row["tool_calls"] is not None else "-"
            seconds = (f"{row['wall_seconds']:.1f}" if row["wall_seconds"] is not None
                       else "-")
            print(f"{row['case']:<20} {(row['model'] or '-'): <20} {exact:>5}  "
                  f"{inject:>6}  {repair:>6}  {calls:>5}  {seconds:>7}")
            if row["error"]:
                print(f"  Error: {row['error']}")
    print("\nComplete means scored with injection and repair both verified.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    run = sub.add_parser("run", help="Run all cases sequentially, then write a summary")
    run.add_argument("--nika-root")
    run.add_argument("--model", default=sade_eval.os.getenv("SADE_MODEL", "claude-haiku-5-5"))
    run.add_argument("--max-turns", type=int, default=30)
    run.add_argument("--repeats", type=int, default=1)
    report = sub.add_parser("summarize", help="Summarize existing run result JSON files")
    report.add_argument("paths", nargs="*", type=Path)
    report.add_argument("--out", type=Path)
    saved = sub.add_parser("report", help="Print a saved benchmark summary as a readable report")
    saved.add_argument("path", type=Path)
    rescore = sub.add_parser("rescore", help="Rescore a saved format error after parser fixes")
    rescore.add_argument("path", type=Path)
    args = parser.parse_args()
    if args.action == "report":
        print_summary(json.loads(args.path.read_text()))
        return 0
    if args.action == "rescore":
        data = json.loads(args.path.read_text())
        if (data.get("status") != "error" or
                not str(data.get("error", "")).startswith("ValueError: SADE did not submit") or
                not data.get("agent", {}).get("final_text")):
            parser.error("rescore requires a saved DIAGNOSIS parsing error with agent final text")
        prediction = sade_eval.parse_prediction(data["agent"]["final_text"])
        data["score"] = sade_eval.score_prediction(data["case"], prediction)
        data["parser_correction"] = {
            "original_status": data["status"], "original_error": data["error"],
            "rescored_at": datetime.now(timezone.utc).isoformat(),
        }
        data["status"] = "scored"
        del data["error"]
        args.path.write_text(json.dumps(data, indent=2) + "\n")
        print(f"Rescored {args.path}: exact RCA {data['score']['rca_exact']}")
        return 0
    if args.action == "run":
        if args.repeats < 1 or args.max_turns < 1 or not args.model.strip():
            parser.error("--repeats and --max-turns must be positive; --model must not be empty")
        nika_root = sade_eval._nika_root(args.nika_root)
        sade_eval._preflight(nika_root)
        paths = []
        for repeat in range(1, args.repeats + 1):
            for case in sade_eval.CASES:
                print(f"Running {case} (pass {repeat}/{args.repeats})...", flush=True)
                with redirect_stdout(io.StringIO()):
                    path = sade_eval.run_case(case, nika_root, args.max_turns, args.model)
                paths.append(path)
                result = json.loads(path.read_text())
                print(f"  {result['status']}; exact RCA: "
                      f"{result.get('score', {}).get('rca_exact', 'n/a')}; "
                      f"repair verified: {result['repair_verified']}; report: {path}", flush=True)
                if not result["repair_verified"]:
                    print("Repair verification failed; stopping before the next case.", file=sys.stderr)
                    break
            else:
                continue
            break
        summary = summarize(paths)
        out = RESULTS / f"benchmark-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, indent=2) + "\n")
        print_summary(summary)
        print(f"Summary: {out}")
        return 0 if summary["attempted"] == len(sade_eval.CASES) * args.repeats and summary["errors"] == 0 and summary["repair_verified"] == summary["attempted"] else 1
    paths = args.paths or sorted(RESULTS.glob("*/*.json"))
    summary = summarize(paths)
    print_summary(summary)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(summary, indent=2) + "\n")
        print(f"Summary: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
