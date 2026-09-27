"""freeflow/engine.py — Central FreeFlow Dictation Orchestrator.

Wires together:
1. AudioRecorder (16kHz float32 + 400ms ring buffer + AGC + VAD silence auto-cutoff)
2. MLXTranscriber (Local Apple Silicon Whisper with dynamic model switching)
3. DictionaryManager (Acoustic biasing + longest-match-first post-corrections)
4. ContextDetector (macOS/cross-platform frontmost app & window awareness)
5. Cleaner (Rule-based instant cleaner + Local SLM self-correction & formatting)
6. TextInjector (Fast pasteboard + Cmd+V with transparent clipboard restore)
7. HistoryManager (Persistent clipboard history with 1-click re-copying)
8. DictationHUD (Visual floating pill overlay & audio cues)
"""

from __future__ import annotations

import asyncio
import logging
import re
import threading
import time
from typing import Callable, Optional

import numpy as np

from freeflow.app_context import AppContext, ContextDetector
from freeflow.cleaner import RuleCleaner, SLMCleaner
from freeflow.config import ConfigManager
from freeflow.dictionary import DictionaryManager
from freeflow.history import HistoryManager
from freeflow.hud import DictationHUD
from freeflow.injector import TextInjector
from freeflow.recorder import AudioRecorder
from freeflow.transcriber import MLXTranscriber

log = logging.getLogger("freeflow.engine")


