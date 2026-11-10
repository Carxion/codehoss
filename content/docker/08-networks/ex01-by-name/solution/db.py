import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = (json.dumps({"answer": 42})).encode()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body)


print("listening on 6000", flush=True)
HTTPServer(("0.0.0.0", 6000), Handler).serve_forever()
