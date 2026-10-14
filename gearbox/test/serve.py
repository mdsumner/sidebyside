"""Static server with HTTP Range support and CORS, for local testing."""
import os, re, sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

class H(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Range")
        self.send_header("Access-Control-Expose-Headers", "Content-Range, Content-Length, Content-Type")
        super().end_headers()
    def do_OPTIONS(self):
        self.send_response(204); self.end_headers()
    def log_message(self, *a):
        pass
    def do_GET(self):
        rng = self.headers.get("Range")
        path = self.translate_path(self.path)
        if not rng or not os.path.isfile(path):
            return super().do_GET()
        size = os.path.getsize(path)
        m = re.match(r"bytes=(\d*)-(\d*)", rng)
        if m.group(1) == "":  # suffix range: the last N bytes
            a = max(0, size - int(m.group(2))); b = size - 1
        else:
            a = int(m.group(1)); b = int(m.group(2)) if m.group(2) else size - 1
        b = min(b, size - 1)
        if a >= size:
            self.send_response(416); self.send_header("Content-Range", "bytes */%d" % size); self.end_headers(); return
        with open(path, "rb") as f:
            f.seek(a); data = f.read(b - a + 1)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", "bytes %d-%d/%d" % (a, b, size))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

if __name__ == "__main__":
    os.chdir(sys.argv[1])
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[2])), H).serve_forever()
