"""Run SADE cases sequentially and summarize saved local RCA evaluations."""

from __future__ import annotations

import argparse
import io
import json
import math
import random
import sys
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sade_eval

ROOT = sade_eval.ROOT
RESULTS = ROOT / "results" / "sade"
AXES = (
    "detection_correct",
    "device_correct",
    "localization_correct",
    "fault_type_correct",
    "rca_exact",
    "explanation_correct",
    "repair_correct",
    "full_correct",
)
AXIS_LABELS = {
    "detection_correct": "Anomaly detected",
    "device_correct": "Device correct",
    "localization_correct": "Resource correct",
    "fault_type_correct": "Fault type correct",
    "rca_exact": "Exact RCA fields",
    "explanation_correct": "Explanation",
    "repair_correct": "Repair recommendation",
    "full_correct": "Full correctness",
}


def proportion(correct: int, total: int) -> dict:
    """Wilson interval: small perfect samples still have wide uncertainty."""
    if not total:
        return {"correct": correct, "denominator": total, "rate": None, "ci95": None}
    p, z = correct / total, 1.959963984540054
    d = 1 + z * z / total
    center = (p + z * z / (2 * total)) / d
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / d
    return {
        "correct": correct,
        "denominator": total,
        "rate": round(p, 4),
        "ci95": [round(max(0, center - margin), 4), round(min(1, center + margin), 4)],
    }


def summarize_metric(rows: list[dict], key: str) -> dict:
    correct = sum(bool(row["score"] and row["score"].get(key) is True) for row in rows)
    assessed = sum(
        bool(row["score"] and row["score"].get(key) is not None) for row in rows
    )
    metric = {
        **proportion(correct, len(rows)),
        "scored_denominator": assessed,
        "unscored": len(rows) - assessed,
        "rate_scored": round(correct / assessed, 4) if assessed else None,
    }
    if (
        key in ("explanation_correct", "repair_correct", "full_correct")
        and not assessed
    ):
        metric["rate"] = metric["ci95"] = None
    return metric


