"""Unit tests for FreeFlow embedded REST API server."""

import json
import time
import urllib.request
from whisper_flow.engine import DictationEngine
from whisper_flow.server import APIServer


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


if __name__ == "__main__":
    test_api_endpoints()
