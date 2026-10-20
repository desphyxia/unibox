"""Serve the web build to devices on the same Wi-Fi (for trying it on an iPad without a Mac). The published copy on
GitHub Pages (https) needs none of this; it is for quick checks of a local build.

Build:  godot --headless --path . --export-release "Web" build/web/index.html     (needs Godot 4.7.2 web export templates)
Run:    python serve_web.py      then open the printed address in Safari on the iPad (same Wi-Fi).
Once, in an admin PowerShell, let the iPad reach this port on home (Private) networks:
        New-NetFirewallRule -DisplayName "Fox web test 8060" -Direction Inbound -Protocol TCP -LocalPort 8060 -Profile Private -Action Allow
Sound is off when served this way: browsers allow web audio only on https pages, and a home network serves plain http.
"""
import functools, http.server, os, socket

PORT = 8060
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build", "web")


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".wasm": "application/wasm", ".pck": "application/octet-stream"}

    def do_GET(self):
        # Plain http is all a home network has. Godot's page refuses to start without https ("Secure Context"), which a
        # build without threads doesn't need, so drop that one check; and browsers block web audio on http, so start
        # the engine with no sound.
        if self.path.split("?")[0] in ("/", "/index.html"):
            html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
            old = "const missing = Engine.getMissingFeatures({\n\t\tthreads: GODOT_THREADS_ENABLED,\n\t});"
            if old in html:
                html = html.replace(old, old[:-1] + ".filter((m) => !m.startsWith('Secure Context'));")
            html = html.replace('const GODOT_CONFIG = {"args":[]', 'const GODOT_CONFIG = {"args":["--audio-driver","Dummy"]', 1)
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")   # always load the newest build
        super().end_headers()


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.168.0.1", 9))                   # no traffic is sent; this just picks the Wi-Fi address
        return s.getsockname()[0]
    finally:
        s.close()


if __name__ == "__main__":
    if not os.path.exists(os.path.join(ROOT, "index.html")):
        raise SystemExit("No web build yet: export the 'Web' preset to build/web first.")
    print(f"Open on the iPad:  http://{lan_ip()}:{PORT}/")
    http.server.ThreadingHTTPServer(("0.0.0.0", PORT), functools.partial(Handler, directory=ROOT)).serve_forever()
