import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

READY = False


def warm_up():
    global READY
    time.sleep(3)  # loading data...
    READY = True


threading.Thread(target=warm_up, daemon=True).start()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200 if READY else 503)
            self.end_headers()
            self.wfile.write(b"ok" if READY else b"starting")
            return
        body = b"Service is up\n"
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body)


print("listening on 8000", flush=True)
HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
