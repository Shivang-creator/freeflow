"""voice/dictation/hotkey.py — Global Push-to-Talk & Double-Tap Hotkey Monitor.

Listens for Right Option (`Key.alt_r`) using pynput and Quartz Event Tap:
1. Push-to-Talk (Hold): Hold Right Option while speaking, release to transcribe & paste.
2. Double-Tap Toggle: Quick double-tap of Right Option toggles hands-free recording on/off.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional

from pynput import keyboard

log = logging.getLogger("dictation.hotkey")


class HotkeyMonitor:
    """Monitors global keyboard events for Push-to-Talk and Toggle triggers."""

    def __init__(
        self,
        on_start_recording: Callable[..., None],
        on_stop_recording: Callable[[], None],
        on_upgrade_to_toggle: Optional[Callable[[], None]] = None,
        trigger_key: keyboard.Key = keyboard.Key.alt_r,
    ) -> None:
        self.on_start_recording = on_start_recording
        self.on_stop_recording = on_stop_recording
        self.on_upgrade_to_toggle = on_upgrade_to_toggle
        self.trigger_key = trigger_key

        self.is_key_down = False
        self.is_recording = False
        self.is_toggle_mode = False

        self._key_down_time = 0.0
        self._last_release_time = 0.0
        self._listener: Optional[keyboard.Listener] = None
        self._lock = threading.Lock()

    def reset_toggle(self) -> None:
        """Resets toggle state when auto-silence cutoff concludes recording."""
        with self._lock:
            self.is_toggle_mode = False
            self.is_recording = False

    def start(self) -> None:
        """Starts the background keyboard listener."""
        log.info("Starting global hotkey monitor for trigger key: %s", self.trigger_key)
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        """Stops the listener."""
        if self._listener:
            self._listener.stop()
            self._listener = None

    def _is_match(self, key: keyboard.Key | keyboard.KeyCode) -> bool:
        if key == self.trigger_key:
            return True
        # Check vk for Right Option on macOS (61)
        if self.trigger_key == keyboard.Key.alt_r:
            if hasattr(key, "vk") and key.vk == 61:
                return True
        # Also allow F8 as secondary convenience shortcut
        if key == keyboard.Key.f8:
            return True
        return False

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        if not self._is_match(key):
            return

        with self._lock:
            if self.is_key_down:
                return  # Key repeat event
            self.is_key_down = True
            now = time.time()
            self._key_down_time = now

            # If already in toggle mode recording, this press stops it
            if self.is_toggle_mode and self.is_recording:
                log.info("Toggle mode stop triggered by key press.")
                self.is_toggle_mode = False
                self.is_recording = False
                threading.Thread(target=self.on_stop_recording, daemon=True).start()
                return

            # Check if this is the second tap of a double-tap (within 0.40s of last release)
            time_since_last_release = now - self._last_release_time
            if time_since_last_release < 0.40:
                log.info("Double-tap confirmed! Entering toggle hands-free recording mode.")
                self.is_toggle_mode = True
                self.is_recording = True
                if self.on_upgrade_to_toggle:
                    threading.Thread(target=self.on_upgrade_to_toggle, daemon=True).start()
                return

            # Dedicated convenience shortcut: F8 is always a single-tap hands-free toggle
            if key == keyboard.Key.f8:
                if not self.is_recording:
                    log.info("F8 key press: Engaging hands-free toggle mode.")
                    self.is_toggle_mode = True
                    self.is_recording = True
                    threading.Thread(target=self.on_start_recording, kwargs={"is_toggle": True}, daemon=True).start()
                return

            # Otherwise, start push-to-talk recording immediately
            if not self.is_recording:
                self.is_recording = True
                self.is_toggle_mode = False
                log.info("Push-to-talk recording started.")
                threading.Thread(target=self.on_start_recording, kwargs={"is_toggle": False}, daemon=True).start()

    def _on_release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        if not self._is_match(key):
            return

        with self._lock:
            self.is_key_down = False
            now = time.time()
            self._last_release_time = now
            press_duration = now - self._key_down_time

            # If in toggle mode, key release should NOT stop recording (wait for next press)
            if self.is_toggle_mode:
                return

            # If in push-to-talk mode, release stops recording
            if self.is_recording:
                # If released very quickly (<0.28s), user might be trying to double-tap
                if press_duration < 0.28:
                    threading.Thread(target=self._check_double_tap_window, args=(now,), daemon=True).start()
                else:
                    log.info("Push-to-talk released after %.2fs. Stopping recording.", press_duration)
                    self.is_recording = False
                    threading.Thread(target=self.on_stop_recording, daemon=True).start()

    def _check_double_tap_window(self, release_time: float) -> None:
        """Waits briefly to distinguish between a short hold and a double tap."""
        time.sleep(0.35)
        with self._lock:
            # If toggle mode was activated in the meantime, do nothing
            if self.is_toggle_mode:
                return
            # If still recording from a single tap, stop it now
            if self.is_recording and not self.is_key_down and self._last_release_time == release_time:
                log.info("Single quick tap completed. Stopping recording.")
                self.is_recording = False
                threading.Thread(target=self.on_stop_recording, daemon=True).start()
