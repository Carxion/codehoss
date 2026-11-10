import json
import os
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

API_URL = os.environ.get("API_URL", "http://localhost:5000")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            with urllib.request.urlopen(API_URL, timeout=3) as r:
                fruit = json.load(r)["fruit"]
            body, code = "Fruit: " + ", ".join(fruit) + "\n", 200
        except OSError as e:
            body, code = f"Can't reach the API at {API_URL}: {e}\n", 502
        self.send_response(code)
        self.end_headers()
        self.wfile.write(body.encode())


HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
