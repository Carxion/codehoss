import json
import os
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

DB_URL = os.environ.get("DB_URL", "http://db:6000")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            with urllib.request.urlopen(DB_URL, timeout=3) as r:
                body, code = f"The answer is {json.load(r)['answer']}\n", 200
        except OSError as e:
            body, code = f"Can't reach the database at {DB_URL}: {e}\n", 502
        self.send_response(code)
        self.end_headers()
        self.wfile.write(body.encode())


print("listening on 8000", flush=True)
HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
