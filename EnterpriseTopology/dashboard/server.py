"""Local, loopback-only presentation UI for the SADE benchmark."""

from __future__ import annotations

import argparse
import errno
import json
import os
import re
import subprocess
import sys
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
STATIC = Path(__file__).resolve().parent
RESULTS = ROOT / "results" / "sade"
sys.path.insert(0, str(STATIC))
from fault_runtime import (
    Conflict,
    catalog,
    generic_faults,
    native_support,
    selected,
    support,
    topologies,
)
from operation_control import Operations, sanitized

MODEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,99}$")
CASE_COUNT = len(json.loads((ROOT / "tools" / "sade_cases.json").read_text()))


class RunState:
    def __init__(self, python: Path, nika_root: Path):
        self.python = python
        self.nika_root = nika_root
        self.lock = threading.Lock()
        self.running = False
        self.started_at: str | None = None
        self.finished_at: str | None = None
        self.returncode: int | None = None
        self.report: str | None = None
        self.repeats = 1
        self.lines: list[str] = []
        self.process: subprocess.Popen | None = None
        self.operations = Operations(python)
        self.case_count = CASE_COUNT
        self.fault_id = None
        self.topology_id = "enterprise-75"
        self.completion_count = 0

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "claude_auth_preference": "API key" if os.getenv("ANTHROPIC_API_KEY", "").strip() else "Claude Code login (subscription if signed in with Claude.ai)",
                "running": self.running,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "returncode": self.returncode,
                "report": self.report,
                "repeats": self.repeats,
                "case_count": self.case_count,
                "topology_id": self.topology_id,
                "fault_id": self.fault_id,
                "completion_count": self.completion_count,
                "lines": self.lines[-160:],
            }

    def start(
        self,
        model: str,
        repeats: int,
        mode: str = "live",
        prompt_style: str = "generic",
        tool_profile: str = "atomic",
        judge_model: str | None = None,
        fault_id: str | None = None,
        topology_id: str = "enterprise-75",
        enterprise20: bool = False,
    ) -> bool:
        with self.lock:
            if self.running:
                return False
            if enterprise20:
                if topology_id != "enterprise-75" or fault_id is not None:
                    raise ValueError("The original 20-ticket suite requires Enterprise Topology")
                enabled, reason = native_support(topology_id)
                if not enabled:
                    raise ValueError(reason)
                count = CASE_COUNT
            else:
                chosen = [fault_id] if fault_id else list(generic_faults.FAMILIES)
                if not all(generic_faults.validated(topology_id, key) for key in chosen):
                    raise ValueError('Validate each selected topology/fault combination first')
                count = len(chosen)
            lease = self.operations.reserve_auto(topology_id)
            self.fault_id = fault_id
            self.topology_id = topology_id
            self.case_count = count
            self.completion_count = 0
            self.running = True
            self.started_at = datetime.now(timezone.utc).isoformat()
            self.finished_at = None
            self.returncode = None
            self.report = None
            self.repeats = repeats
            self.lines = [
                f"Starting {repeats} pass(es) × {self.case_count} scenarios with {model} ({mode})…"
            ]
        try:
            threading.Thread(
                target=self._run,
                args=(model, repeats, mode, prompt_style, tool_profile, judge_model, fault_id, lease, topology_id, enterprise20),
                daemon=True,
            ).start()
        except Exception:
            lease.release()
            with self.lock:
                self.running = False
            raise
        return True

    def _run(
        self,
        model: str,
        repeats: int,
        mode: str = "live",
        prompt_style: str = "generic",
        tool_profile: str = "atomic",
        judge_model: str | None = None,
        fault_id: str | None = None,
        lease=None,
        topology_id="enterprise-75",
        enterprise20=False,
    ) -> None:
        command = [
            str(self.python),
            "-u",
            str(ROOT / "tools" / "sade_benchmark.py"),
            "run",
            "--nika-root",
            str(self.nika_root),
            "--model",
            model,
            "--repeats",
            str(repeats),
            "--mode",
            mode,
            "--prompt-style",
            prompt_style,
            "--tool-profile",
            tool_profile,
        ]
        if enterprise20:
            command.extend(["--max-turns", "20", "--seed", "42"])
        if fault_id:
            command.extend(["--cases", *selected(topology_id, fault_id)["case_ids"]])
        if judge_model:
            command.extend(["--judge-model", judge_model])
        try:
            environment = os.environ.copy()
            if enterprise20:
                environment.pop("SADE_GENERIC_TOPOLOGY", None)
            else:
                environment["SADE_GENERIC_TOPOLOGY"] = topology_id
            environment["SADE_ENV_LOCK_FD"] = str(lease.file.fileno())
            process = subprocess.Popen(
                command,
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=environment,
                pass_fds=(lease.file.fileno(),),
            )
            with self.lock:
                self.process = process
            assert process.stdout is not None
            for raw in process.stdout:
                line = sanitized(raw.rstrip("\n"))
                with self.lock:
                    self.lines.append(line)
                    if re.match(r"^  (scored|error);", line):
                        self.completion_count += 1
                    if len(self.lines) > 500:
                        self.lines = self.lines[-500:]
                    if line.startswith("Summary: "):
                        candidate = Path(line[9:].strip())
                        if (
                            candidate.parent.resolve() == RESULTS.resolve()
                            and candidate.is_file()
                        ):
                            self.report = candidate.name
            code = process.wait()
        except Exception as exc:  # noqa: BLE001 - preserve run status when a worker cannot launch
            code = -1
            with self.lock:
                self.lines.append(sanitized(f"Unable to start benchmark: {exc}"))
        finally:
            if lease:
                lease.release()
        with self.lock:
            self.returncode = code
            self.finished_at = datetime.now(timezone.utc).isoformat()
            self.running = False
            self.process = None


