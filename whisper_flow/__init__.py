"""voice/dictation — System-Wide Local Speech-to-Text for macOS."""

from whisper_flow.app_context import AppContext, ContextDetector
from whisper_flow.cleaner import RuleCleaner, SLMCleaner
from whisper_flow.dictionary import DictionaryManager
from whisper_flow.engine import DictationEngine
from whisper_flow.hotkey import HotkeyMonitor
from whisper_flow.injector import TextInjector
from whisper_flow.recorder import AudioRecorder
from whisper_flow.transcriber import MLXTranscriber

__all__ = [
    "AppContext",
    "ContextDetector",
    "RuleCleaner",
    "SLMCleaner",
    "DictionaryManager",
    "DictationEngine",
    "HotkeyMonitor",
    "TextInjector",
    "AudioRecorder",
    "MLXTranscriber",
]
