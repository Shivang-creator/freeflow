"""whisper_flow/app_context.py — Frontmost Application & Context Awareness."""

from __future__ import annotations

from whisper_flow.platform import (
    BaseContextProvider,
    PlatformAppContext as AppContext,
    PlatformAppMode as AppMode,
    get_context_provider,
)

# Export ContextDetector using the modular platform provider
class ContextDetector:
    """Detects active application and window context via platform provider."""

    def __init__(self, provider: BaseContextProvider | None = None) -> None:
        self.provider = provider or get_context_provider()

    def get_active_context(self) -> AppContext:
        return self.provider.get_active_context()


__all__ = ["AppMode", "AppContext", "ContextDetector"]
