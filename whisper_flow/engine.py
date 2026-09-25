"""voice/dictation/engine.py — Central OpenWhisper-Style Dictation Orchestrator.

Wires together:
1. AudioRecorder (16kHz float32)
2. MLXTranscriber (Local Apple Silicon Whisper with vocabulary biasing)
3. DictionaryManager (Konkani words, personal names, longest-match-first post-corrections)
4. ContextDetector (macOS frontmost app & window awareness)
5. Cleaner (Rule-based instant cleaner + Local SLM self-correction & formatting)
6. TextInjector (Fast pasteboard + Cmd+V with transparent clipboard restore)
7. DictationHUD (Visual floating overlay & non-blocking sound cues)
"""

from __future__ import annotations

import asyncio
import logging
import re
import threading
import time
from pathlib import Path
from typing import Optional

import numpy as np

from whisper_flow.app_context import AppContext, ContextDetector
from whisper_flow.cleaner import RuleCleaner, SLMCleaner
from whisper_flow.dictionary import DictionaryManager
from whisper_flow.hotkey import HotkeyMonitor
from whisper_flow.hud import DictationHUD
from whisper_flow.injector import TextInjector
from whisper_flow.recorder import AudioRecorder
from whisper_flow.transcriber import MLXTranscriber

log = logging.getLogger("dictation.engine")


class DictationEngine:
    """Universal macOS Speech-to-Text Dictation Engine."""

    def __init__(
        self,
        whisper_model: str = "mlx-community/whisper-large-v3-turbo-4bit",
        slm_model: str = "qwen2.5:1.5b",
        enable_slm: bool = True,
    ) -> None:
        log.info("Initializing Universal Dictation Engine...")
        self.recorder = AudioRecorder(sample_rate=16000)
        self.transcriber = MLXTranscriber(model_repo=whisper_model)
        self.dictionary_mgr = DictionaryManager()
        self.context_detector = ContextDetector()
        self.rule_cleaner = RuleCleaner()
        self.slm_cleaner = SLMCleaner(model_name=slm_model)
        self.enable_slm = enable_slm
        self.hud = DictationHUD()
        self._processing_lock = threading.Lock()
        threading.Thread(target=self._prewarm, daemon=True).start()

    def _prewarm(self) -> None:
        """Pre-warms MLX Whisper in memory so the first dictation is instant."""
        try:
            log.info("Pre-warming MLX Whisper in memory...")
            dummy = np.zeros(16000, dtype=np.float32)
            self.transcriber.transcribe(dummy)
            log.info("✅ MLX Whisper pre-warmed and ready.")
        except Exception as e:
            log.debug("Pre-warm degraded: %s", e)

    def start_recording(self, is_toggle: bool = False) -> None:
        """Called immediately when push-to-talk key is pressed or toggle begins."""
        try:
            self.hud.on_recording_start()
            self.recorder.start(
                is_toggle=is_toggle,
                on_silence_callback=self._on_silence_cutoff,
            )
        except Exception as e:
            log.error("Failed to start dictation recording: %s", e)
            self.hud.on_cancel()

    def upgrade_to_toggle(self) -> None:
        """Upgrades active recording from push-to-talk to hands-free toggle with silence detection."""
        log.info("Upgrading active recording to hands-free toggle mode with VAD.")
        self.recorder.is_toggle_mode = True
        self.recorder.on_silence_callback = self._on_silence_cutoff

    def _on_silence_cutoff(self) -> None:
        """Invoked when user stops speaking in hands-free toggle mode for >2.5s."""
        log.info("Silence cutoff triggered in engine (>2.5s pause). Finalizing dictation.")
        if hasattr(self, "hotkey_monitor") and self.hotkey_monitor:
            self.hotkey_monitor.reset_toggle()
        self.stop_recording_and_process()

    def stop_recording_and_process(self) -> None:
        """Called when key is released or toggle stops. Runs full transcription pipeline."""
        threading.Thread(target=self._process_pipeline, daemon=True).start()

    def _process_pipeline(self) -> None:
        if not self._processing_lock.acquire(blocking=False):
            log.warning("Pipeline already running; skipping concurrent execution.")
            return

        t_total_0 = time.time()
        try:
            # 1. Stop audio capture
            audio_data = self.recorder.stop()
            duration = len(audio_data) / 16000.0

            # Guard against accidental micro-taps (<0.25s or near-silent)
            if duration < 0.25:
                log.info("Audio duration too short (%.2fs); ignoring.", duration)
                self.hud.on_cancel()
                return

            self.hud.on_transcribing()

            # 2. Inspect active macOS application context
            context = self.context_detector.get_active_context()
            log.info("Active Context: App='%s', Title='%s', Mode='%s'", context.app_name, context.window_title, context.mode.value)

            # 3. Transcribe via local Apple Silicon Whisper
            initial_prompt = self.dictionary_mgr.get_initial_prompt()
            raw_transcript = self.transcriber.transcribe(audio_data, initial_prompt=initial_prompt)

            if not raw_transcript.strip():
                log.info("Transcribed text is empty.")
                self.hud.on_cancel()
                return

            log.info("Raw ASR Transcript: '%s'", raw_transcript)

            # 4. Apply deterministic dictionary corrections (longest match first)
            corrected_text, applied_rules = self.dictionary_mgr.apply_corrections(raw_transcript)
            if applied_rules:
                log.info("Applied %d dictionary corrections: %s", len(applied_rules), applied_rules)

            # 5. Text Cleanup, Formatting & Mid-Sentence Correction
            self.hud.on_formatting(context.app_name)
            final_text = self._clean_and_format(corrected_text, context)
            log.info("Final Cleaned Text (%d chars): '%s'", len(final_text), final_text)

            # 6. Inject into focused field
            success = TextInjector.inject(final_text, restore_clipboard=True)
            if success:
                self.hud.on_complete(preview_text=final_text)
            else:
                self.hud.on_cancel()

            log.info("Dictation pipeline finished in %.2fs total.", time.time() - t_total_0)

        except Exception as e:
            log.error("Error in dictation pipeline: %s", e, exc_info=True)
            self.hud.on_cancel()
        finally:
            self._processing_lock.release()

    def _clean_and_format(self, text: str, context: AppContext) -> str:
        """Runs two-tier cleanup: fast rule cleanup, followed by SLM if enabled."""
        # Tier 1: Deterministic rule cleaner
        rule_output = self.rule_cleaner.clean(text, context)

        if not self.enable_slm:
            return rule_output

        # For Hindi Devanagari text, bypass SLM to ensure 100% authentic Hindi output without translation
        if re.search(r"[\u0900-\u097F]", text):
            log.info("Devanagari text detected; returning rule cleaner output to preserve native Hindi.")
            return rule_output

        # Tier 2: Context-aware SLM rewriter
        # Only invoke SLM if there's self-correction markers or in coding/notes modes
        needs_slm = (
            any(w in text.lower() for w in ("wait", "no wait", "actually", "scratch that", "make it"))
            or context.mode.value in ("code", "notes")
            or len(text.split()) > 7
        )

        if not needs_slm:
            return rule_output

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            slm_output = loop.run_until_complete(self.slm_cleaner.clean(text, context))
            loop.close()
            return slm_output or rule_output
        except Exception as e:
            log.warning("SLM cleanup failed (%s). Using rule output.", e)
            return rule_output
