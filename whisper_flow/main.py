"""voice/dictation/main.py — CLI Entrypoint & Daemon for System-Wide Dictation.

Usage:
    # Run the background dictation daemon (Hold Right Option to speak)
    python -m whisper_flow.main

    # Manage user dictionary
    python -m whisper_flow.main --dict
    python -m whisper_flow.main --add-word "Susegad"
    python -m whisper_flow.main --add-correction "cloud code" "Claude Code"

    # Test text cleaner directly
    python -m whisper_flow.main --test-clean "have pink as the colour wait wait no make it blue"
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

from pynput import keyboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("dictation")

from whisper_flow.dictionary import DictionaryManager
from whisper_flow.engine import DictationEngine
from whisper_flow.hotkey import HotkeyMonitor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="System-Wide macOS Dictation with MLX Whisper and Local SLM")
    parser.add_argument("--key", default="alt_r", help="Trigger key: alt_r (Right Option), cmd_r, f8")
    parser.add_argument("--whisper-model", default="mlx-community/whisper-large-v3-turbo-4bit", help="MLX Whisper model repo")
    parser.add_argument("--slm-model", default="qwen2.5:1.5b", help="Ollama model for contextual text formatting")
    parser.add_argument("--no-slm", action="store_true", help="Disable SLM and use fast rule cleaner only")
    parser.add_argument("--dict", action="store_true", help="Show current dictionary entries")
    parser.add_argument("--add-word", type=str, help="Add a vocabulary word to bias acoustic Whisper")
    parser.add_argument("--add-correction", nargs=2, metavar=("HEARD", "WRITE"), help="Add a heard -> write correction pair")
    parser.add_argument("--test-clean", type=str, help="Test the cleanup and formatting pipeline on a sample text string")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dict_mgr = DictionaryManager()

    if args.dict:
        print("\n--- 📖 Custom Dictation Dictionary ---")
        print(f"Path: {dict_mgr.dict_path}\n")
        print(f"Vocabulary ({len(dict_mgr.vocabulary)} words):")
        for w in dict_mgr.vocabulary:
            print(f"  • {w}")
        print(f"\nCorrections ({len(dict_mgr.corrections)} pairs):")
        for h, w in dict_mgr.corrections.items():
            print(f"  • '{h}' ➔ '{w}'")
        print("--------------------------------------\n")
        return

    if args.add_word:
        dict_mgr.add_word(args.add_word)
        print(f"✅ Added vocabulary word: '{args.add_word}'")
        return

    if args.add_correction:
        h, w = args.add_correction
        dict_mgr.add_correction(h, w)
        print(f"✅ Added correction: '{h}' ➔ '{w}'")
        return

    if args.test_clean:
        print(f"\nTesting cleanup on: '{args.test_clean}'")
        engine = DictationEngine(enable_slm=not args.no_slm, slm_model=args.slm_model)
        context = engine.context_detector.get_active_context()
        print(f"Active Context: App={context.app_name}, Mode={context.mode.value}")
        corrected, applied = dict_mgr.apply_corrections(args.test_clean)
        print(f"After Dictionary Pass: '{corrected}' (Applied: {applied})")
        final = engine._clean_and_format(corrected, context)
        print(f"Final Cleaned Text:    '{final}'\n")
        return

    # Map hotkey argument to pynput Key
    key_map = {
        "alt_r": keyboard.Key.alt_r,
        "option_r": keyboard.Key.alt_r,
        "cmd_r": keyboard.Key.cmd_r,
        "ctrl_r": keyboard.Key.ctrl_r,
        "f8": keyboard.Key.f8,
    }
    trigger_key = key_map.get(args.key.lower(), keyboard.Key.alt_r)

    print("\n" + "=" * 65)
    print("🎙️  SYSTEM-WIDE LOCAL SPEECH-TO-TEXT (OPENWHISPER ENGINE)")
    print("=" * 65)
    print(f"• Trigger:            HOLD Right Option key (Push-to-Talk)")
    print(f"                      or DOUBLE-TAP Right Option / Tap F8 (Hands-Free Toggle + VAD)")
    print(f"• Whisper Engine:     {args.whisper_model} (Apple Silicon MLX)")
    print(f"• Cleanup & SLM:      {args.slm_model if not args.no_slm else 'Disabled (Rule-only)'}")
    print(f"• Custom Dictionary:  {len(dict_mgr.vocabulary)} words, {len(dict_mgr.corrections)} corrections loaded")
    print(f"• Universal Paste:    Active across all Apps, Browsers, IDEs & Terminals")
    print("=" * 65)
    print("Listening for hotkey... Press Ctrl+C to stop.\n")

    engine = DictationEngine(
        whisper_model=args.whisper_model,
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
        print("\nStopping Dictation Service...")
        hotkey_monitor.stop()


if __name__ == "__main__":
    main()
