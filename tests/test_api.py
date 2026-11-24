"""Unit tests for FreeFlow embedded REST API server."""

import json
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from freeflow.config import ConfigManager
from freeflow.dictionary import DictionaryManager
from freeflow.engine import DictationEngine
from freeflow.history import HistoryManager
from freeflow.server import APIServer


def test_api_endpoints():
    engine = DictationEngine(prewarm=False)
    server = APIServer(engine=engine, port=52888)
    server.start()
    time.sleep(0.3)

    base = "http://127.0.0.1:52888"

    try:
        # 1. Test status
        with urllib.request.urlopen(f"{base}/api/status") as resp:
            data = json.loads(resp.read().decode())
            assert data["app"] == "FreeFlow"
            assert "active_model" in data

        # 2. Test models
        with urllib.request.urlopen(f"{base}/api/models") as resp:
            data = json.loads(resp.read().decode())
            assert len(data["models"]) == 3

        # 3. Test dictionary
        with urllib.request.urlopen(f"{base}/api/dictionary") as resp:
            data = json.loads(resp.read().decode())
            assert "vocabulary" in data
            assert "corrections" in data

        # 4. Test add word
        req = urllib.request.Request(
            f"{base}/api/dictionary/word",
            data=json.dumps({"word": "UnitTestTerm"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode())
            assert res["status"] == "ok"

        # Check word was added
        with urllib.request.urlopen(f"{base}/api/dictionary") as resp:
            data = json.loads(resp.read().decode())
            assert "UnitTestTerm" in data["vocabulary"]

        # 5. Delete word
        req = urllib.request.Request(
            f"{base}/api/dictionary/word",
            data=json.dumps({"word": "UnitTestTerm"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="DELETE",
        )
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode())
            assert res["status"] == "ok"

        # 6. Test history
        with urllib.request.urlopen(f"{base}/api/history") as resp:
            data = json.loads(resp.read().decode())
            assert "entries" in data

    finally:
        server.stop()

    print("✅ All FreeFlow API tests passed successfully!")


def _call(url, method="GET", body=None, headers=None):
    """Returns (status, response headers, body text) without raising on 4xx."""
    req = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.headers, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read().decode()


def test_api_only_answers_its_own_ui():
    """A web page open in the user's browser must not be able to use the API.

    The server has no login and returns dictation history, so every way a foreign
    site can reach 127.0.0.1 has to be refused: CORS reads, cross-site form-style
    POSTs, preflighted DELETEs, and DNS rebinding.
    """
    port = 52889
    base = f"http://127.0.0.1:{port}"
    evil = "https://evil.example"

    with tempfile.TemporaryDirectory() as d:
        history = HistoryManager(history_path=Path(d) / "history.json")
        dictionary = DictionaryManager(dict_path=Path(d) / "dictionary.json")
        engine = DictationEngine(
            config_mgr=ConfigManager(config_path=Path(d) / "config.json"),
            history_mgr=history,
            dict_mgr=dictionary,
            prewarm=False,
        )
        history.add_entry(text="my private dictation")
        server = APIServer(engine=engine, port=port)
        server.start()
        time.sleep(0.3)

        try:
            # The UI itself (same origin) keeps working, with and without an Origin header.
            status, headers, body = _call(f"{base}/api/history")
            assert status == 200 and "my private dictation" in body
            # ...and no response may invite other origins to read it.
            assert headers.get("Access-Control-Allow-Origin") is None

            status, _, _ = _call(
                f"{base}/api/dictionary/word", "POST",
                json.dumps({"word": "SameOriginTerm"}).encode(),
                {"Content-Type": "application/json", "Origin": base},
            )
            assert status == 200 and "SameOriginTerm" in dictionary.vocabulary

            # 1. Cross-origin read of the dictation history.
            status, headers, body = _call(f"{base}/api/history", headers={"Origin": evil})
            assert status == 403 and "my private dictation" not in body
            assert headers.get("Access-Control-Allow-Origin") is None

            # 2. Cross-site "simple" POST (text/plain needs no preflight) planting a
            #    correction that would be pasted into every future dictation.
            status, _, _ = _call(
                f"{base}/api/dictionary/correction", "POST",
                json.dumps({"heard": "the", "write": "INJECTED"}).encode(),
                {"Content-Type": "text/plain", "Origin": evil},
            )
            assert status == 403 and "the" not in dictionary.corrections

            # 3. Preflight for a cross-site DELETE (wipe history) is not approved.
            status, headers, _ = _call(
                f"{base}/api/history", "OPTIONS",
                headers={"Origin": evil, "Access-Control-Request-Method": "DELETE"},
            )
            assert status == 403 and headers.get("Access-Control-Allow-Origin") is None
            status, _, _ = _call(f"{base}/api/history", "DELETE", b"{}", {"Origin": evil})
            assert status == 403 and len(history.entries) == 1

            # 4. DNS rebinding: the page's own hostname now resolves to 127.0.0.1,
            #    so the request is "same-origin" to the browser but the Host is wrong.
            status, _, body = _call(f"{base}/api/history", headers={"Host": f"evil.example:{port}"})
            assert status == 403 and "my private dictation" not in body
        finally:
            server.stop()

    print("✅ FreeFlow API rejects cross-origin and rebinding requests!")


if __name__ == "__main__":
    test_api_endpoints()
    test_api_only_answers_its_own_ui()
