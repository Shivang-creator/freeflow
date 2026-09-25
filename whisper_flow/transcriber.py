"""voice/dictation/transcriber.py — On-Device Apple Silicon Whisper Transcriber.

Uses `mlx_whisper` to execute transcription locally via Apple Silicon unified memory
and Metal acceleration.
Supports acoustic vocabulary biasing via `initial_prompt`.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Optional, Union

import numpy as np

log = logging.getLogger("dictation.transcriber")

# Default models
# Primary: whisper-large-v3-turbo 4-bit (~464MB, SOTA accuracy, ~250ms)
# Fallback: whisper-small 4-bit (~197MB, instant load)
DEFAULT_MODEL = "mlx-community/whisper-large-v3-turbo-4bit"
FALLBACK_MODEL = "mlx-community/whisper-small-mlx-4bit"


class MLXTranscriber:
    """Local Speech-to-Text Transcriber powered by Apple MLX."""

    def __init__(self, model_repo: str = DEFAULT_MODEL) -> None:
        self.model_repo = model_repo
        self._warmed = False

    def transcribe(
        self,
        audio: Union[np.ndarray, str, Path],
        initial_prompt: Optional[str] = None,
        language: Optional[str] = None,
    ) -> str:
        """Transcribes 16kHz audio array or file into text.
        
        Args:
            audio: 1D numpy array of float32 samples at 16000Hz, or file path.
            initial_prompt: Custom vocabulary prompt to bias acoustic decoding.
            language: Target language code (e.g. "en", "hi", "mr"). Defaults to None (auto-detect).
            
        Returns:
            Raw transcribed text in the spoken language.
        """
        import mlx_whisper

        t0 = time.time()
        log.info("Starting local MLX transcription with model %s (lang=%s)...", self.model_repo, language or "auto")

        decode_kwargs = {
            "temperature": 0.0,  # Greedy decoding for maximum speed and deterministic output
        }
        if language:
            decode_kwargs["language"] = language

        # Transcribe with primary model, fall back gracefully if download is still running
        try:
            result = mlx_whisper.transcribe(
                audio,
                path_or_hf_repo=self.model_repo,
                initial_prompt=initial_prompt or "",
                **decode_kwargs,
            )
        except Exception as e:
            log.warning("Primary model %s failed (%s). Retrying with fallback %s...", self.model_repo, e, FALLBACK_MODEL)
            result = mlx_whisper.transcribe(
                audio,
                path_or_hf_repo=FALLBACK_MODEL,
                initial_prompt=initial_prompt or "",
                **decode_kwargs,
            )

        elapsed = time.time() - t0
        text = result.get("text", "").strip()
        log.info("MLX transcription completed in %.2fs: '%s'", elapsed, text)
        return text
