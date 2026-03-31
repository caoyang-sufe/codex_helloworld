import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(ROOT_DIR, "assets")


def list_png_paths(folder_name: str) -> list[str]:
    folder = os.path.join(ASSETS_DIR, folder_name)
    if not os.path.isdir(folder):
        return []
    files = []
    for name in os.listdir(folder):
        if name.lower().endswith(".png"):
            files.append(f"assets/{folder_name}/{name}")
    return sorted(files)


class GameRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/cards":
            payload = {
                "cards": list_png_paths("card"),
                "pieces": list_png_paths("piece"),
            }
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        super().do_GET()


def main():
    os.chdir(ROOT_DIR)
    server = ThreadingHTTPServer(("localhost", 8080), GameRequestHandler)
    print("Serving on http://localhost:8080")
    server.serve_forever()


if __name__ == "__main__":
    main()
