"""freeflow/platform/linux.py — Linux Text Injection and Window Detection (X11 / Wayland)."""

from __future__ import annotations

import logging
import shutil
import subprocess
from freeflow.platform.base import (
    BaseContextProvider,
    BaseTextInjector,
    PlatformAppContext,
    PlatformAppMode,
)

log = logging.getLogger("freeflow.platform.linux")


class LinuxContextProvider(BaseContextProvider):
    """Fallback Linux context provider via xdotool or standard environment."""

    def get_active_context(self) -> PlatformAppContext:
        app_name = "LinuxApp"
        if shutil.which("xdotool"):
            try:
                out = subprocess.check_output(["xdotool", "getwindowfocus", "getwindowname"], text=True).strip()
                app_name = out or "LinuxApp"
            except Exception:
                pass

        return PlatformAppContext(
            app_name=app_name,
            bundle_id="",
            window_title=app_name,
            mode=PlatformAppMode.GENERAL,
            formatting_instructions="Standard dictation text cleanup.",
        )


class LinuxTextInjector(BaseTextInjector):
    """Linux text injector using wl-clipboard (Wayland) or xclip/xdotool (X11)."""

    def get_clipboard(self) -> str:
        for cmd in (["wl-paste"], ["xclip", "-selection", "clipboard", "-o"]):
            if shutil.which(cmd[0]):
                try:
                    return subprocess.check_output(cmd, text=True, timeout=0.5)
                except Exception:
                    pass
        return ""

    def set_clipboard(self, text: str) -> bool:
        for cmd in (["wl-copy"], ["xclip", "-selection", "clipboard"]):
            if shutil.which(cmd[0]):
                try:
                    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                    p.communicate(input=text.encode("utf-8"), timeout=0.5)
                    return p.returncode == 0
                except Exception:
                    pass
        return False

    def inject(self, text: str, restore_clipboard: bool = True) -> bool:
        if not text:
            return False
        old = self.get_clipboard() if restore_clipboard else ""
        if not self.set_clipboard(text):
            return False

        # Simulate Ctrl+Shift+V or Ctrl+V via xdotool if present
        if shutil.which("xdotool"):
            try:
                subprocess.run(["xdotool", "key", "--clearmodifiers", "ctrl+v"], timeout=1.0)
                return True
            except Exception as e:
                log.warning("xdotool keystroke failed: %s", e)
        return True