def report_files() -> list[Path]:
    return sorted(
        RESULTS.glob("benchmark-*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def report_index() -> list[dict]:
    rows = []
    for path in report_files():
        try:
            data = json.loads(path.read_text())
            if not isinstance(data, dict):
                continue
            runs = data.get("runs", [])
            metrics = data.get("metrics", {})
            if (
                not isinstance(runs, list)
                or any(not isinstance(run, dict) for run in runs)
                or not isinstance(metrics, dict)
                or any(not isinstance(metrics.get(key, {}), dict)
                       for key in ("rca_exact", "full_correct"))
            ):
                continue
            rows.append(
                {
                    "id": path.name,
                    "generated_at": data.get("generated_at"),
                    "attempted": data.get("attempted", 0),
                    "scored": data.get("scored", 0),
                    "complete_runs": data.get("complete_runs", 0),
                    "model": next(
                        (
                            r.get("model")
                            for r in data.get("runs", [])
                            if r.get("model")
                        ),
                        None,
                    ),
                    "exact_rate": data.get("metrics", {})
                    .get("rca_exact", {})
                    .get("rate"),
                    "full_rate": data.get("metrics", {})
                    .get("full_correct", {})
                    .get("rate_scored"),
                    "scorer_version": data.get("scorer_version", "1.0"),
                }
            )
        except (OSError, ValueError, TypeError):
            continue
    return rows


class Handler(BaseHTTPRequestHandler):
    state: RunState

    def _json(self, status: int, data: dict | list) -> None:
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path, content_type: str) -> None:
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            return self._file(STATIC / "index.html", "text/html; charset=utf-8")
        if parsed.path == "/style.css":
            return self._file(STATIC / "style.css", "text/css; charset=utf-8")
        if parsed.path == "/app.js":
            return self._file(STATIC / "app.js", "text/javascript; charset=utf-8")
        if parsed.path == "/faults.js":
            return self._file(STATIC / "faults.js", "text/javascript; charset=utf-8")
        if parsed.path == "/topology.js":
            return self._file(STATIC / "topology.js", "text/javascript; charset=utf-8")
        topology_map = topologies()
        if parsed.path == "/api/topologies":
            return self._json(200, [
                {"id": key, "name": item["name"],
                 "evaluation_enabled": item["evaluation_enabled"]}
                for key, item in topology_map.items()
            ])
        if parsed.path == "/api/topology":
            topology_id = parse_qs(parsed.query).get("id", ["enterprise-75"])[0]
            topology = topology_map.get(topology_id)
            if topology is None:
                return self._json(404, {"error": "Topology not found"})
            try:
                inventory = json.loads(topology["inventory"].read_text())
            except (OSError, ValueError):
                return self._json(500, {"error": "Topology inventory is unavailable"})
            health = None
            if topology_id == "enterprise-75":
                try:
                    saved = json.loads((ROOT / "results/latest-health.json").read_text())
                    health = {
                        "timestamp": saved["timestamp"],
                        "passed": saved["passed"],
                        "total": len(saved["checks"]),
                        "passing": sum(c["passed"] for c in saved["checks"]),
                    }
                except (OSError, ValueError, KeyError):
                    pass
            executable, runtime_note = support(topology_id)
            return self._json(200, {
                "id": topology_id,
                "execution_enabled": executable,
                "support_reason": runtime_note,
                "name": topology["name"],
                "nodes": inventory["nodes"],
                "links": inventory["links"],
                "scenario_count": topology["scenario_count"],
                "evaluation_enabled": topology["evaluation_enabled"],
                "health": health,
                "layout": inventory.get("layout", "enterprise"),
                "protocols": inventory.get("protocols", "OSPF · VRRP · VLAN"),
                "note": runtime_note if executable else inventory.get("note"),
                "source_path": inventory.get("source_path"),
                "source_commit": inventory.get("source_commit"),
                "scenarios": list(generic_faults.FAMILIES),
            })
        if parsed.path in ("/api/faults", "/api/manual/status"):
            topology_id = parse_qs(parsed.query).get("topology_id", [""])[0]
            try:
                data = catalog(topology_id) if parsed.path == "/api/faults" else self.state.operations.snapshot(topology_id)
                return self._json(200, data)
            except ValueError as exc:
                return self._json(400, {"error": str(exc)})
            except (OSError, KeyError):
                return self._json(503, {"error": "Runtime journal or adapter unavailable"})
        if parsed.path == "/api/status":
            return self._json(200, self.state.snapshot())
        if parsed.path == "/api/reports":
            return self._json(200, report_index())
        if parsed.path == "/api/report":
            name = parse_qs(parsed.query).get("id", [""])[0]
            if name not in {path.name for path in report_files()}:
                return self._json(404, {"error": "Report not found"})
            try:
                return self._json(200, json.loads((RESULTS / name).read_text()))
            except (OSError, ValueError):
                return self._json(500, {"error": "Report cannot be read"})
        self._json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        if self.path not in ("/api/run", "/api/manual"):
            return self._json(404, {"error": "Not found"})
        # Browser requests must originate from this loopback server.
        try:
            host = urlparse("http://" + self.headers.get("Host", "")).hostname
        except ValueError:
            return self._json(403, {"error": "Invalid loopback host"})
        if host not in ("127.0.0.1", "localhost", "::1"):
            return self._json(403, {"error": "Loopback host required"})
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self._json(415, {"error": "application/json required"})
        origin = self.headers.get("Origin", "")
        if origin and origin != f"http://{self.headers.get('Host', '')}":
            return self._json(403, {"error": "Invalid origin"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 4096:
                raise ValueError("Invalid request size")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise TypeError("Request must be a JSON object")
            allowed = {"topology_id", "fault_id", "action"} if self.path == "/api/manual" else {
                "topology_id", "fault_id", "scope", "model", "judge_model", "repeats", "mode", "prompt_style", "tool_profile"}
            if set(payload) - allowed:
                raise ValueError("Unexpected request fields")
            topology_id = payload.get("topology_id")
            fault_id = payload.get("fault_id")
            if not isinstance(topology_id, str) or topology_id not in topologies():
                raise ValueError("Unknown topology ID")
            if not isinstance(fault_id, str):
                raise TypeError("A fault ID is required")
            row = selected(topology_id, fault_id)
            if self.path == "/api/manual":
                action = payload.get("action")
                if not isinstance(action, str):
                    raise ValueError("A manual action is required")
                self.state.operations.start(topology_id, action, fault_id)
                return self._json(202, self.state.operations.snapshot(topology_id))
            scope = payload.get("scope", "selected")
            if scope not in ("selected", "all", "enterprise20"):
                raise ValueError("Invalid evaluation scope")
            if scope == "enterprise20":
                if topology_id != "enterprise-75":
                    raise ValueError("The original 20-ticket suite requires Enterprise Topology")
            elif fault_id not in generic_faults.FAMILIES or not row['evaluation_enabled']:
                raise ValueError('Validate the selected generic fault before benchmarking')
            if scope == 'all' and not all(generic_faults.validated(topology_id, key) for key in generic_faults.FAMILIES):
                raise ValueError('Validate all five generic cases before running the full suite')
            model = payload.get("model", "claude-haiku-5-5")
            judge_model = payload.get("judge_model")
            if judge_model == "same":
                judge_model = None
            if judge_model is not None and (not isinstance(judge_model, str) or not MODEL_PATTERN.fullmatch(judge_model)):
                raise ValueError("Invalid judge model ID")
            repeats = payload.get("repeats", 1)
            mode = payload.get("mode", "live")
            prompt_style = payload.get("prompt_style", "generic")
            tool_profile = payload.get("tool_profile", "atomic")
            if prompt_style not in ("generic", "guided") or tool_profile not in (
                "atomic",
                "sweep",
            ):
                raise ValueError("Invalid diagnostic profile")
            if prompt_style != 'generic' or tool_profile != 'atomic':
                raise ValueError('Generic faults currently require the generic prompt and atomic tools')
            if mode not in ("live", "no-tools"):
                raise ValueError("Invalid evaluation mode")
            if not isinstance(model, str) or not MODEL_PATTERN.fullmatch(model):
                raise ValueError("Invalid model ID")
            if type(repeats) is not int or not 1 <= repeats <= 10:
                raise ValueError("Repeats must be between 1 and 10")
        except Conflict as exc:
            return self._json(409, {"error": str(exc)})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return self._json(400, {"error": str(exc)})
        except (OSError, KeyError):
            return self._json(503, {"error": "Runtime recovery journal unavailable; inspect it before proceeding"})
        if any(selected.startswith("gemini-") for selected in (model, judge_model or model)) and not (os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()):
            return self._json(400, {"error": "Set GEMINI_API_KEY in the server terminal, then restart the dashboard"})
        if any(selected.startswith("deepseek-") for selected in (model, judge_model or model)) and not os.getenv("DEEPSEEK_API_KEY", "").strip():
            return self._json(400, {"error": "Set DEEPSEEK_API_KEY in the server terminal, then restart the dashboard"})
        try:
            options = {"enterprise20": True} if scope == "enterprise20" else {}
            if not self.state.start(model, repeats, mode, prompt_style, tool_profile, judge_model,
                                    fault_id if scope == "selected" else None, topology_id, **options):
                return self._json(409, {"error": "A benchmark is already running"})
        except ValueError as exc:
            return self._json(400, {"error": str(exc)})
        except Conflict as exc:
            return self._json(409, {"error": str(exc)})
        except (OSError, KeyError):
            return self._json(503, {"error": "Runtime recovery journal unavailable; inspect it before proceeding"})
        self._json(202, self.state.snapshot())

    def log_message(self, format: str, *args: object) -> None:
        if not self.path.startswith(("/api/status", "/api/manual/status")):
            super().log_message(format, *args)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--nika-root", type=Path, default=ROOT.parents[2] / "nika-demo")
    parser.add_argument("--python", type=Path)
    args = parser.parse_args()
    nika_root = args.nika_root.expanduser().resolve()
    # Keep the venv symlink intact: resolving it would run the base interpreter.
    python = (
        (args.python or nika_root / ".venv" / "bin" / "python").expanduser().absolute()
    )
    Handler.state = RunState(python, nika_root)
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            parser.exit(
                2,
                f"Port {args.port} is already in use. If the dashboard is open, "
                f"use http://127.0.0.1:{args.port}/; otherwise choose --port {args.port + 1}.\n",
            )
        raise
    print(f"SADE dashboard: http://127.0.0.1:{server.server_port}", flush=True)
    print(f"Benchmark Python: {python}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    main()
