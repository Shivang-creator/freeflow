"""freeflow/server.py — Lightweight Local HTTP API & Web UI Server for FreeFlow."""

from __future__ import annotations

import json
import logging
import mimetypes
import socket
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional

from freeflow.constants import APP_NAME, APP_VERSION, HOTKEYS, MODELS
from freeflow.engine import DictationEngine
from freeflow.injector import TextInjector
from freeflow.transcriber import download_model, is_model_cached

log = logging.getLogger("freeflow.server")
WEB_DIR = Path(__file__).resolve().parent / "web"


def find_free_port(start_port: int = 52834) -> int:
    """Finds an available local port starting from start_port."""
    for port in range(start_port, start_port + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return 0


class FreeFlowAPIHandler(BaseHTTPRequestHandler):
    """Handles REST API and serves the embedded glassmorphic Web UI."""

    engine: DictationEngine

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress noisy HTTP request logging
        return

    def _send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 0:
                body = self.rfile.read(content_length).decode("utf-8")
                return json.loads(body)
        except Exception as e:
            log.debug("JSON parse error: %s", e)
        return {}

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # Static assets
        if path in ("/", "/index.html"):
            return self._serve_file(WEB_DIR / "index.html", "text/html")
        elif path == "/style.css":
            return self._serve_file(WEB_DIR / "style.css", "text/css")
        elif path == "/app.js":
            return self._serve_file(WEB_DIR / "app.js", "application/javascript")

        # API Endpoints
        if path == "/api/status":
            cfg = self.engine.config_mgr.config
            model_info = self.engine.config_mgr.get_model_info()
            return self._send_json({
                "app": APP_NAME,
                "version": APP_VERSION,
                "state": self.engine.current_state,
                "active_model": model_info,
                "hotkey": cfg.hotkey,
                "enable_slm": cfg.enable_slm,
                "slm_model": cfg.slm_model,
                "enable_sound": cfg.enable_sound,
                "enable_hud": cfg.enable_hud,
                "vad_pause_seconds": cfg.vad_pause_seconds,
                "vocab_count": len(self.engine.dictionary_mgr.vocabulary),
                "corrections_count": len(self.engine.dictionary_mgr.corrections),
                "history_count": len(self.engine.history_mgr.entries),
            })

        if path == "/api/models":
            model_list = []
            active_repo = self.engine.transcriber.model_repo
            for m_id, m in MODELS.items():
                item = dict(m)
                item["is_cached"] = is_model_cached(m["repo"])
                item["is_active"] = (m["repo"] == active_repo)
                model_list.append(item)
            return self._send_json({"models": model_list})

        if path == "/api/dictionary":
            return self._send_json(self.engine.dictionary_mgr.to_dict())

        if path == "/api/history":
            limit = int(query.get("limit", ["50"])[0])
            q = query.get("q", [""])[0]
            entries = self.engine.history_mgr.get_recent(limit=limit, query=q)
            return self._send_json({"entries": entries})

        if path == "/api/config":
            return self._send_json({
                "config": self.engine.config_mgr.config.to_dict(),
                "hotkeys": HOTKEYS,
            })

        self.send_error(404, "Endpoint not found")

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        data = self._read_json()

        if path == "/api/models/activate":
            repo = data.get("repo")
            model_id = data.get("model_id")
            if model_id and model_id in MODELS:
                repo = MODELS[model_id]["repo"]
            if repo:
                self.engine.switch_model(repo)
                return self._send_json({"status": "ok", "active_model": repo})
            return self._send_json({"error": "Missing model repo or ID"}, status=400)

        if path == "/api/models/download":
            repo = data.get("repo")
            if not repo:
                return self._send_json({"error": "Missing repo"}, status=400)

            def _bg_download() -> None:
                download_model(repo)

            threading.Thread(target=_bg_download, daemon=True).start()
            return self._send_json({"status": "downloading", "repo": repo})

        if path == "/api/dictionary/word":
            word = data.get("word", "")
            success = self.engine.dictionary_mgr.add_word(word)
            return self._send_json({"status": "ok", "added": success, "word": word})

        if path == "/api/dictionary/correction":
            heard = data.get("heard", "")
            write = data.get("write", "")
            success = self.engine.dictionary_mgr.add_correction(heard, write)
            return self._send_json({"status": "ok", "added": success, "heard": heard, "write": write})

        if path == "/api/history/copy":
            text = data.get("text", "")
            success = TextInjector.set_clipboard(text)
            return self._send_json({"status": "ok", "copied": success})

        if path == "/api/config":
            updated = self.engine.config_mgr.update(**data)
            # Apply dynamic changes directly to engine
            if "enable_sound" in data:
                self.engine.hud.enable_sound = updated.enable_sound
            if "enable_hud" in data:
                self.engine.hud.enable_hud = updated.enable_hud
            if "enable_slm" in data:
                self.engine.enable_slm = updated.enable_slm
            if "slm_model" in data:
                self.engine.slm_cleaner.model_name = updated.slm_model
            return self._send_json({"status": "ok", "config": updated.to_dict()})

        self.send_error(404, "Endpoint not found")

    def do_DELETE(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        data = self._read_json()

        if path == "/api/dictionary/word":
            word = data.get("word", "")
            removed = self.engine.dictionary_mgr.remove_word(word)
            return self._send_json({"status": "ok", "removed": removed})

        if path == "/api/dictionary/correction":
            heard = data.get("heard", "")
            removed = self.engine.dictionary_mgr.remove_correction(heard)
            return self._send_json({"status": "ok", "removed": removed})

        if path == "/api/history":
            entry_id = data.get("id")
            if entry_id:
                removed = self.engine.history_mgr.delete_entry(entry_id)
                return self._send_json({"status": "ok", "deleted": removed})
            else:
                self.engine.history_mgr.clear()
                return self._send_json({"status": "ok", "cleared": True})

        self.send_error(404, "Endpoint not found")

    def _serve_file(self, file_path: Path, content_type: str) -> None:
        if not file_path.exists():
            self.send_error(404, f"File {file_path.name} not found")
            return
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error reading file: {e}")


class APIServer:
    """Manages the background HTTP server for FreeFlow."""

    def __init__(self, engine: DictationEngine, port: int = 0) -> None:
        self.engine = engine
        self.port = port or find_free_port()
        FreeFlowAPIHandler.engine = self.engine
        self.httpd = ThreadingHTTPServer(("127.0.0.1", self.port), FreeFlowAPIHandler)
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        log.info("Starting FreeFlow Local Web API server on http://127.0.0.1:%d", self.port)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"
