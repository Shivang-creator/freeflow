"""voice/dictation/hud.py — Visual & Audio State Feedback for Dictation.

Uses the native Swift JARVIS HUD overlay + non-blocking macOS audio feedback.
States:
- Listening: Subtle glowing pill "Dictating..." + soft audio chirp
- Formatting: "Refining text..."
- Done: "Injected" -> Auto-dismiss
"""

from __future__ import annotations

import logging
import subprocess
from typing import Optional

from whisper_flow.hud_client import hud_hide, hud_listening, hud_transcribing, send_hud_event

log = logging.getLogger("dictation.hud")


class DictationHUD:
    """Manages visual indicator and sound effects during dictation."""

    @staticmethod
    def play_sound(sound_name: str = "Tink") -> None:
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
        hud_listening(text="Listening...", auto_hide=15.0)

    def on_transcribing(self) -> None:
        hud_transcribing(text="Transcribing with MLX...")

    def on_formatting(self, app_name: str) -> None:
        send_hud_event("thinking", text=f"Formatting for {app_name}...", title="Dictation")

    def on_complete(self, preview_text: str = "") -> None:
        self.play_sound("Tink")
        preview = (preview_text[:60] + "...") if len(preview_text) > 60 else preview_text
        send_hud_event("speaking", text=preview or "Pasted!", title="Dictation", auto_hide=1.5)

    def on_cancel(self) -> None:
        hud_hide()
