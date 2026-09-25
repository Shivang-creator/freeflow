"""whisper_flow/config.py — Persistent Configuration Manager for FreeFlow."""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from whisper_flow.constants import (
    CONFIG_DIR,
    CONFIG_FILE,
    DEFAULT_MODEL_REPO,
    MODELS,
)

log = logging.getLogger("freeflow.config")


@dataclass
class AppConfig:
    hotkey: str = "alt_r"
    whisper_model: str = DEFAULT_MODEL_REPO
    enable_slm: bool = True
    slm_model: str = "qwen2.5:1.5b"
    enable_sound: bool = True
    enable_hud: bool = True
    vad_pause_seconds: float = 2.5
    restore_clipboard: bool = True
    auto_start_at_login: bool = False
    custom_vocab_prompt_limit: int = 40

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppConfig:
        known_fields = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)


class ConfigManager:
    """Thread-safe persistent configuration manager."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self.config_path = config_path or CONFIG_FILE
        self._lock = threading.Lock()
        self.config = AppConfig()
        self.load()

    def load(self) -> AppConfig:
        with self._lock:
            if not self.config_path.exists():
                self._save_unlocked()
                return self.config

            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.config = AppConfig.from_dict(data)
                log.info("Loaded config from %s", self.config_path)
            except Exception as e:
                log.warning("Failed to parse config at %s (%s). Using defaults.", self.config_path, e)
                self.config = AppConfig()
            return self.config

    def _save_unlocked(self) -> None:
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config.to_dict(), f, indent=2)
            log.info("Saved config to %s", self.config_path)
        except Exception as e:
            log.error("Failed to write config to %s: %s", self.config_path, e)

    def save(self) -> None:
        with self._lock:
            self._save_unlocked()

    def update(self, **kwargs: Any) -> AppConfig:
        with self._lock:
            for k, v in kwargs.items():
                if hasattr(self.config, k):
                    setattr(self.config, k, v)
            self._save_unlocked()
        return self.config

    def get_model_info(self) -> dict[str, Any]:
        """Returns metadata for the currently configured Whisper model."""
        for m in MODELS.values():
            if m["repo"] == self.config.whisper_model:
                return m
        return {
            "id": "custom",
            "name": "Custom Model",
            "repo": self.config.whisper_model,
            "size_mb": 0,
            "ram_mb": 0,
            "latency": "Unknown",
            "badge": "⚙️ Custom",
            "description": self.config.whisper_model,
            "recommended": False,
        }
