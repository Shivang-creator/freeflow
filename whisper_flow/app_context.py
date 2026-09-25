"""voice/dictation/app_context.py — Frontmost macOS Application & Context Awareness.

Detects the active macOS application and window title in <15ms using AppleScript/PyObjC.
Maps the environment into targeted formatting personas:
- 'code': IDEs & Terminals -> preserve camelCase/snake_case, syntax formatting, code blocks
- 'notes': Obsidian / Notion -> structured markdown, bullet points, headers
- 'chat': Slack / WhatsApp -> direct, conversational, natural punctuation
- 'email': Mail / Outlook -> polite, properly paragraphed, formal punctuation
- 'search': Safari / Chrome search bars -> concise query without trailing periods
- 'general': Default
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Optional

log = logging.getLogger("dictation.context")


class AppMode(str, Enum):
    CODE = "code"
    NOTES = "notes"
    CHAT = "chat"
    EMAIL = "email"
    SEARCH = "search"
    GENERAL = "general"


@dataclass
class AppContext:
    app_name: str
    bundle_id: str
    window_title: str
    mode: AppMode
    formatting_instructions: str


# App name mapping to mode
MODE_MAPPING: dict[str, AppMode] = {
    # Coding & Development
    "code": AppMode.CODE,
    "visual studio code": AppMode.CODE,
    "cursor": AppMode.CODE,
    "xcode": AppMode.CODE,
    "pycharm": AppMode.CODE,
    "sublime text": AppMode.CODE,
    "terminal": AppMode.CODE,
    "iterm2": AppMode.CODE,
    "iterm": AppMode.CODE,
    "warp": AppMode.CODE,
    "alacritty": AppMode.CODE,
    "kitty": AppMode.CODE,
    # Notes & Knowledge
    "obsidian": AppMode.NOTES,
    "notion": AppMode.NOTES,
    "notes": AppMode.NOTES,
    "apple notes": AppMode.NOTES,
    "bear": AppMode.NOTES,
    "craft": AppMode.NOTES,
    "logseq": AppMode.NOTES,
    "textedit": AppMode.NOTES,
    # Chat & Messaging
    "slack": AppMode.CHAT,
    "discord": AppMode.CHAT,
    "whatsapp": AppMode.CHAT,
    "telegram": AppMode.CHAT,
    "messages": AppMode.CHAT,
    "microsoft teams": AppMode.CHAT,
    "signal": AppMode.CHAT,
    # Email
    "mail": AppMode.EMAIL,
    "microsoft outlook": AppMode.EMAIL,
    "superhuman": AppMode.EMAIL,
    "thunderbird": AppMode.EMAIL,
}

MODE_INSTRUCTIONS: dict[AppMode, str] = {
    AppMode.CODE: (
        "The user is in a code editor or terminal. Format programming terms correctly. "
        "Preserve camelCase, snake_case, variable names, and code syntax. "
        "If a coding prompt or function signature is spoken, format it as clean code or a crisp developer instruction. "
        "Do not invent new code; only structure what the user dictated."
    ),
    AppMode.NOTES: (
        "The user is in a note-taking application (Obsidian/Notes). "
        "Format spoken items into clean markdown bullet points ('- ') or numbered lists where appropriate. "
        "Use proper capitalization and clean paragraphs."
    ),
    AppMode.CHAT: (
        "The user is typing a chat message (Slack/WhatsApp). "
        "Keep it conversational, direct, and concise. Remove stiff formalism. "
        "Strip filler words and use natural punctuation."
    ),
    AppMode.EMAIL: (
        "The user is composing an email. "
        "Ensure professional tone, complete sentences, proper paragraphs, and polite formatting."
    ),
    AppMode.SEARCH: (
        "The user is searching in a browser. "
        "Provide a crisp, direct search phrase. Do not end with a period."
    ),
    AppMode.GENERAL: (
        "Clean transcript: remove fillers, apply spoken self-corrections, and format standard punctuation."
    ),
}


class ContextDetector:
    """Fast inspector for active macOS frontmost window and application."""

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

    def get_active_context(self) -> AppContext:
        """Inspects frontmost app in macOS via AppleScript."""
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
            log.debug("Active context query error: %s", e)
            app_name = "Unknown"
            bundle_id = ""
            win_title = ""

        mode = self._classify_mode(app_name, win_title)
        instructions = MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS[AppMode.GENERAL])

        return AppContext(
            app_name=app_name,
            bundle_id=bundle_id,
            window_title=win_title,
            mode=mode,
            formatting_instructions=instructions,
        )

    def _classify_mode(self, app_name: str, win_title: str) -> AppMode:
        app_lower = app_name.lower()
        title_lower = win_title.lower()

        # Check explicit app mapping
        for key, mode in MODE_MAPPING.items():
            if key in app_lower:
                return mode

        # Browser search heuristics
        if any(browser in app_lower for browser in ("safari", "chrome", "arc", "brave", "firefox")):
            if any(s in title_lower for s in ("new tab", "search", "google", "kagi", "duckduckgo")):
                return AppMode.SEARCH

        return AppMode.GENERAL
