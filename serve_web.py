import mimetypes
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

mimetypes.add_type("application/manifest+json", ".webmanifest")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("application/vnd.android.package-archive", ".apk")
mimetypes.add_type("application/x-apple-aspen-config", ".mobileconfig")

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "dist")
PORT = int(os.environ.get("PORT", "8011"))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def do_GET(self):
        path = self.translate_path(self.path)
        if not os.path.exists(path) or os.path.isdir(path):
            self.path = "/index.html"
        return super().do_GET()

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
