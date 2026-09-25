"""whisper_flow/hud.py — Visual & Audio State Feedback for Dictation."""

from __future__ import annotations

import logging
import subprocess
from typing import Optional

from whisper_flow.hud_client import (
    hud_done,
    hud_formatting,
    hud_hide,
    hud_listening,
    hud_transcribing,
)

log = logging.getLogger("freeflow.hud")


class DictationHUD:
    """Manages visual indicator and sound effects during dictation."""

    def __init__(self, enable_sound: bool = True, enable_hud: bool = True) -> None:
        self.enable_sound = enable_sound
        self.enable_hud = enable_hud

    def play_sound(self, sound_name: str = "Tink") -> None:
        if not self.enable_sound:
            return
        sound_path = f"/System/Library/Sounds/{sound_name}.aiff"
        try:
            subprocess.Popen(
                ["afplay", sound_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    def on_recording_start(self) -> None:
        self.play_sound("Pop")
        if self.enable_hud:
            hud_listening(text="Listening...", auto_hide=15.0)

    def on_transcribing(self) -> None:
        if self.enable_hud:
            hud_transcribing(text="Transcribing with MLX...")

    def on_formatting(self, app_name: str = "") -> None:
        if self.enable_hud:
            hud_formatting(app_name=app_name)

    def on_complete(self, preview_text: str = "") -> None:
        self.play_sound("Tink")
        if self.enable_hud:
            hud_done(preview_text=preview_text, auto_hide=1.8)

    def on_cancel(self) -> None:
        if self.enable_hud:
            hud_hide()
