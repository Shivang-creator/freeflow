"""freeflow/platform/__init__.py — OS Auto-detection & Factory for Platform Providers."""

from __future__ import annotations

import sys
from freeflow.platform.base import (
    BaseContextProvider,
    BaseTextInjector,
    PlatformAppContext,
    PlatformAppMode,
)

if sys.platform == "darwin":
    from freeflow.platform.macos import MacOSContextProvider as DefaultContextProvider
    from freeflow.platform.macos import MacOSTextInjector as DefaultTextInjector
elif sys.platform.startswith("linux"):
    from freeflow.platform.linux import LinuxContextProvider as DefaultContextProvider
    from freeflow.platform.linux import LinuxTextInjector as DefaultTextInjector
elif sys.platform in ("win32", "cygwin"):
    from freeflow.platform.windows import WindowsContextProvider as DefaultContextProvider
    from freeflow.platform.windows import WindowsTextInjector as DefaultTextInjector
else:
    from freeflow.platform.macos import MacOSContextProvider as DefaultContextProvider
    from freeflow.platform.macos import MacOSTextInjector as DefaultTextInjector


def get_context_provider() -> BaseContextProvider:
    return DefaultContextProvider()


def get_text_injector() -> BaseTextInjector:
    return DefaultTextInjector()


__all__ = [
    "BaseContextProvider",
    "BaseTextInjector",
    "PlatformAppContext",
    "PlatformAppMode",
    "get_context_provider",
    "get_text_injector",
]
