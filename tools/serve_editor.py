#!/usr/bin/env python3
"""
serve_editor.py

最小本地 HTTP server，给 editor.html 提供 GET（静态文件）+ PUT（保存 spec）+ POST /render 接口。
防 file:// CORS 限制，让 editor 能 fetch + 保存 + 重渲染闭环。

使用：
  python3 tools/serve_editor.py [--port 8080]
  浏览器打开 http://localhost:8080/editor/editor.html
"""

import argparse
import http.server
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PROJECT_ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_PUT(self):
        # 仅允许写 specs/ 目录下 .json
        rel = self.path.lstrip("/")
        target = (PROJECT_ROOT / rel).resolve()
        if not str(target).startswith(str((PROJECT_ROOT / "specs").resolve())):
            self.send_error(403, "PUT only allowed under /specs/")
            return
        if not target.suffix == ".json":
            self.send_error(403, "PUT only .json files")
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            json.loads(body)  # validate
        except Exception as e:
            self.send_error(400, f"Invalid JSON: {e}")
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True, "path": rel}).encode("utf-8"))

    def do_POST(self):
        # POST /api/check  → 跑 mechanical_check + template_diff
        # POST /api/render → 跑 render.py
        if self.path == "/api/check":
            self._run_check()
        elif self.path == "/api/render":
            self._run_render()
        else:
            self.send_error(404)

    def _run_check(self):
        spec = PROJECT_ROOT / "specs" / "demo_lighting_req.spec.json"
        schema = PROJECT_ROOT / "schema" / "lighting_req.schema.json"
        try:
            subprocess.run([sys.executable, "tools/mechanical_check.py", str(spec), str(schema), "--quiet"],
                           cwd=PROJECT_ROOT, check=False, capture_output=True)
            subprocess.run([sys.executable, "tools/template_diff.py", str(spec), "--quiet"],
                           cwd=PROJECT_ROOT, check=False, capture_output=True)
            self._json_ok({"ok": True})
        except Exception as e:
            self.send_error(500, str(e))

    def _run_render(self):
        spec = PROJECT_ROOT / "specs" / "demo_lighting_req.spec.json"
        tmpl = PROJECT_ROOT / "templates" / "lighting_req.html.tmpl"
        out = PROJECT_ROOT / "outputs" / "demo.html"
        try:
            subprocess.run([sys.executable, "tools/render.py", str(spec), str(tmpl), str(out)],
                           cwd=PROJECT_ROOT, check=True, capture_output=True)
            self._json_ok({"ok": True, "output": "outputs/demo.html"})
        except subprocess.CalledProcessError as e:
            self.send_error(500, e.stderr.decode("utf-8", errors="replace") if e.stderr else "render failed")

    def _json_ok(self, payload):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    httpd = http.server.HTTPServer(("127.0.0.1", args.port), Handler)
    print(f"serving level-design-deck at http://127.0.0.1:{args.port}/")
    print(f"open editor: http://127.0.0.1:{args.port}/editor/editor.html")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
