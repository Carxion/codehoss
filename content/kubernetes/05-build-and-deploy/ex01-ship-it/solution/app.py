from http.server import BaseHTTPRequestHandler, HTTPServer

MESSAGE = "Hello from my own image"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(f"{MESSAGE}\n".encode())


HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
