"""whisper_flow/hud_client.py — Client for the Native Siri-Style FreeFlow Floating HUD."""

from __future__ import annotations

import json
import logging
import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Optional

from whisper_flow.constants import FREEFLOW_HUD_SOCKET, LEGACY_HUD_SOCKET

log = logging.getLogger("freeflow.hud")

HUD_DIR = Path(__file__).resolve().parent.parent / "hud"
HUD_BINARY = HUD_DIR / "freeflow-hud"
LEGACY_BINARY = HUD_DIR / "jarvis-hud"


def get_active_socket_path() -> str:
    if os.path.exists(FREEFLOW_HUD_SOCKET):
        return FREEFLOW_HUD_SOCKET
    if os.path.exists(LEGACY_HUD_SOCKET):
        return LEGACY_HUD_SOCKET
    return FREEFLOW_HUD_SOCKET


def is_hud_running() -> bool:
    """Checks if the HUD socket is actively accepting connections."""
    sock_path = get_active_socket_path()
    if not os.path.exists(sock_path):
        return False
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(0.15)
            s.connect(sock_path)
            return True
    except Exception:
        return False


def ensure_hud_running() -> bool:
    """Ensures the background Swift floating HUD process is running."""
    if is_hud_running():
        return True

    target_binary = HUD_BINARY if HUD_BINARY.exists() else LEGACY_BINARY
    if not target_binary.exists():
        log.warning("HUD binary does not exist at %s", target_binary)
        return False

    try:
        log.info("🚀 Launching native FreeFlow floating pill HUD overlay...")
        subprocess.Popen([str(target_binary)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(15):
            time.sleep(0.08)
            if is_hud_running():
                log.info("✅ FreeFlow HUD connected successfully.")
                return True
    except Exception as e:
        log.error("Failed to start HUD process: %s", e)

    return False


def send_hud_event(
    state: str,
    text: str = "",
    title: str = "FreeFlow",
    auto_hide: Optional[float] = None,
) -> bool:
    """Sends a state update to the native floating HUD."""
    ensure_hud_running()
    sock_path = get_active_socket_path()

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
            s.connect(sock_path)
            s.sendall(msg.encode("utf-8"))
            return True
    except Exception as e:
        log.debug("HUD event dispatch failed: %s", e)
        return False


def hud_listening(text: str = "Listening...", auto_hide: float = 12.0) -> None:
    send_hud_event("listening", text=text, title="FreeFlow", auto_hide=auto_hide)


def hud_transcribing(text: str = "Transcribing...") -> None:
    send_hud_event("thinking", text=text, title="FreeFlow")


def hud_formatting(app_name: str = "") -> None:
    msg = f"Formatting for {app_name}..." if app_name else "Refining text..."
    send_hud_event("thinking", text=msg, title="FreeFlow")


def hud_done(preview_text: str = "", auto_hide: float = 2.0) -> None:
    display_text = preview_text if len(preview_text) <= 90 else preview_text[:87] + "..."
    send_hud_event("speaking", text=display_text or "Injected!", title="FreeFlow", auto_hide=auto_hide)


def hud_hide() -> None:
    send_hud_event("hide")