class DictationEngine:
    """Universal 100% On-Device Dictation Engine."""

    def __init__(
        self,
        config_mgr: Optional[ConfigManager] = None,
        history_mgr: Optional[HistoryManager] = None,
        dict_mgr: Optional[DictionaryManager] = None,
        whisper_model: Optional[str] = None,
        slm_model: Optional[str] = None,
        enable_slm: Optional[bool] = None,
        status_callback: Optional[Callable[[str, dict], None]] = None,
        prewarm: bool = True,
    ) -> None:
        log.info("Initializing FreeFlow Dictation Engine...")
        self.config_mgr = config_mgr or ConfigManager()
        self.config = self.config_mgr.config
        self.history_mgr = history_mgr or HistoryManager()
        self.dictionary_mgr = dict_mgr or DictionaryManager()
        self.context_detector = ContextDetector()
        self.rule_cleaner = RuleCleaner()

        # Config overrides
        active_model = whisper_model or self.config.whisper_model
        active_slm_model = slm_model or self.config.slm_model
        self.enable_slm = enable_slm if enable_slm is not None else self.config.enable_slm

        self.recorder = AudioRecorder(sample_rate=16000)
        self.transcriber = MLXTranscriber(model_repo=active_model)
        self.slm_cleaner = SLMCleaner(model_name=active_slm_model)
        self.hud = DictationHUD(
            enable_sound=self.config.enable_sound,
            enable_hud=self.config.enable_hud,
        )

        self.status_callback = status_callback
        self.current_state = "idle"
        self._processing_lock = threading.Lock()
        self.hotkey_monitor = None

        if prewarm:
            threading.Thread(target=self._prewarm, daemon=True).start()

    def set_status(self, state: str, **kwargs: str) -> None:
        self.current_state = state
        if self.status_callback:
            try:
                self.status_callback(state, kwargs)
            except Exception as e:
                log.debug("Status callback error: %s", e)

    def _prewarm(self) -> None:
        """Pre-warms MLX Whisper in memory so the first dictation is instant."""
        self.transcriber.prewarm()

    def switch_model(self, model_repo: str) -> None:
        """Switches the active MLX Whisper model and prewarms it."""
        log.info("Switching engine model to: %s", model_repo)
        self.transcriber.set_model(model_repo)
        self.config_mgr.update(whisper_model=model_repo)
        threading.Thread(target=self._prewarm, daemon=True).start()

    def start_recording(self, is_toggle: bool = False) -> None:
        """Called immediately when push-to-talk key is pressed or toggle begins."""
        try:
            self.set_status("recording", mode="toggle" if is_toggle else "hold")
            self.hud.on_recording_start()
            self.recorder.start(
                is_toggle=is_toggle,
                on_silence_callback=self._on_silence_cutoff,
            )
        except Exception as e:
            log.error("Failed to start dictation recording: %s", e)
            self.set_status("idle")
            self.hud.on_cancel()

    def upgrade_to_toggle(self) -> None:
        """Upgrades active recording from push-to-talk to hands-free toggle with silence detection."""
        log.info("Upgrading active recording to hands-free toggle mode with VAD.")
        self.set_status("recording", mode="toggle")
        self.recorder.is_toggle_mode = True
        self.recorder.on_silence_callback = self._on_silence_cutoff

    def _on_silence_cutoff(self) -> None:
        """Invoked when user stops speaking in hands-free toggle mode for >2.5s."""
        log.info("Silence cutoff triggered in engine (>%.1fs pause). Finalizing dictation.", self.config.vad_pause_seconds)
        if self.hotkey_monitor:
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

            # Guard against accidental micro-taps (<0.25s)
            if duration < 0.25:
                log.info("Audio duration too short (%.2fs); ignoring.", duration)
                self.hud.on_cancel()
                self.set_status("idle")
                return

            self.set_status("transcribing", duration=f"{duration:.1f}s")
            self.hud.on_transcribing()

            # 2. Inspect active macOS application context
            context = self.context_detector.get_active_context()
            log.info("Active Context: App='%s', Mode='%s'", context.app_name, context.mode.value)

            # 3. Transcribe via local Apple Silicon Whisper
            initial_prompt = self.dictionary_mgr.get_initial_prompt(
                max_words=self.config.custom_vocab_prompt_limit
            )
            raw_transcript = self.transcriber.transcribe(audio_data, initial_prompt=initial_prompt)

            if not raw_transcript.strip():
                log.info("Transcribed text is empty.")
                self.hud.on_cancel()
                self.set_status("idle")
                return

            log.info("Raw ASR Transcript: '%s'", raw_transcript)

            # 4. Apply deterministic dictionary corrections (longest match first)
            corrected_text, applied_rules = self.dictionary_mgr.apply_corrections(raw_transcript)
            if applied_rules:
                log.info("Applied %d dictionary corrections: %s", len(applied_rules), applied_rules)

            # 5. Text Cleanup, Formatting & Mid-Sentence Correction
            self.set_status("formatting", app=context.app_name)
            self.hud.on_formatting(context.app_name)
            final_text = self._clean_and_format(corrected_text, context)
            log.info("Final Cleaned Text (%d chars): '%s'", len(final_text), final_text)

            # 6. Inject into focused field
            success = TextInjector.inject(final_text, restore_clipboard=self.config.restore_clipboard)
            if success:
                self.hud.on_complete(preview_text=final_text)
                self.set_status("done", preview=final_text[:40])
                # Save to persistent clipboard history
                self.history_mgr.add_entry(
                    text=final_text,
                    raw_text=raw_transcript,
                    app_name=context.app_name,
                    mode=context.mode.value,
                    duration_s=duration,
                    model_name=self.transcriber.model_repo.split("/")[-1],
                )
            else:
                self.hud.on_cancel()
                self.set_status("idle")

            log.info("Dictation pipeline finished in %.2fs total.", time.time() - t_total_0)

        except Exception as e:
            log.error("Error in dictation pipeline: %s", e, exc_info=True)
            self.hud.on_cancel()
            self.set_status("idle")
        finally:
            time.sleep(0.3)
            self.set_status("idle")
            self._processing_lock.release()

    def _clean_and_format(self, text: str, context: AppContext) -> str:
        """Runs two-tier cleanup: fast rule cleanup, followed by SLM if enabled."""
        rule_output = self.rule_cleaner.clean(text, context)

        if not self.enable_slm:
            return rule_output

        # For Hindi Devanagari text, bypass SLM to ensure 100% authentic Hindi output without translation
        if re.search(r"[\u0900-\u097F]", text):
            log.info("Devanagari text detected; returning rule cleaner output to preserve native Hindi.")
            return rule_output

        # Only invoke SLM if there's self-correction markers or in coding/notes modes or longer phrases
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
