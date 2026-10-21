"""Lab-only syslog collector and read-only event endpoint."""
import json, socket, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from collections import deque
records = deque(maxlen=100)
lock = threading.Lock()
log = Path('/var/log/network-events.jsonl')
def collect():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('192.168.241.12', 1514))
    while True:
        payload, peer = sock.recvfrom(8192)
        record = dict(received_at=time.time(), source=peer[0], message=payload.decode(errors='replace'))
        with lock:
            records.append(record)
            with log.open('a') as f:
                f.write(json.dumps(record) + '\n')
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ('/health', '/events'):
            self.send_error(404); return
        with lock:
            value = {'service': 'soft3888-management', 'events': list(records)}
        data = json.dumps(value).encode()
        self.send_response(200); self.send_header('Content-Type','application/json')
        self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)
threading.Thread(target=collect, daemon=True).start()
ThreadingHTTPServer(('192.168.241.12', 9100), Handler).serve_forever()
