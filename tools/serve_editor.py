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
from urllib.parse import urlparse, parse_qs

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def list_specs():
    """列出 specs/*.spec.json 的 stem（去掉 .spec 后缀）。"""
    specs_dir = PROJECT_ROOT / "specs"
    return sorted(p.stem.replace(".spec", "") for p in specs_dir.glob("*.spec.json"))


def infer_paths(spec_id):
    """spec_id → (spec_path, schema_path, template_path)。
    扫 schema/，按最长 module 名前缀匹配（与 regenerate_field.infer_schema_path 同思路）。"""
    schema_dir = PROJECT_ROOT / "schema"
    candidates = sorted(
        (p.name[:-len(".schema.json")] for p in schema_dir.glob("*.schema.json")),
        key=len, reverse=True,
    )
    for module in candidates:
        if module in spec_id:
            return (
                PROJECT_ROOT / "specs" / f"{spec_id}.spec.json",
                schema_dir / f"{module}.schema.json",
                PROJECT_ROOT / "templates" / f"{module}.html.tmpl",
            )
    return None


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

    def do_GET(self):
        # GET /api/specs           → 返回 specs/*.spec.json 列表
        # GET /api/paths?spec=<id> → 返回该 spec 的 spec/schema/template 路径
        parsed = urlparse(self.path)
        if parsed.path == "/api/specs":
            self._json_ok({"specs": list_specs()})
            return
        if parsed.path == "/api/paths":
            spec_id = parse_qs(parsed.query).get("spec", [""])[0]
            paths = infer_paths(spec_id)
            if paths:
                spec, schema, tmpl = paths
                self._json_ok({
                    "spec": "/" + str(spec.relative_to(PROJECT_ROOT)),
                    "schema": "/" + str(schema.relative_to(PROJECT_ROOT)),
                    "template": "/" + str(tmpl.relative_to(PROJECT_ROOT)),
                })
            else:
                self.send_error(400, f"cannot infer paths for {spec_id!r}")
            return
        super().do_GET()

    def do_POST(self):
        # POST /api/check?spec=<id>       → 跑 mechanical_check + template_diff + cross_check
        # POST /api/render?spec=<id>      → 跑 render.py
        # POST /api/cross-check?level_id= → 单独跑 cross_check（供 editor.html 按需调用）
        parsed = urlparse(self.path)
        if parsed.path == "/api/check":
            self._run_check(self._spec_id_from_query(parsed))
        elif parsed.path == "/api/render":
            self._run_render(self._spec_id_from_query(parsed))
        elif parsed.path == "/api/cross-check":
            qs = parse_qs(parsed.query)
            level_id = qs.get("level_id", [""])[0]
            self._run_cross_check(level_id)
        elif parsed.path == "/api/render-level":
            qs = parse_qs(parsed.query)
            level_id = qs.get("level_id", [""])[0]
            self._run_render_level(level_id)
        elif parsed.path == "/api/render-deck":
            qs = parse_qs(parsed.query)
            level_id = qs.get("level_id", [""])[0]
            if not level_id:
                self._json_error("missing level_id")
                return
            result = subprocess.run(
                [sys.executable, str(PROJECT_ROOT / "tools" / "render_deck.py"), "--level-id", level_id],
                capture_output=True, text=True, cwd=str(PROJECT_ROOT)
            )
            if result.returncode != 0:
                self._json_error(result.stderr or "render_deck failed")
                return
            self._json_ok({"path": f"outputs/level_{level_id}__deck.html"})
        else:
            self.send_error(404)

    def _spec_id_from_query(self, parsed):
        qs = parse_qs(parsed.query)
        spec_id = qs.get("spec", ["demo_lighting_req"])[0]
        return spec_id

    def _resolve_paths_or_500(self, spec_id):
        paths = infer_paths(spec_id)
        if not paths:
            self.send_error(400, f"cannot infer module for spec_id {spec_id!r}")
            return None
        spec, schema, tmpl = paths
        if not spec.exists():
            self.send_error(404, f"spec not found: {spec.relative_to(PROJECT_ROOT)}")
            return None
        return paths

    def _run_check(self, spec_id):
        paths = self._resolve_paths_or_500(spec_id)
        if not paths:
            return
        spec, schema, _ = paths
        try:
            subprocess.run([sys.executable, "tools/mechanical_check.py", str(spec), str(schema), "--quiet"],
                           cwd=PROJECT_ROOT, check=False, capture_output=True)
            subprocess.run([sys.executable, "tools/template_diff.py", str(spec), "--quiet"],
                           cwd=PROJECT_ROOT, check=False, capture_output=True)
            # 额外跑 cross_check，结果独立写 .cross_warnings.json
            level_id = self._extract_level_id(spec)
            if level_id:
                subprocess.run([sys.executable, "tools/cross_check.py", "--level-id", level_id],
                               cwd=PROJECT_ROOT, check=False, capture_output=True)
            self._json_ok({"ok": True, "spec_id": spec_id})
        except Exception as e:
            self.send_error(500, str(e))

    def _run_cross_check(self, level_id):
        if not level_id:
            self.send_error(400, "level_id required")
            return
        try:
            subprocess.run([sys.executable, "tools/cross_check.py", "--level-id", level_id],
                           cwd=PROJECT_ROOT, check=False, capture_output=True)
            self._json_ok({"ok": True, "level_id": level_id,
                           "output": "outputs/.cross_warnings.json"})
        except Exception as e:
            self.send_error(500, str(e))

    def _extract_level_id(self, spec_path: Path) -> str:
        try:
            import json as _json
            spec = _json.loads(spec_path.read_text(encoding="utf-8"))
            meta = spec.get("meta", {})
            if meta.get("level_id"):
                return meta["level_id"].strip()
            spec_id = (meta.get("spec_id") or "").strip()
            schema_dir = PROJECT_ROOT / "schema"
            modules = sorted(
                (p.name[:-len(".schema.json")] for p in schema_dir.glob("*.schema.json")),
                key=len, reverse=True,
            )
            for module in modules:
                prefix = module + "_"
                if spec_id.startswith(prefix):
                    return spec_id[len(prefix):]
        except Exception:
            pass
        return ""

    def _run_render(self, spec_id):
        paths = self._resolve_paths_or_500(spec_id)
        if not paths:
            return
        spec, _, tmpl = paths
        out = PROJECT_ROOT / "outputs" / f"{spec_id}.html"
        try:
            subprocess.run([sys.executable, "tools/render.py", str(spec), str(tmpl), str(out)],
                           cwd=PROJECT_ROOT, check=True, capture_output=True)
            self._json_ok({"ok": True, "spec_id": spec_id, "output": f"outputs/{spec_id}.html"})
        except subprocess.CalledProcessError as e:
            self.send_error(500, e.stderr.decode("utf-8", errors="replace") if e.stderr else "render failed")

    def _run_render_level(self, level_id):
        if not level_id:
            self.send_error(400, "level_id required")
            return
        try:
            r = subprocess.run([sys.executable, "tools/render_level.py", "--level-id", level_id, "--render-missing"],
                               cwd=PROJECT_ROOT, check=True, capture_output=True)
            self._json_ok({"ok": True, "level_id": level_id, "output": f"outputs/level_{level_id}__full.html",
                           "stdout": r.stdout.decode("utf-8", errors="replace").strip()})
        except subprocess.CalledProcessError as e:
            self.send_error(500, e.stderr.decode("utf-8", errors="replace") if e.stderr else "render-level failed")

    def _json_ok(self, payload):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def _json_error(self, msg):
        self.send_response(400)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": msg}).encode("utf-8"))


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
