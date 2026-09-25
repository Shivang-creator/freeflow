"""voice/hud_client.py — Python Client for the Native Siri-Style JARVIS HUD.

Communicates with the floating macOS HUD window via /tmp/jarvis_hud.sock.
Automatically launches the native jarvis-hud binary if not already running.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Optional

log = logging.getLogger("ironman.hud")

SOCKET_PATH = "/tmp/jarvis_hud.sock"
HUD_BINARY = Path(__file__).resolve().parent.parent / "hud" / "jarvis-hud"


def is_hud_running() -> bool:
    """Checks if the jarvis_hud socket is actively accepting connections."""
    if not os.path.exists(SOCKET_PATH):
        return False
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(0.15)
            s.connect(SOCKET_PATH)
            return True
    except Exception:
        return False


def ensure_hud_running() -> bool:
    """Ensures the background Swift HUD process is running."""
    if is_hud_running():
        return True

    if not HUD_BINARY.exists():
        log.warning("HUD binary does not exist at %s", HUD_BINARY)
        return False

    try:
        log.info("🚀 Launching native Siri-style JARVIS HUD overlay...")
        subprocess.Popen([str(HUD_BINARY)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Give it a fraction of a second to bind the socket
        for _ in range(15):
            time.sleep(0.08)
            if is_hud_running():
                log.info("✅ JARVIS HUD connected successfully.")
                return True
    except Exception as e:
        log.error("Failed to start JARVIS HUD process: %s", e)

    return False


def send_hud_event(
    state: str,
    text: str = "",
    title: str = "JARVIS",
    auto_hide: Optional[float] = None,
) -> bool:
    """Sends a state update to the native Siri-style floating HUD."""
    ensure_hud_running()

    payload = {
        "state": state,
        "text": text,
        "title": title,
    }
    if auto_hide is not None:
        payload["auto_hide"] = auto_hide

    try:
        msg = json.dumps(payload) + "\n"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            s.connect(SOCKET_PATH)
            s.sendall(msg.encode("utf-8"))
            return True
    except Exception as e:
        log.debug("HUD event dispatch failed: %s", e)
        return False


def hud_listening(text: str = "Listening...", auto_hide: float = 12.0) -> None:
    send_hud_event("listening", text=text, title="JARVIS", auto_hide=auto_hide)


def hud_transcribing(text: str = "Transcribing...") -> None:
    send_hud_event("thinking", text=text, title="JARVIS")


def hud_thinking(text: str) -> None:
    send_hud_event("thinking", text=text, title="JARVIS")


def hud_speaking(agent: str, text: str, auto_hide: float = 6.0) -> None:
    # Truncate text for sleek HUD display if very long
    display_text = text if len(text) <= 90 else text[:87] + "..."
    send_hud_event("speaking", text=display_text, title=agent, auto_hide=auto_hide)


def hud_hide() -> None:
    send_hud_event("hide")
