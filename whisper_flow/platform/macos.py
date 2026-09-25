"""whisper_flow/platform/macos.py — macOS Native Context Detection and Keystroke Injection."""

from __future__ import annotations

import logging
import subprocess
import time
from typing import Optional

from whisper_flow.platform.base import (
    BaseContextProvider,
    BaseTextInjector,
    PlatformAppContext,
    PlatformAppMode,
)

log = logging.getLogger("freeflow.platform.macos")

MODE_MAPPING: dict[str, PlatformAppMode] = {
    # Coding & Development
    "code": PlatformAppMode.CODE,
    "visual studio code": PlatformAppMode.CODE,
    "cursor": PlatformAppMode.CODE,
    "xcode": PlatformAppMode.CODE,
    "pycharm": PlatformAppMode.CODE,
    "sublime text": PlatformAppMode.CODE,
    "terminal": PlatformAppMode.CODE,
    "iterm2": PlatformAppMode.CODE,
    "iterm": PlatformAppMode.CODE,
    "warp": PlatformAppMode.CODE,
    "alacritty": PlatformAppMode.CODE,
    "kitty": PlatformAppMode.CODE,
    # Notes & Knowledge
    "obsidian": PlatformAppMode.NOTES,
    "notion": PlatformAppMode.NOTES,
    "notes": PlatformAppMode.NOTES,
    "apple notes": PlatformAppMode.NOTES,
    "bear": PlatformAppMode.NOTES,
    "craft": PlatformAppMode.NOTES,
    "logseq": PlatformAppMode.NOTES,
    "textedit": PlatformAppMode.NOTES,
    # Chat & Messaging
    "slack": PlatformAppMode.CHAT,
    "discord": PlatformAppMode.CHAT,
    "whatsapp": PlatformAppMode.CHAT,
    "telegram": PlatformAppMode.CHAT,
    "messages": PlatformAppMode.CHAT,
    "microsoft teams": PlatformAppMode.CHAT,
    "signal": PlatformAppMode.CHAT,
    # Email
    "mail": PlatformAppMode.EMAIL,
    "microsoft outlook": PlatformAppMode.EMAIL,
    "superhuman": PlatformAppMode.EMAIL,
    "thunderbird": PlatformAppMode.EMAIL,
}

MODE_INSTRUCTIONS: dict[PlatformAppMode, str] = {
    PlatformAppMode.CODE: (
        "The user is in a code editor or terminal. Format programming terms correctly. "
        "Preserve camelCase, snake_case, variable names, and code syntax. "
        "If a coding prompt or function signature is spoken, format it as clean code or a crisp developer instruction. "
        "Do not invent new code; only structure what the user dictated."
    ),
    PlatformAppMode.NOTES: (
        "The user is in a note-taking application (Obsidian/Notes). "
        "Format spoken items into clean markdown bullet points ('- ') or numbered lists where appropriate. "
        "Use proper capitalization and clean paragraphs."
    ),
    PlatformAppMode.CHAT: (
        "The user is typing a chat message (Slack/WhatsApp). "
        "Keep it conversational, direct, and concise. Remove stiff formalism. "
        "Strip filler words and use natural punctuation."
    ),
    PlatformAppMode.EMAIL: (
        "The user is composing an email. "
        "Ensure professional tone, complete sentences, proper paragraphs, and polite formatting."
    ),
    PlatformAppMode.SEARCH: (
        "The user is searching in a browser. "
        "Provide a crisp, direct search phrase. Do not end with a period."
    ),
    PlatformAppMode.GENERAL: (
        "Clean transcript: remove fillers, apply spoken self-corrections, and format standard punctuation."
    ),
}


class MacOSContextProvider(BaseContextProvider):
    """Inspects frontmost macOS application and window title in <15ms via AppleScript."""

    _SCRIPT = """
    tell application "System Events"
        set fp to first application process whose frontmost is true
        set appName to name of fp
        set bid to ""
        try
            set bid to bundle identifier of fp
        end try
        set winTitle to ""
        try
            if (count of windows of fp) > 0 then
                set winTitle to name of front window of fp
            end if
        end try
        return appName & "|||" & bid & "|||" & winTitle
    end tell
    """

    def get_active_context(self) -> PlatformAppContext:
        try:
            res = subprocess.run(
                ["osascript", "-e", self._SCRIPT],
                capture_output=True,
                text=True,
                timeout=0.6,
            )
            raw = res.stdout.strip()
            if "|||" in raw:
                parts = raw.split("|||")
                app_name = parts[0].strip()
                bundle_id = parts[1].strip() if len(parts) > 1 else ""
                win_title = parts[2].strip() if len(parts) > 2 else ""
            else:
                app_name = raw or "Unknown"
                bundle_id = ""
                win_title = ""
        except Exception as e:
            log.debug("macOS context detector error: %s", e)
            app_name = "Unknown"
            bundle_id = ""
            win_title = ""

        mode = self._classify_mode(app_name, win_title)
        instructions = MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS[PlatformAppMode.GENERAL])

        return PlatformAppContext(
            app_name=app_name,
            bundle_id=bundle_id,
            window_title=win_title,
            mode=mode,
            formatting_instructions=instructions,
        )

    def _classify_mode(self, app_name: str, win_title: str) -> PlatformAppMode:
        app_lower = app_name.lower()
        title_lower = win_title.lower()

        for key, mode in MODE_MAPPING.items():
            if key in app_lower:
                return mode

        if any(browser in app_lower for browser in ("safari", "chrome", "arc", "brave", "firefox")):
            if any(s in title_lower for s in ("new tab", "search", "google", "kagi", "duckduckgo")):
                return PlatformAppMode.SEARCH

        return PlatformAppMode.GENERAL


class MacOSTextInjector(BaseTextInjector):
    """Pastes text via macOS pasteboard (`pbcopy`) and Command+V simulation."""

    def get_clipboard(self) -> str:
        try:
            res = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=0.5)
            return res.stdout
        except Exception:
            return ""

    def set_clipboard(self, text: str) -> bool:
        try:
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            p.communicate(input=text.encode("utf-8"), timeout=0.5)
            return p.returncode == 0
        except Exception as e:
            log.error("Failed to copy to macOS pasteboard: %s", e)
            return False

    def inject(self, text: str, restore_clipboard: bool = True) -> bool:
        if not text:
            return False

        old_clipboard = self.get_clipboard() if restore_clipboard else ""

        try:
            # 1. Place text on pasteboard
            if not self.set_clipboard(text):
                return False

            # 2. Simulate Cmd+V
            script = 'tell application "System Events" to keystroke "v" using {command down}'
            res = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=1.0)
            if res.returncode != 0:
                log.warning("AppleScript keystroke failed: %s", res.stderr)
                return False

            log.info("Successfully injected %d chars into macOS active window.", len(text))
            return True
        except Exception as e:
            log.error("macOS injection failed: %s", e)
            return False
        finally:
            if restore_clipboard and old_clipboard:
                time.sleep(0.12)
                self.set_clipboard(old_clipboard)
