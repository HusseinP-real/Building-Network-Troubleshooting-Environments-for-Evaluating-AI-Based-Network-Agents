from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import urlopen

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            with urlopen('http://10.60.6.11:8080/', timeout=2) as response:
                backend = response.read()
            status, body = 200, b'application: healthy\n' + backend
        except Exception:
            status, body = 503, b'application: backend unavailable\n'
        self.send_response(status)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(body)

HTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
