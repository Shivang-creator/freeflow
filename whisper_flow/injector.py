"""voice/dictation/injector.py — macOS Text Injection into Focused Application.

Dual Strategy:
1. Fast Pasteboard + Command-V simulation:
   Works universally across Native AppKit apps, Web browsers (Chrome, Safari),
   Electron apps (VS Code, Cursor, Slack, Discord, Obsidian), and Terminals.
2. Transparent Clipboard Preservation:
   Saves user's prior clipboard content before pasting, and restores it 50ms later.
"""

from __future__ import annotations

import logging
import subprocess
import time
from typing import Optional

log = logging.getLogger("dictation.injector")


class TextInjector:
    """Injects text into whatever application currently has keyboard focus."""

    @staticmethod
    def get_clipboard() -> str:
        try:
            res = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=0.5)
            return res.stdout
        except Exception:
            return ""

    @staticmethod
    def set_clipboard(text: str) -> bool:
        try:
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            p.communicate(input=text.encode("utf-8"), timeout=0.5)
            return p.returncode == 0
        except Exception as e:
            log.error("Failed to copy text to clipboard: %s", e)
            return False

    @classmethod
    def inject(cls, text: str, restore_clipboard: bool = True) -> bool:
        """Puts text into the active focused field via pasteboard + Cmd+V."""
        if not text:
            return False

        old_clipboard = cls.get_clipboard() if restore_clipboard else ""

        try:
            # 1. Place cleaned text onto pasteboard
            if not cls.set_clipboard(text):
                return False

            # 2. Simulate Command + V via AppleScript
            script = 'tell application "System Events" to keystroke "v" using {command down}'
            res = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=1.0)
            if res.returncode != 0:
                log.warning("AppleScript keystroke failed: %s", res.stderr)
                return False

            log.info("Successfully injected %d characters into focused window.", len(text))
            return True

        except Exception as e:
            log.error("Text injection failed: %s", e)
            return False

        finally:
            if restore_clipboard and old_clipboard:
                # Give target app 120ms to swallow pasteboard event before restoring
                time.sleep(0.12)
                cls.set_clipboard(old_clipboard)
