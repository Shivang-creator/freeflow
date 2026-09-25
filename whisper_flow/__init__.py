"""whisper_flow — Universal 100% On-Device Voice Dictation for Apple Silicon."""

from whisper_flow.app import run_menu_bar_app
from whisper_flow.app_context import AppContext, ContextDetector
from whisper_flow.cleaner import RuleCleaner, SLMCleaner
from whisper_flow.config import AppConfig, ConfigManager
from whisper_flow.constants import APP_NAME, APP_SUBTITLE, APP_VERSION, HOTKEYS, MODELS
from whisper_flow.dictionary import DictionaryManager
from whisper_flow.engine import DictationEngine
from whisper_flow.history import HistoryEntry, HistoryManager
from whisper_flow.hotkey import HotkeyMonitor
from whisper_flow.hud import DictationHUD
from whisper_flow.injector import TextInjector
from whisper_flow.recorder import AudioRecorder
from whisper_flow.transcriber import MLXTranscriber

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
