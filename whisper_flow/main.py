"""whisper_flow/main.py — FreeFlow CLI & App Entrypoint.

Usage:
    # 1-Click Launch: Starts macOS Menu Bar App with floating HUD
    freeflow
    python -m whisper_flow.main

    # Headless CLI daemon
    freeflow --cli
    python -m whisper_flow.main --cli

    # List & Download Voice Modules
    freeflow --models
    freeflow --download ultra_lite

    # Manage user dictionary
    freeflow --dict
    freeflow --add-word "Susegad"
    freeflow --add-correction "visval floor" "FreeFlow"

    # Inspect recent clipboard history
    freeflow --history
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

# Configure clean logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("freeflow")

from whisper_flow.constants import (
    APP_NAME,
    APP_SUBTITLE,
    APP_VERSION,
    HOTKEYS,
    MODELS,
)
from whisper_flow.dictionary import DictionaryManager
from whisper_flow.engine import DictationEngine
from whisper_flow.history import HistoryManager
from whisper_flow.hotkey import HotkeyMonitor
from whisper_flow.transcriber import download_model, is_model_cached


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} v{APP_VERSION} — {APP_SUBTITLE} (Apple Silicon Metal)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--app", action="store_true", help="Launch native macOS Menu Bar App (Default on macOS)")
    parser.add_argument("--cli", action="store_true", help="Run as headless CLI daemon in terminal")
    parser.add_argument("--key", default="alt_r", help="Trigger key: alt_r (Right Option), alt_l, cmd_r, f8")
    parser.add_argument("--whisper-model", default=None, help="MLX Whisper model repo or ID (turbo, low_ram, ultra_lite)")
    parser.add_argument("--slm-model", default="qwen2.5:1.5b", help="Ollama model for contextual text formatting")
    parser.add_argument("--no-slm", action="store_true", help="Disable SLM and use fast rule cleaner only")
    parser.add_argument("--dict", action="store_true", help="Show current dictionary entries")
    parser.add_argument("--add-word", type=str, help="Add a vocabulary word to bias acoustic Whisper")
    parser.add_argument("--add-correction", nargs=2, metavar=("HEARD", "WRITE"), help="Add a heard -> write correction pair")
    parser.add_argument("--history", action="store_true", help="Display recent clipboard dictation history")
    parser.add_argument("--models", action="store_true", help="List supported MLX Whisper models and RAM usage")
    parser.add_argument("--download", type=str, metavar="MODEL_ID", help="Download a model (turbo, low_ram, ultra_lite)")
    parser.add_argument("--test-clean", type=str, help="Test the cleanup and formatting pipeline on sample text")
    return parser.parse_args()


def get_key_from_string(key_name: str):
    from pynput import keyboard
    mapping = {
        "alt_r": keyboard.Key.alt_r,
        "option_r": keyboard.Key.alt_r,
        "alt_l": keyboard.Key.alt_l,
        "option_l": keyboard.Key.alt_l,
        "cmd_r": keyboard.Key.cmd_r,
        "ctrl_r": keyboard.Key.ctrl_r,
        "f8": keyboard.Key.f8,
    }
    return mapping.get(key_name.lower(), keyboard.Key.alt_r)


def main() -> None:
    args = parse_args()
    dict_mgr = DictionaryManager()
    history_mgr = HistoryManager()

    # 1. Models overview
    if args.models:
        print("\n" + "=" * 68)
        print(f"🎙️  {APP_NAME.upper()} — VOICE MODULES & RAM BUDGETS")
        print("=" * 68)
        for m_id, m in MODELS.items():
            cached = is_model_cached(m["repo"])
            status = "✅ Cached on Disk" if cached else "☁️  Download Required"
            rec = " [RECOMMENDED]" if m.get("recommended") else ""
            print(f"\n• {m['name']}{rec}:")
            print(f"  - Model ID:     {m_id}")
            print(f"  - HuggingFace:  {m['repo']}")
            print(f"  - Weight Size:  ~{m['size_mb']} MB")
            print(f"  - RAM Usage:    ~{m['ram_mb']} MB unified memory")
            print(f"  - Latency:      {m['latency']}")
            print(f"  - Status:       {status}")
            print(f"  - Summary:      {m['description']}")
        print("\nTo download a model: freeflow --download <model_id>")
        print("=" * 68 + "\n")
        return

    # 2. Download model directly
    if args.download:
        target_id = args.download.lower()
        if target_id in MODELS:
            repo = MODELS[target_id]["repo"]
        else:
            repo = args.download
        print(f"\n⚡ Downloading {repo} from HuggingFace...")
        success = download_model(repo)
        if success:
            print(f"✅ Model weights ready on disk! ({repo})\n")
        else:
            print(f"❌ Failed to download model weights ({repo}).\n")
        return

    # 3. View Dictionary
    if args.dict:
        print("\n--- 📖 Custom FreeFlow Dictionary ---")
        print(f"Path: {dict_mgr.dict_path}\n")
        print(f"Vocabulary ({len(dict_mgr.vocabulary)} words):")
        for w in dict_mgr.vocabulary:
            print(f"  • {w}")
        print(f"\nCorrections ({len(dict_mgr.corrections)} pairs):")
        for h, w in dict_mgr.corrections.items():
            print(f"  • '{h}' ➔ '{w}'")
        print("--------------------------------------\n")
        return

    # 4. Add word
    if args.add_word:
        dict_mgr.add_word(args.add_word)
        print(f"✅ Added vocabulary word: '{args.add_word}'")
        return

    # 5. Add correction
    if args.add_correction:
        h, w = args.add_correction
        dict_mgr.add_correction(h, w)
        print(f"✅ Added correction: '{h}' ➔ '{w}'")
        return

    # 6. View Clipboard History
    if args.history:
        entries = history_mgr.get_recent(limit=15)
        print(f"\n--- 📋 Recent Dictation History ({len(entries)} items) ---")
        for e in entries:
            print(f"[{e['iso_time']}] [{e['app_name']}] ({e['duration_s']}s, {e['word_count']} words)")
            print(f"  \"{e['text']}\"\n")
        print("------------------------------------------------------\n")
        return

    # 7. Test Cleaner
    if args.test_clean:
        print(f"\nTesting cleanup on: '{args.test_clean}'")
        engine = DictationEngine(enable_slm=not args.no_slm, slm_model=args.slm_model, prewarm=False)
        context = engine.context_detector.get_active_context()
        print(f"Active Context: App={context.app_name}, Mode={context.mode.value}")
        corrected, applied = dict_mgr.apply_corrections(args.test_clean)
        print(f"After Dictionary Pass: '{corrected}' (Applied: {applied})")
        final = engine._clean_and_format(corrected, context)
        print(f"Final Cleaned Text:    '{final}'\n")
        return

    # Determine Model Repo
    model_repo = args.whisper_model
    if model_repo and model_repo in MODELS:
        model_repo = MODELS[model_repo]["repo"]

    # If running on macOS without --cli, launch Native Menu Bar App by default
    if sys.platform == "darwin" and not args.cli:
        try:
            from whisper_flow.app import run_menu_bar_app
            print(f"🚀 Starting {APP_NAME} Menu Bar App...")
            engine = DictationEngine(
                whisper_model=model_repo,
                slm_model=args.slm_model,
                enable_slm=not args.no_slm,
            )
            run_menu_bar_app(engine=engine)
            return
        except Exception as e:
            log.warning("Menu Bar GUI initialization failed (%s). Falling back to CLI daemon.", e)

    # Headless CLI Daemon Mode
    trigger_key = get_key_from_string(args.key)

    print("\n" + "=" * 68)
    print(f"🎙️  {APP_NAME.upper()} — 100% ON-DEVICE SPEECH-TO-TEXT DAEMON")
    print("=" * 68)
    print("• Push-to-Talk:       HOLD Right Option key (speak and release)")
    print("• Hands-Free Toggle:  DOUBLE-TAP Right Option or Tap F8 (with 2.5s VAD auto-stop)")
    print(f"• Whisper Engine:     {model_repo or 'Turbo 4-bit'} (Apple Silicon Metal)")
    print(f"• Text Cleanup:       {'Smart SLM (' + args.slm_model + ')' if not args.no_slm else 'Rule Cleaner (0ms)'}")
    print(f"• User Dictionary:    {len(dict_mgr.vocabulary)} words, {len(dict_mgr.corrections)} phonetic rules")
    print(f"• Universal Paste:    Active across all Apps, Browsers, IDEs & Terminals")
    print("=" * 68)
    print("Daemon running. Press Ctrl+C to stop.\n")

    engine = DictationEngine(
        whisper_model=model_repo,
        slm_model=args.slm_model,
        enable_slm=not args.no_slm,
    )

    hotkey_monitor = HotkeyMonitor(
        on_start_recording=engine.start_recording,
        on_stop_recording=engine.stop_recording_and_process,
        on_upgrade_to_toggle=engine.upgrade_to_toggle,
        trigger_key=trigger_key,
    )
    engine.hotkey_monitor = hotkey_monitor
    hotkey_monitor.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\nStopping {APP_NAME}...")
        hotkey_monitor.stop()


if __name__ == "__main__":
    main()
