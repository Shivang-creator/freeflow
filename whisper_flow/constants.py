"""whisper_flow/constants.py — Universal Constants and Model Definitions for FreeFlow."""

from __future__ import annotations

import os
from pathlib import Path

# Branding & Metadata
APP_NAME = "FreeFlow"
APP_SUBTITLE = "100% On-Device Voice Dictation"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Shivang Shirodkar"
APP_DESCRIPTION = "Universal 100% on-device speech-to-text dictation engine for Apple Silicon with low RAM and instant paste."

# Configuration & Data Directories
USER_HOME = Path.home()
CONFIG_DIR = USER_HOME / ".freeflow"
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_FILE = CONFIG_DIR / "history.json"
USER_DICTIONARY_FILE = CONFIG_DIR / "dictionary.json"

# Fallback bundled dictionary in the package
DEFAULT_DICTIONARY_FILE = Path(__file__).resolve().parent / "dictionary.json"

# HUD Socket Paths
FREEFLOW_HUD_SOCKET = "/tmp/freeflow_hud.sock"
LEGACY_HUD_SOCKET = "/tmp/jarvis_hud.sock"

# Voice Models Configuration & RAM Budgets
MODELS = {
    "turbo": {
        "id": "turbo",
        "name": "Turbo (Recommended)",
        "repo": "mlx-community/whisper-large-v3-turbo-4bit",
        "size_mb": 464,
        "ram_mb": 740,
        "latency": "~250–350ms",
        "badge": "🌟 SOTA Accuracy",
        "description": "Large-v3-turbo 4-bit. SOTA accuracy & multilingual detection in ~740 MB unified RAM.",
        "recommended": True,
    },
    "low_ram": {
        "id": "low_ram",
        "name": "Low RAM",
        "repo": "mlx-community/whisper-small-mlx-4bit",
        "size_mb": 197,
        "ram_mb": 350,
        "latency": "~180–250ms",
        "badge": "⚡ Low RAM",
        "description": "Small 4-bit. Blazing fast transcription in ~350 MB RAM, ideal for 8GB Macs.",
        "recommended": False,
    },
    "ultra_lite": {
        "id": "ultra_lite",
        "name": "Ultra-Lite",
        "repo": "mlx-community/whisper-tiny-mlx-4bit",
        "size_mb": 75,
        "ram_mb": 150,
        "latency": "~100–180ms",
        "badge": "🪶 Ultra-Lite",
        "description": "Tiny 4-bit. Featherweight ~150 MB footprint with near-zero resource consumption.",
        "recommended": False,
    },
}

DEFAULT_MODEL_ID = "turbo"
DEFAULT_MODEL_REPO = MODELS["turbo"]["repo"]

# Supported Hotkeys
HOTKEYS = {
    "alt_r": {
        "id": "alt_r",
        "label": "Right Option (Recommended)",
        "description": "Hold Right Option to speak, release to paste.",
    },
    "alt_l": {
        "id": "alt_l",
        "label": "Left Option",
        "description": "Hold Left Option to speak, release to paste.",
    },
    "cmd_r": {
        "id": "cmd_r",
        "label": "Right Command",
        "description": "Hold Right Command to speak, release to paste.",
    },
    "ctrl_r": {
        "id": "ctrl_r",
        "label": "Right Control",
        "description": "Hold Right Control to speak, release to paste.",
    },
    "f8": {
        "id": "f8",
        "label": "F8 Function Key",
        "description": "Tap F8 to start/stop dictation with silence detection.",
    },
}