def summarize(paths: list[Path]) -> dict:
    records = []
    for path in paths:
        data = json.loads(path.read_text())
        if data.get("case") not in sade_eval.CASES:
            continue
        scored = data.get("status") == "scored" and isinstance(data.get("score"), dict)
        # Rescore saved predictions under the current strict scorer; do not carry
        # forward legacy partial-match exact RCA flags.
        if scored:
            prediction = data["score"].get("predicted")
            if isinstance(prediction, dict):
                data["score"] = sade_eval.score_prediction(
                    data["case"],
                    prediction,
                    data["score"].get("quality")
                    if data.get("scorer_version") == sade_eval.SCORER_VERSION
                    else None,
                )
            else:
                scored = False
        row = {
            "case": data["case"],
            "timestamp": data.get("timestamp"),
            "model": data.get("model"),
            "max_turns": data.get("max_turns"),
            "judge_model": data.get("judge_model"),
            "failure_kind": data.get("failure_kind"),
            "hit_max_turns": data.get("agent", {}).get("hit_max_turns", False),
            "status": data.get("status"),
            "category": sade_eval.CASES[data["case"]]["category"],
            "fault": sade_eval.CASES[data["case"]]["fault"],
            "mode": data.get("mode", "live"),
            "prompt_style": data.get("prompt_style", "guided"),
            "tool_profile": data.get("tool_profile", "sweep"),
            "source_scorer_version": data.get("scorer_version", "1.0"),
            "quality_error": data.get("quality_error"),
            "quality": data.get("score", {}).get("quality"),
            "judge_cost_usd": data.get("score", {})
            .get("quality", {})
            .get("total_cost_usd")
            if data.get("score", {}).get("quality")
            else None,
            "faults": sade_eval.case_faults(data["case"]),
            "benchmark_version": data.get("benchmark_version", "1.0"),
            "state_verified": data.get(
                "state_verified", data.get("injection_verified", False)
            ),
            "predicted_anomaly": data.get("score", {})
            .get("predicted", {})
            .get("is_anomaly")
            if scored
            else None,
            "injection_verified": data.get("injection_verified", False),
            "repair_verified": data.get("repair_verified", False),
            "result_path": str(path.resolve()),
            "wall_seconds": data.get("wall_seconds"),
            "diagnosis_seconds": data.get("diagnosis_seconds"),
            "tool_calls": data.get("agent", {}).get("tool_calls"),
            "total_cost_usd": data.get("agent", {}).get("total_cost_usd"),
            "usage": data.get("agent", {}).get("usage"),
            "error": data.get("error"),
            "score": {key: data["score"].get(key) for key in AXES} if scored else None,
        }
        records.append(row)
    records.sort(key=lambda row: (row["timestamp"] or "", row["case"]))
    by_case = {}
    for case in sade_eval.CASES:
        subset = [row for row in records if row["case"] == case]
        scored = [row for row in subset if row["score"] is not None]
        by_case[case] = {
            "attempted": len(subset),
            "scored": len(scored),
            "exact_rca_correct": sum(row["score"]["rca_exact"] for row in scored),
        }
    scored = [row for row in records if row["score"] is not None]
    summary = {
        "schema_version": 4,
        "budget_exhausted": sum(r["hit_max_turns"] for r in records),
        "by_configuration": {},
        "scorer_version": sade_eval.SCORER_VERSION,
        "manifest_hash": sade_eval.MANIFEST_HASH,
        "benchmark_versions": sorted({r["benchmark_version"] for r in records}),
        "modes": sorted({r["mode"] for r in records}),
        "quality_scored": sum(
            r["score"] is not None and r["score"]["explanation_correct"] is not None
            for r in records
        ),
        "experiment_groups": sorted(
            {f"{r['mode']}/{r['prompt_style']}/{r['tool_profile']}" for r in records}
        ),
        "source_scorer_versions": sorted({r["source_scorer_version"] for r in records}),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "local enterprise-topology SADE evaluation; not official NIKA metrics",
        "attempted": len(records),
        "scored": len(scored),
        "errors": len(records) - len(scored),
        "complete_runs": sum(
            row["score"] is not None
            and row["state_verified"]
            and row["repair_verified"]
            for row in records
        ),
        "injection_verified": sum(row["injection_verified"] for row in records),
        "repair_verified": sum(row["repair_verified"] for row in records),
        "metrics": {key: summarize_metric(records, key) for key in AXES},
        "by_case": by_case,
        "runs": records,
    }
    for row in records:
        key = json.dumps([row[k] for k in ("model", "max_turns", "judge_model", "benchmark_version", "mode", "prompt_style", "tool_profile")])
        summary["by_configuration"].setdefault(key, []).append(row)
    summary["by_configuration"] = {key: {"attempted": len(rows), "metrics": {axis: summarize_metric(rows, axis) for axis in AXES}} for key, rows in summary["by_configuration"].items()}
    summary["by_category"] = {
        category: proportion(
            sum(
                bool(r["score"] and r["score"]["rca_exact"])
                for r in records
                if r["category"] == category
            ),
            sum(r["category"] == category for r in records),
        )
        for category in sorted({c["category"] for c in sade_eval.CASES.values()})
    }
    healthy = [r for r in scored if r["category"] == "healthy"]
    summary["healthy_false_positive"] = proportion(
        sum(r["predicted_anomaly"] is True for r in healthy), len(healthy)
    )
    summary["healthy_false_positive"]["unscored"] = sum(
        r["category"] == "healthy" and r["score"] is None for r in records
    )
    summary["healthy_correct_rejection"] = summary["by_category"]["healthy"]
    summary["suite_coverage"] = len({r["case"] for r in records}) / len(sade_eval.CASES)
    summary["by_experiment"] = {}
    for group in summary["experiment_groups"]:
        subset = [
            r
            for r in records
            if f"{r['mode']}/{r['prompt_style']}/{r['tool_profile']}" == group
        ]
        summary["by_experiment"][group] = {
            "attempted": len(subset),
            "metrics": {key: summarize_metric(subset, key) for key in AXES},
        }
    summary["ablation_deltas"] = {}
    for axis in AXES:
        for tools in ("atomic", "sweep"):
            generic = summary["by_experiment"].get(f"live/generic/{tools}")
            guided = summary["by_experiment"].get(f"live/guided/{tools}")
            if (
                generic
                and guided
                and generic["metrics"][axis]["rate"] is not None
                and guided["metrics"][axis]["rate"] is not None
            ):
                summary["ablation_deltas"][f"guided_minus_generic/{tools}/{axis}"] = (
                    round(
                        guided["metrics"][axis]["rate"]
                        - generic["metrics"][axis]["rate"],
                        4,
                    )
                )
        for style in ("generic", "guided"):
            atomic = summary["by_experiment"].get(f"live/{style}/atomic")
            sweep = summary["by_experiment"].get(f"live/{style}/sweep")
            if (
                atomic
                and sweep
                and atomic["metrics"][axis]["rate"] is not None
                and sweep["metrics"][axis]["rate"] is not None
            ):
                summary["ablation_deltas"][f"sweep_minus_atomic/{style}/{axis}"] = (
                    round(
                        sweep["metrics"][axis]["rate"]
                        - atomic["metrics"][axis]["rate"],
                        4,
                    )
                )
    return summary


