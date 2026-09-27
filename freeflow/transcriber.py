"""freeflow/transcriber.py — On-Device Apple Silicon Whisper Transcriber & Model Manager.

Uses `mlx_whisper` to execute transcription locally via Apple Silicon unified memory
and Metal acceleration.
Supports:
- Dynamic 1-click model switching (Turbo, Low RAM, Ultra-Lite)
- Automated model downloading via huggingface_hub
- Pre-warming to ensure sub-350ms first-run latency
- Acoustic vocabulary biasing via `initial_prompt`.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Callable, Optional, Union

import numpy as np

from freeflow.constants import DEFAULT_MODEL_REPO, MODELS

log = logging.getLogger("freeflow.transcriber")


def is_model_cached(model_repo: str) -> bool:
    """Checks whether the requested model is already downloaded in HuggingFace cache."""
    try:
        from huggingface_hub import try_to_load_from_cache
        res = try_to_load_from_cache(model_repo, "config.json")
        return res is not None and isinstance(res, str)
    except Exception as e:
        log.debug("Error checking cache for %s: %s", model_repo, e)
        # Fallback check of directory existence
        safe_name = "models--" + model_repo.replace("/", "--")
        cache_dir = Path.home() / ".cache" / "huggingface" / "hub" / safe_name
        return cache_dir.exists() and any(cache_dir.iterdir())


def download_model(
    model_repo: str,
    progress_callback: Optional[Callable[[str, float], None]] = None,
) -> bool:
    """Downloads a model snapshot from HuggingFace with status updates."""
    try:
        from huggingface_hub import snapshot_download

        log.info("Starting automated download for model repo: %s", model_repo)
        if progress_callback:
            progress_callback(model_repo, 0.1)

        snapshot_download(
            repo_id=model_repo,
            resume_download=True,
            local_files_only=False,
        )

        if progress_callback:
            progress_callback(model_repo, 1.0)
        log.info("✅ Model download complete: %s", model_repo)
        return True
    except Exception as e:
        log.error("Failed to download model %s: %s", model_repo, e)
        return False


class MLXTranscriber:
    """Local Speech-to-Text Transcriber powered by Apple MLX."""

    def __init__(self, model_repo: str = DEFAULT_MODEL_REPO) -> None:
        self.model_repo = model_repo
        self.is_warmed = False
        self._lock = threading.Lock()

    def set_model(self, model_repo: str) -> None:
        """Dynamically switches active model repository and resets warmed flag."""
        with self._lock:
            if self.model_repo != model_repo:
                log.info("Switching Whisper model from %s -> %s", self.model_repo, model_repo)
                self.model_repo = model_repo
                self.is_warmed = False

    def prewarm(self) -> bool:
        """Pre-warms MLX Whisper in memory so the first dictation is instant."""
        try:
            log.info("Pre-warming MLX Whisper in memory (%s)...", self.model_repo)
            dummy = np.zeros(16000, dtype=np.float32)
            self.transcribe(dummy)
            self.is_warmed = True
            log.info("✅ MLX Whisper (%s) pre-warmed and ready.", self.model_repo)
            return True
        except Exception as e:
            log.warning("Pre-warm degraded for %s: %s", self.model_repo, e)
            return False

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
        with self._lock:
            active_repo = self.model_repo

        log.info("Starting local MLX transcription with model %s (lang=%s)...", active_repo, language or "auto")

        decode_kwargs = {
            "temperature": 0.0,  # Greedy decoding for maximum speed and deterministic output
        }
        if language:
            decode_kwargs["language"] = language

        try:
            result = mlx_whisper.transcribe(
                audio,
                path_or_hf_repo=active_repo,
                initial_prompt=initial_prompt or "",
                **decode_kwargs,
            )
        except Exception as e:
            fallback = MODELS["low_ram"]["repo"]
            log.warning("Primary model %s failed (%s). Retrying with fallback %s...", active_repo, e, fallback)
            result = mlx_whisper.transcribe(
                audio,
                path_or_hf_repo=fallback,
                initial_prompt=initial_prompt or "",
                **decode_kwargs,
            )

        elapsed = time.time() - t0
        text = result.get("text", "").strip()
        log.info("MLX transcription completed in %.2fs: '%s'", elapsed, text)
        return text
