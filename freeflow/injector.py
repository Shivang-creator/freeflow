"""freeflow/injector.py — Universal Text Injection into Focused Application."""

from __future__ import annotations

from typing import Optional

from freeflow.platform import BaseTextInjector, get_text_injector


class TextInjector:
    """Injects text into whatever application currently has keyboard focus."""

    _injector: BaseTextInjector = get_text_injector()

    @classmethod
    def get_clipboard(cls) -> str:
        return cls._injector.get_clipboard()

    @classmethod
    def set_clipboard(cls, text: str) -> bool:
        return cls._injector.set_clipboard(text)

    @classmethod
    def inject(cls, text: str, restore_clipboard: bool = True) -> bool:
        return cls._injector.inject(text, restore_clipboard=restore_clipboard)


__all__ = ["TextInjector"]