def print_summary(summary: dict) -> None:
    def rate(value: float | None) -> str:
        return "n/a" if value is None else f"{value:.1%}"

    print("SADE local benchmark report")
    print("===========================")
    print(summary["scope"])
    print(
        f"Attempts: {summary['attempted']}  Scored: {summary['scored']}  "
        f"Complete: {summary['complete_runs']}  Errors: {summary['errors']}"
    )
    print(
        f"Injection verified: {summary['injection_verified']}/{summary['attempted']}  "
        f"Environment restored: {summary['repair_verified']}/{summary['attempted']}"
    )
    print(
        f"Quality scored: {summary.get('quality_scored', 0)}/{summary['attempted']}; full correctness requires field, explanation and repair credit."
    )
    print(
        "\nScoring                    Correct/attempts   Rate    Correct/scored   Rate"
    )
    for key, metric in summary["metrics"].items():
        attempts = f"{metric['correct']}/{metric['denominator']}"
        scored = f"{metric['correct']}/{metric['scored_denominator']}"
        print(
            f"{AXIS_LABELS[key]:<26} {attempts:>8} {rate(metric['rate']):>8} "
            f"{scored:>16} {rate(metric['rate_scored']):>7}"
        )
    print("\nExact RCA by case")
    for case, counts in summary["by_case"].items():
        if counts["attempted"]:
            print(
                f"  {case:<20} {counts['exact_rca_correct']}/{counts['attempted']} attempts"
            )
    if summary["runs"]:
        print("\nIndividual runs")
        print(
            "Case                 Model                Exact  Inject  Restore Calls  Seconds"
        )
        for row in summary["runs"]:
            exact = "yes" if row["score"] and row["score"]["rca_exact"] else "no"
            inject = "yes" if row["injection_verified"] else "no"
            repair = "yes" if row["repair_verified"] else "no"
            calls = row["tool_calls"] if row["tool_calls"] is not None else "-"
            seconds = (
                f"{row['wall_seconds']:.1f}" if row["wall_seconds"] is not None else "-"
            )
            print(
                f"{row['case']:<20} {(row['model'] or '-'): <20} {exact:>5}  "
                f"{inject:>6}  {repair:>6}  {calls:>5}  {seconds:>7}"
            )
            if row["error"]:
                print(f"  Error: {row['error']}")
    for category, metric in summary.get("by_category", {}).items():
        print(
            f"{category}: {metric['correct']}/{metric['denominator']} exact diagnoses"
        )
    for name, group in summary.get("by_experiment", {}).items():
        print(
            f"Experiment {name}: {group['attempted']} attempts; exact fields {rate(group['metrics']['rca_exact']['rate'])}; full {rate(group['metrics']['full_correct']['rate'])}"
        )
    print(
        "\nComplete means scored with test state and environment restoration verified. Restoration is performed by the runner, not the agent."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    run = sub.add_parser("run", help="Run all cases sequentially, then write a summary")
    run.add_argument("--nika-root")
    run.add_argument(
        "--model", default=sade_eval.os.getenv("SADE_MODEL", "claude-haiku-5-5")
    )
    run.add_argument("--max-turns", type=int, default=20)
    run.add_argument("--repeats", type=int, default=1)
    run.add_argument("--prompt-style", choices=("generic", "guided"), default="generic")
    run.add_argument("--tool-profile", choices=("atomic", "sweep"), default="atomic")
    run.add_argument("--judge-model")
    run.add_argument(
        "--cases",
        nargs="+",
        choices=list(sade_eval.CASES),
        help="Subset for paired experiments",
    )
    run.add_argument(
        "--ablation",
        action="store_true",
        help="Paired generic/guided × atomic/sweep plus no-tools",
    )
    run.add_argument("--resume", type=Path, help="Resume a checkpoint using its saved configuration; completed trials are skipped")
    run.add_argument("--seed", type=int, default=42)
    run.add_argument("--mode", choices=("live", "no-tools"), default="live")
    report = sub.add_parser(
        "summarize", help="Summarize existing run result JSON files"
    )
    report.add_argument("paths", nargs="*", type=Path)
    report.add_argument("--out", type=Path)
    saved = sub.add_parser(
        "report", help="Print a saved benchmark summary as a readable report"
    )
    saved.add_argument("path", type=Path)
    rescore = sub.add_parser(
        "rescore", help="Rescore a saved format error after parser fixes"
    )
    rescore.add_argument("path", type=Path)
    args = parser.parse_args()
    if args.action == "report":
        print_summary(json.loads(args.path.read_text()))
        return 0
    if args.action == "rescore":
        data = json.loads(args.path.read_text())
        if (
            data.get("status") != "error"
            or not str(data.get("error", "")).startswith(
                "ValueError: SADE did not submit"
            )
            or not data.get("agent", {}).get("final_text")
        ):
            parser.error(
                "rescore requires a saved DIAGNOSIS parsing error with agent final text"
            )
        prediction = sade_eval.parse_prediction(data["agent"]["final_text"])
        data["score"] = sade_eval.score_prediction(data["case"], prediction)
        data["parser_correction"] = {
            "original_status": data["status"],
            "original_error": data["error"],
            "rescored_at": datetime.now(timezone.utc).isoformat(),
        }
        data["status"] = "scored"
        del data["error"]
        args.path.write_text(json.dumps(data, indent=2) + "\n")
        print(f"Rescored {args.path}: exact RCA {data['score']['rca_exact']}")
        return 0
    if args.action == "run":
        if args.repeats < 1 or args.max_turns < 1 or not args.model.strip():
            parser.error(
                "--repeats and --max-turns must be positive; --model must not be empty"
            )
        nika_root = sade_eval._nika_root(args.nika_root)
        if not args.resume:
            sade_eval._preflight(nika_root, args.model, args.judge_model)
        rng = random.Random(args.seed)
        selected_cases = args.cases or list(sade_eval.CASES)
        profiles = [(args.mode, args.prompt_style, args.tool_profile)]
        if args.ablation:
            profiles = [("live", style, tools) for style in ("generic", "guided") for tools in ("atomic", "sweep")]
            profiles.append(("no-tools", "generic", "atomic"))
        config = {
            "seed": args.seed, "mode": args.mode, "repeats": args.repeats,
            "model": args.model, "max_turns": args.max_turns,
            "prompt_style": args.prompt_style, "tool_profile": args.tool_profile,
            "judge_model": args.judge_model or args.model, "ablation": args.ablation,
            "selected_cases": selected_cases, "benchmark_version": sade_eval.BENCHMARK_VERSION,
            "manifest_hash": sade_eval.MANIFEST_HASH,
        }
        schedule = []
        for repeat in range(1, args.repeats + 1):
            trials = [(case, *profile) for case in selected_cases for profile in profiles]
            rng.shuffle(trials)
            schedule.extend(dict(case=case, mode=mode, prompt_style=style, tool_profile=tools, repeat=repeat) for case, mode, style, tools in trials)
        out = RESULTS / f"benchmark-{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}.json"
        if args.resume:
            out = args.resume.resolve()
            saved = json.loads(out.read_text())
            config = saved["run_config"]
            if config.get("manifest_hash") != sade_eval.MANIFEST_HASH:
                parser.error("Cannot resume a checkpoint from a different case manifest")
            schedule = config["schedule"]
            sade_eval._preflight(nika_root, config["model"], config["judge_model"])
        config["schedule"] = schedule

        def checkpoint():
            paths = [Path(trial["result_path"]) for trial in schedule if trial.get("result_path")]
            summary = summarize(paths)
            summary["run_config"] = config
            summary["pending"] = len(schedule) - len(paths)
            out.parent.mkdir(parents=True, exist_ok=True)
            temporary = out.with_suffix(".tmp")
            temporary.write_text(json.dumps(summary, indent=2) + "\n")
            temporary.replace(out)
            return summary

        summary = checkpoint()
        print(f"Checkpoint: {out}", flush=True)
        # Every attempted trial is retained, including failed answers. Resume never
        # silently retries model failures and biases the benchmark toward success.
        for trial in schedule:
            if trial.get("result_path"):
                result = json.loads(Path(trial["result_path"]).read_text())
                if not result.get("environment_restored", result.get("repair_verified", False)):
                    raise RuntimeError("Previous trial did not restore the environment; repair and verify it before starting a new batch")
                continue
            print(f"Running {trial['case']} [{trial['mode']}/{trial['prompt_style']}/{trial['tool_profile']}] (pass {trial['repeat']}/{config['repeats']})...", flush=True)
            with redirect_stdout(io.StringIO()):
                path = sade_eval.run_case(trial["case"], nika_root, config["max_turns"], config["model"], trial["mode"], trial["prompt_style"], trial["tool_profile"], config["judge_model"])
            trial["result_path"] = str(path.resolve())
            summary = checkpoint()
            result = json.loads(path.read_text())
            print(f"  {result['status']}; environment restored: {result['repair_verified']}; report: {path}", flush=True)
            if not result["repair_verified"]:
                print("Environment restoration failed; stopping before the next case.", file=sys.stderr)
                break
        print_summary(summary)
        print(f"Summary: {out}")
        return (
            0
            if summary["attempted"]
            == len(schedule)
            and summary["errors"] == 0
            and summary["quality_scored"] == summary["attempted"]
            and summary["repair_verified"] == summary["attempted"]
            else 1
        )
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
