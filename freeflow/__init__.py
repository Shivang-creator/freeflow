"""freeflow — Universal 100% On-Device Voice Dictation for Apple Silicon."""

from freeflow.app import run_menu_bar_app
from freeflow.app_context import AppContext, ContextDetector
from freeflow.cleaner import RuleCleaner, SLMCleaner
from freeflow.config import AppConfig, ConfigManager
from freeflow.constants import APP_NAME, APP_SUBTITLE, APP_VERSION, HOTKEYS, MODELS
from freeflow.dictionary import DictionaryManager
from freeflow.engine import DictationEngine
from freeflow.history import HistoryEntry, HistoryManager
from freeflow.hotkey import HotkeyMonitor
from freeflow.hud import DictationHUD
from freeflow.injector import TextInjector
from freeflow.recorder import AudioRecorder
from freeflow.transcriber import MLXTranscriber

__all__ = [
    "APP_NAME",
    "APP_VERSION",
    "APP_SUBTITLE",
    "MODELS",
    "HOTKEYS",
    "AppConfig",
    "ConfigManager",
    "HistoryEntry",
    "HistoryManager",
    "AppContext",
    "ContextDetector",
    "RuleCleaner",
    "SLMCleaner",
    "DictionaryManager",
    "DictationEngine",
    "HotkeyMonitor",
    "DictationHUD",
    "TextInjector",
    "AudioRecorder",
    "MLXTranscriber",
    "run_menu_bar_app",
]
