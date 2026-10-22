"""Local, loopback-only presentation UI for the SADE benchmark."""

from __future__ import annotations

import argparse
import errno
import json
import os
import re
import subprocess
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
STATIC = Path(__file__).resolve().parent
RESULTS = ROOT / "results" / "sade"
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

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "running": self.running,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "returncode": self.returncode,
                "report": self.report,
                "repeats": self.repeats,
                "case_count": CASE_COUNT,
                "lines": self.lines[-160:],
            }

    def start(
        self,
        model: str,
        repeats: int,
        mode: str = "live",
        prompt_style: str = "generic",
        tool_profile: str = "atomic",
    ) -> bool:
        with self.lock:
            if self.running:
                return False
            self.running = True
            self.started_at = datetime.now(timezone.utc).isoformat()
            self.finished_at = None
            self.returncode = None
            self.report = None
            self.repeats = repeats
            self.lines = [
                f"Starting {repeats} pass(es) × {CASE_COUNT} scenarios with {model} ({mode})…"
            ]
        threading.Thread(
            target=self._run,
            args=(model, repeats, mode, prompt_style, tool_profile),
            daemon=True,
        ).start()
        return True

    def _run(
        self,
        model: str,
        repeats: int,
        mode: str = "live",
        prompt_style: str = "generic",
        tool_profile: str = "atomic",
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
        try:
            process = subprocess.Popen(
                command,
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=os.environ.copy(),
            )
            with self.lock:
                self.process = process
            assert process.stdout is not None
            for raw in process.stdout:
                line = raw.rstrip("\n")
                with self.lock:
                    self.lines.append(line)
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
        except (OSError, ValueError) as exc:
            code = -1
            with self.lock:
                self.lines.append(f"Unable to start benchmark: {exc}")
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
        if parsed.path == "/topology.js":
            return self._file(STATIC / "topology.js", "text/javascript; charset=utf-8")
        topologies = {
            "enterprise-75": {
                "name": "Enterprise Topology",
                "inventory": ROOT / "inventory.json",
                "scenario_count": CASE_COUNT,
                "evaluation_enabled": True,
            },
            "enterprise-75-standalone": {
                "name": "Enterprise Topology · Standalone",
                "inventory": STATIC / "topologies" / "enterprise-75-standalone.json",
                "scenario_count": 0,
                "evaluation_enabled": False,
            },
        }
        if parsed.path == "/api/topologies":
            return self._json(200, [
                {"id": key, "name": item["name"],
                 "evaluation_enabled": item["evaluation_enabled"]}
                for key, item in topologies.items()
            ])
        if parsed.path == "/api/topology":
            topology_id = parse_qs(parsed.query).get("id", ["enterprise-75"])[0]
            topology = topologies.get(topology_id)
            if topology is None:
                return self._json(404, {"error": "Topology not found"})
            try:
                inventory = json.loads(topology["inventory"].read_text())
            except (OSError, ValueError):
                return self._json(500, {"error": "Topology inventory is unavailable"})
            health = None
            if topology["evaluation_enabled"]:
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
            return self._json(200, {
                "id": topology_id,
                "name": topology["name"],
                "nodes": inventory["nodes"],
                "links": inventory["links"],
                "scenario_count": topology["scenario_count"],
                "evaluation_enabled": topology["evaluation_enabled"],
                "health": health,
            })
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
        if self.path != "/api/run":
            return self._json(404, {"error": "Not found"})
        # Browser requests must originate from this loopback server.
        origin = self.headers.get("Origin", "")
        if origin and origin != f"http://{self.headers.get('Host', '')}":
            return self._json(403, {"error": "Invalid origin"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 4096:
                raise ValueError("Invalid request size")
            payload = json.loads(self.rfile.read(length))
            model = payload.get("model", "claude-haiku-5-5")
            repeats = payload.get("repeats", 1)
            mode = payload.get("mode", "live")
            prompt_style = payload.get("prompt_style", "generic")
            tool_profile = payload.get("tool_profile", "atomic")
            if prompt_style not in ("generic", "guided") or tool_profile not in (
                "atomic",
                "sweep",
            ):
                raise ValueError("Invalid diagnostic profile")
            if mode not in ("live", "no-tools"):
                raise ValueError("Invalid evaluation mode")
            if not isinstance(model, str) or not MODEL_PATTERN.fullmatch(model):
                raise ValueError("Invalid model ID")
            if type(repeats) is not int or not 1 <= repeats <= 10:
                raise ValueError("Repeats must be between 1 and 10")
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return self._json(400, {"error": str(exc)})
        if not self.state.start(model, repeats, mode, prompt_style, tool_profile):
            return self._json(409, {"error": "A benchmark is already running"})
        self._json(202, self.state.snapshot())

    def log_message(self, format: str, *args: object) -> None:
        if not self.path.startswith("/api/status"):
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
