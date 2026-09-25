"""whisper_flow/platform/windows.py — Windows Text Injection and Context Provider Stubs."""

from __future__ import annotations

import logging
from whisper_flow.platform.base import (
    BaseContextProvider,
    BaseTextInjector,
    PlatformAppContext,
    PlatformAppMode,
)

log = logging.getLogger("freeflow.platform.windows")


class WindowsContextProvider(BaseContextProvider):
    """Windows context provider stub."""

    def get_active_context(self) -> PlatformAppContext:
        return PlatformAppContext(
            app_name="WindowsApp",
            bundle_id="",
            window_title="WindowsApp",
            mode=PlatformAppMode.GENERAL,
            formatting_instructions="Standard dictation text cleanup.",
        )


class WindowsTextInjector(BaseTextInjector):
    """Windows text injector stub."""

    def get_clipboard(self) -> str:
        return ""

    def set_clipboard(self, text: str) -> bool:
        return False

    def inject(self, text: str, restore_clipboard: bool = True) -> bool:
        return False
