"""Serve the model over HTTP: GET /health, POST /predict (JSON)."""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from model import predict

with open("model/model.json") as f:
    MODEL = json.load(f)
PORT = int(os.environ.get("PORT", "8080"))

# Counters for /metrics (Prometheus text format).
STATS = {"predictions": 0, "errors": 0}


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"status": "ok", "model_version": MODEL["version"]})
        elif self.path == "/metrics":
            text = (
                "# TYPE predictions_total counter\n"
                f"predictions_total {STATS['predictions']}\n"
                "# TYPE prediction_errors_total counter\n"
                f"prediction_errors_total {STATS['errors']}\n"
                "# TYPE model_info gauge\n"
                f'model_info{{version="{MODEL["version"]}"}} 1\n'
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(text)))
            self.end_headers()
            self.wfile.write(text)
        else:
            self.send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/predict":
            return self.send_json(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            values = {f: float(body[f]) for f in MODEL["features"]}
        except (ValueError, KeyError, TypeError):
            STATS["errors"] += 1
            features = ", ".join(MODEL["features"])
            return self.send_json(400, {"error": f"send JSON with numbers for {features}"})
        price = predict(MODEL["weights"], MODEL["features"], values)
        STATS["predictions"] += 1
        self.send_json(200, {"price": round(price, 2), "model_version": MODEL["version"]})

    def log_message(self, *args):  # keep the terminal quiet
        pass


if __name__ == "__main__":
    print(f"serving model {MODEL['version']} on port {PORT}", flush=True)
    ThreadingHTTPServer(("", PORT), Handler).serve_forever()
