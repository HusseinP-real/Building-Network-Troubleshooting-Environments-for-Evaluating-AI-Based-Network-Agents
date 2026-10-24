"""Browser QA fixture: real UI/HTTP/leases, MOCK execution, no containers/model APIs.

python3 EnterpriseTopology/tests/serve_dashboard_fixture.py --port 8877
Compound uplink+ACL injection deliberately fails its second component.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'dashboard'))
import server
import operation_control as control
from environment_guard import Lease


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8877)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='sade-ui-fixture-') as tmp:
        control.Lease = lambda root: Lease(Path(tmp) / Path(root).name)
        server.RESULTS = Path(tmp) / 'sade'
        server.RESULTS.mkdir()
        state = server.RunState(Path(sys.executable), Path(tmp))
        def step(lease, topology, action, fault=None):
            state.operations.log(lease, f'MOCK ONLY: {topology} · {action} · {fault or "full health baseline"}')
            time.sleep(.35)
            data = lease.read()
            state.operations.update(lease, completed=data['operation']['completed'] + 1, phase=f'{action}: {fault or topology}')
            return not (action == 'inject' and fault == 'database-ingress-acl')
        state.operations._step = step
        def automatic(model, repeats, mode, style, profile, judge, fault, lease):
            try:
                for phase in ('baseline', 'injection', 'diagnosis (MOCK, no model API)', 'scoring (MOCK)', 'recovery'):
                    with state.lock:
                        state.lines.append(f'MOCK ONLY: {phase} · {fault or "all"}')
                    time.sleep(1)
            finally:
                cases = server.selected('enterprise-75', fault)['case_ids'] if fault else list(server.catalog('enterprise-75'))
                if not fault:
                    cases = [case for row in cases for case in row['case_ids']]
                axes = ['detection_correct', 'device_correct', 'localization_correct', 'fault_type_correct', 'rca_exact', 'explanation_correct', 'repair_correct', 'full_correct']
                count = len(cases) * repeats
                report = {'schema_version': 4, 'scorer_version': '3.0', 'generated_at': datetime.now(timezone.utc).isoformat(),
                          'topology_name': 'Enterprise Topology · MOCK FIXTURE', 'attempted': count, 'scored': count, 'complete_runs': count,
                          'metrics': {axis: {'rate': 1, 'rate_scored': 1, 'correct': count, 'denominator': count, 'scored_denominator': count, 'unscored': 0} for axis in axes},
                          'runs': [{'case': case, 'fault': fault, 'model': 'MOCK:' + model, 'mode': mode, 'wall_seconds': 1, 'tool_calls': 0,
                                    'state_verified': True, 'repair_verified': True, 'score': {axis: True for axis in axes}}
                                   for _ in range(repeats) for case in cases]}
                name = 'benchmark-mock-selected.json'
                (server.RESULTS / name).write_text(json.dumps(report))
                lease.release()
                with state.lock:
                    state.report = name
                    state.running = False
                    state.returncode = 0
                    state.completion_count = state.case_count * repeats
                    state.finished_at = 'fixture-complete'
        state._run = automatic
        class FixtureHandler(server.Handler):
            def _file(self, path, content_type):
                if path.name != 'index.html':
                    return super()._file(path, content_type)
                html = path.read_text().replace('<body>', '<body><div style="padding:12px;background:#f9dedc;color:#410e0b;text-align:center;font-weight:bold">OFFLINE UI FIXTURE — MOCK executor · no real containers or model APIs</div>')
                body = html.encode()
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            def log_message(self, *args):
                pass
        FixtureHandler.state = state
        http = server.ThreadingHTTPServer(('127.0.0.1', args.port), FixtureHandler)
        print(f'MOCK browser fixture: http://127.0.0.1:{http.server_port}', flush=True)
        try:
            http.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            http.server_close()


if __name__ == '__main__':
    main()
