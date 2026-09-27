"""freeflow/platform/base.py — Abstract Base Interfaces for Cross-Platform Support."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PlatformAppMode(str, Enum):
    CODE = "code"
    NOTES = "notes"
    CHAT = "chat"
    EMAIL = "email"
    SEARCH = "search"
    GENERAL = "general"


@dataclass
class PlatformAppContext:
    app_name: str
    bundle_id: str
    window_title: str
    mode: PlatformAppMode
    formatting_instructions: str


class BaseContextProvider(ABC):
    """Abstract interface for inspecting active foreground application context."""

    @abstractmethod
    def get_active_context(self) -> PlatformAppContext:
        """Returns the current frontmost application and window context."""
        pass


class BaseTextInjector(ABC):
    """Abstract interface for clipboard manipulation and simulated text injection."""

    @abstractmethod
    def get_clipboard(self) -> str:
        """Reads text from system clipboard."""
        pass

    @abstractmethod
    def set_clipboard(self, text: str) -> bool:
        """Sets text onto system clipboard."""
        pass

    @abstractmethod
    def inject(self, text: str, restore_clipboard: bool = True) -> bool:
        """Injects text into focused window and optionally restores prior clipboard."""
        pass
