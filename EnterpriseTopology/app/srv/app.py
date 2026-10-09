from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import urlopen

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            with urlopen('http://10.30.20.10:8080/', timeout=2) as response:
                data=response.read()
            status, body=200, b'app: healthy\n' + data
        except Exception:
            status, body=503, b'app: database dependency unavailable\n'
        self.send_response(status)
        self.send_header('Content-Type','text/plain')
        self.end_headers()
        self.wfile.write(body)

HTTPServer(('0.0.0.0',80),Handler).serve_forever()
