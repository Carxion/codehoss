from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = ("Now you can hear me\n").encode()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body)


print("listening on 8000", flush=True)
HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
