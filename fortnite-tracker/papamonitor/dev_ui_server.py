"""Servidor local para depurar la UI del monitor con recarga automática."""

from __future__ import annotations

import json
import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


LIVE_RELOAD_SNIPPET = """
<script>
(function () {
  if (!window.pywebview) {
    window.pywebview = {
      api: {
        loaded: async () => {},
        minimize: async () => {},
        kill: async () => {},
        reparar_tarea: async () => {},
        check_updates: async () => {},
        desinstalar_tarea: async () => {},
        toggle_emails: async () => {},
        login_google: async () => {},
        logout: async () => {},
        do_auto_update: async () => {},
        save_token: async () => {},
        get_stats: async () => ({ total_minutes: 120, history: { "2026-04-07": 45, "2026-04-08": 75 } }),
        get_api_context: async () => ({ api_base: "https://papa-monitor.vercel.app", token: "" }),
      },
    };
  }

  let last = "";
  async function poll() {
    try {
      const res = await fetch("/__mtime");
      const data = await res.json();
      if (!last) {
        last = data.mtime;
      } else if (last !== data.mtime) {
        window.location.reload();
      }
    } catch (_) {}
  }
  setInterval(poll, 1000);
  poll();
})();
</script>
"""


class _DevUiHandler(SimpleHTTPRequestHandler):
    ui_root: Path

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(self.ui_root), **kwargs)

    def log_message(self, format, *args):
        return

    def _max_mtime(self) -> float:
        latest = 0.0
        for ext in (".html", ".css", ".js"):
            for p in self.ui_root.rglob(f"*{ext}"):
                try:
                    latest = max(latest, p.stat().st_mtime)
                except OSError:
                    pass
        return latest

    def do_GET(self):
        if self.path == "/__mtime":
            payload = {"mtime": str(self._max_mtime())}
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path in ("/", "/dashboard", "/dashboard.html"):
            html_path = self.ui_root / "dashboard.html"
            html = html_path.read_text(encoding="utf-8")
            html = html.replace("</body>", f"{LIVE_RELOAD_SNIPPET}\n</body>")
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        super().do_GET()


class DevUiServer:
    def __init__(self, ui_root: str):
        self.ui_root = Path(ui_root).resolve()
        self.server: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.port: int | None = None

    def start(self) -> str:
        handler_cls = type(
            "BoundDevUiHandler",
            (_DevUiHandler,),
            {"ui_root": self.ui_root},
        )
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
        self.port = int(self.server.server_address[1])
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return f"http://127.0.0.1:{self.port}/dashboard"

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
