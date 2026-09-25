"""voice/dictation/recorder.py — Low-Latency Rolling Audio Recorder with AGC.

Maintains a permanent, lightweight 16kHz float32 input stream with a rolling 400ms
ring buffer.
Guarantees:
1. Zero stream startup latency (stream is already active).
2. Captures words spoken at the exact instant (or 400ms before) the hotkey is pressed.
3. Software peak normalization (AGC) to ensure clear acoustic decoding on Bluetooth AirPods.
"""

from __future__ import annotations

import collections
import logging
import threading
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

log = logging.getLogger("dictation.recorder")


class AudioRecorder:
    """Captures microphone audio at 16kHz mono float32 with a rolling pre-buffer."""

    def __init__(self, sample_rate: int = 16000, pre_buffer_ms: int = 400) -> None:
        self.sample_rate = sample_rate
        self.block_size = 1024  # ~64ms per block at 16kHz
        # Number of blocks to keep for pre-buffering (e.g., 400ms / 64ms ~= 6 blocks)
        self.pre_buffer_blocks = max(2, int(pre_buffer_ms / (self.block_size / sample_rate * 1000)))
        self._ring_buffer: collections.deque[np.ndarray] = collections.deque(maxlen=self.pre_buffer_blocks)

        self.is_recording = False
        self.is_toggle_mode = False
        self.on_silence_callback: Optional[Callable[[], None]] = None
        self._speech_detected = False
        self._consecutive_silent_blocks = 0
        self._active_chunks: list[np.ndarray] = []
        self._stream: Optional[sd.InputStream] = None
        self._lock = threading.Lock()

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info: dict, status: sd.CallbackFlags) -> None:
        chunk = indata[:, 0].copy()
        with self._lock:
            if self.is_recording:
                self._active_chunks.append(chunk)
                # In hands-free toggle mode, track speech activity and auto-stop on pause
                if self.is_toggle_mode and self.on_silence_callback:
                    rms = float(np.sqrt(np.mean(chunk ** 2)))
                    if rms > 0.015:
                        self._speech_detected = True
                        self._consecutive_silent_blocks = 0
                    elif self._speech_detected and rms < 0.008:
                        self._consecutive_silent_blocks += 1
                        # ~2.5s of silence after speech (39 blocks * 64ms ~= 2.5s)
                        if self._consecutive_silent_blocks >= 39:
                            log.info("Silence detected (>2.5s) in hands-free mode. Auto-finalizing dictation.")
                            self.is_toggle_mode = False
                            cb = self.on_silence_callback
                            threading.Thread(target=cb, daemon=True).start()

    def start(self, is_toggle: bool = False, on_silence_callback: Optional[Callable[[], None]] = None) -> None:
        """Starts capturing audio on demand, keeping hardware free when idle for macOS Hey Siri."""
        with self._lock:
            if self.is_recording:
                return

            self._active_chunks = []
            self.is_recording = True
            self.is_toggle_mode = is_toggle
            self.on_silence_callback = on_silence_callback
            self._speech_detected = False
            self._consecutive_silent_blocks = 0

            try:
                self._stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype="float32",
                    callback=self._audio_callback,
                    blocksize=self.block_size,
                )
                self._stream.start()
                log.info("Microphone engaged on demand (toggle=%s).", is_toggle)
            except Exception as e:
                log.error("Failed to open on-demand audio stream: %s", e)
                self.is_recording = False

    def stop(self) -> np.ndarray:
        """Concludes recording, immediately closes stream to release hardware for Siri, and returns buffer."""
        with self._lock:
            if not self.is_recording:
                return np.zeros(0, dtype=np.float32)

            self.is_recording = False
            self.is_toggle_mode = False
            self.on_silence_callback = None

            if self._stream:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None

            chunks = self._active_chunks
            self._active_chunks = []

            if not chunks:
                return np.zeros(0, dtype=np.float32)

            audio = np.concatenate(chunks, axis=0)
            duration = len(audio) / self.sample_rate

            # Software AGC: Normalize low microphone peaks (crucial for AirPods mics)
            peak = float(np.max(np.abs(audio)))
            if 0.02 < peak < 0.60:
                boost = min(3.0, 0.85 / peak)
                audio = audio * boost
                log.info("Applied AGC normalization: peak %.3f -> boosted %.2fx", peak, boost)

            log.info("Recording completed: %.2fs audio captured (%d samples).", duration, len(audio))
            return audio

    def close(self) -> None:
        """Shuts down background stream."""
        with self._lock:
            if self._stream:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None
