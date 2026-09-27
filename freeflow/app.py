"""freeflow/app.py — Native macOS Menu Bar Application for FreeFlow.

Provides:
- Menu Bar Status Item (NSStatusBar) with live state indicator (Ready, Recording, Processing)
- Quick actions: Toggle Dictation, Recent snippets submenu with 1-click re-copying
- Model switcher submenu (Turbo, Low-RAM, Ultra-Lite)
- Native Frosted Glass Settings & History Window powered by WKWebView and embedded Web API
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from typing import Optional

import objc
from pynput import keyboard

# Load Apple frameworks via PyObjC
import AppKit
from AppKit import (
    NSAlert,
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSApplicationActivationPolicyRegular,
    NSBackingStoreBuffered,
    NSColor,
    NSMenu,
    NSMenuItem,
    NSRect,
    NSStatusBar,
    NSVariableStatusItemLength,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable,
    NSWindowStyleMaskResizable,
    NSWindowStyleMaskTitled,
)

# Load WebKit framework
objc.loadBundle("WebKit", globals(), bundle_path="/System/Library/Frameworks/WebKit.framework")

from freeflow.constants import APP_NAME, HOTKEYS, MODELS
from freeflow.engine import DictationEngine
from freeflow.hotkey import HotkeyMonitor
from freeflow.injector import TextInjector
from freeflow.server import APIServer

log = logging.getLogger("freeflow.app")


def get_pynput_trigger_key(key_name: str) -> keyboard.Key:
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


class FreeFlowMenuBarApp(AppKit.NSObject):
    """Native macOS Menu Bar Status Item & Controller."""

    def init(self) -> Optional[FreeFlowMenuBarApp]:
        self = objc.super(FreeFlowMenuBarApp, self).init()
        if self is None:
            return None

        self.engine: Optional[DictationEngine] = None
        self.server: Optional[APIServer] = None
        self.hotkey_monitor: Optional[HotkeyMonitor] = None
        self.status_item = None
        self.settings_window = None
        self.web_view = None
        return self

    @objc.python_method
    def start_with_engine(self, engine: DictationEngine, server: APIServer) -> None:
        self.engine = engine
        self.server = server
        self.engine.status_callback = self.on_engine_status_change

        # Setup NSStatusBar item
        self.status_bar = NSStatusBar.systemStatusBar()
        self.status_item = self.status_bar.statusItemWithLength_(NSVariableStatusItemLength)
        self.update_status_item_label("FreeFlow 🎙️")

        # Build initial menu
        self.rebuild_menu()

        # Start Hotkey listener
        trigger_key = get_pynput_trigger_key(self.engine.config.hotkey)
        self.hotkey_monitor = HotkeyMonitor(
            on_start_recording=self.engine.start_recording,
            on_stop_recording=self.engine.stop_recording_and_process,
            on_upgrade_to_toggle=self.engine.upgrade_to_toggle,
            trigger_key=trigger_key,
        )
        self.engine.hotkey_monitor = self.hotkey_monitor
        self.hotkey_monitor.start()

    @objc.python_method
    def update_status_item_label(self, label: str) -> None:
        if self.status_item and self.status_item.button():
            self.status_item.button().setTitle_(label)

    @objc.python_method
    def on_engine_status_change(self, state: str, details: dict) -> None:
        """Invoked on worker threads from DictationEngine."""
        def _update() -> None:
            if state == "recording":
                self.update_status_item_label("FreeFlow 🔴")
            elif state in ("transcribing", "formatting"):
                self.update_status_item_label("FreeFlow 🟣")
            elif state == "done":
                self.update_status_item_label("FreeFlow ✨")
                time.sleep(1.0)
                self.update_status_item_label("FreeFlow 🎙️")
            else:
                self.update_status_item_label("FreeFlow 🎙️")
            self.rebuild_menu()

        # Dispatch UI updates onto main thread
        AppKit.dispatch_async(AppKit.dispatch_get_main_queue(), _update)

    @objc.python_method
    def rebuild_menu(self) -> None:
        menu = NSMenu.alloc().init()
        menu.setAutoenablesItems_(False)

        # 1. Status Header
        state = self.engine.current_state if self.engine else "idle"
        state_labels = {
            "idle": "FreeFlow: Ready",
            "recording": "FreeFlow: Recording... 🔴",
            "transcribing": "FreeFlow: Transcribing with MLX... 🟣",
            "formatting": "FreeFlow: Formatting text... ✨",
            "done": "FreeFlow: Dictation Injected! ✓",
        }
        header_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            state_labels.get(state, "FreeFlow: Ready"),
            None,
            "",
        )
        header_item.setEnabled_(False)
        menu.addItem_(header_item)

        # 2. Toggle Dictation Action
        toggle_title = "⏹ Stop Dictation" if state == "recording" else "🎙️ Start Dictation"
        toggle_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            toggle_title,
            objc.selector(self.toggleDictation_, signature=b"v@:@"),
            "",
        )
        toggle_item.setTarget_(self)
        menu.addItem_(toggle_item)

        menu.addItem_(NSMenuItem.separatorItem())

        # 3. Recent Dictations Submenu
        recent_menu = NSMenu.alloc().init()
        recent_entries = self.engine.history_mgr.get_recent(limit=5) if self.engine else []
        if recent_entries:
            for entry in recent_entries:
                snippet = entry["text"]
                label = (snippet[:38] + "...") if len(snippet) > 38 else snippet
                item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    f"\"{label}\"",
                    objc.selector(self.copySnippetAction_, signature=b"v@:@"),
                    "",
                )
                item.setRepresentedObject_(snippet)
                item.setTarget_(self)
                recent_menu.addItem_(item)
        else:
            empty_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("(No recent dictations)", None, "")
            empty_item.setEnabled_(False)
            recent_menu.addItem_(empty_item)

        recent_parent = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("📋 Recent Dictations", None, "")
        recent_parent.setSubmenu_(recent_menu)
        menu.addItem_(recent_parent)

        # Full History Item
        history_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Open Clipboard History...",
            objc.selector(self.openHistoryTab_, signature=b"v@:@"),
            "h",
        )
        history_item.setTarget_(self)
        menu.addItem_(history_item)

        menu.addItem_(NSMenuItem.separatorItem())

        # 4. Voice Models Submenu
        models_menu = NSMenu.alloc().init()
        active_repo = self.engine.transcriber.model_repo if self.engine else ""
        for m_id, m in MODELS.items():
            is_active = (m["repo"] == active_repo)
            prefix = "✓ " if is_active else "   "
            item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                f"{prefix}{m['name']} ({m['latency']})",
                objc.selector(self.switchModelAction_, signature=b"v@:@"),
                "",
            )
            item.setRepresentedObject_(m["repo"])
            item.setTarget_(self)
            models_menu.addItem_(item)

        models_parent = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("⚡ Voice Models & RAM", None, "")
        models_parent.setSubmenu_(models_menu)
        menu.addItem_(models_parent)

        # 5. Dictionary & Settings
        dict_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "📖 Custom Dictionary & Slang...",
            objc.selector(self.openDictionaryTab_, signature=b"v@:@"),
            "d",
        )
        dict_item.setTarget_(self)
        menu.addItem_(dict_item)

        settings_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "⚙️ Preferences & Settings...",
            objc.selector(self.openSettingsTab_, signature=b"v@:@"),
            ",",
        )
        settings_item.setTarget_(self)
        menu.addItem_(settings_item)

        menu.addItem_(NSMenuItem.separatorItem())

        # 6. Quit
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit FreeFlow",
            objc.selector(self.quitApp_, signature=b"v@:@"),
            "q",
        )
        quit_item.setTarget_(self)
        menu.addItem_(quit_item)

        self.status_item.setMenu_(menu)

    def toggleDictation_(self, sender: NSMenuItem) -> None:
        if not self.engine:
            return
        if self.engine.current_state == "recording":
            self.engine.stop_recording_and_process()
        else:
            self.engine.start_recording(is_toggle=True)

    def copySnippetAction_(self, sender: NSMenuItem) -> None:
        text = sender.representedObject()
        if text:
            TextInjector.set_clipboard(str(text))
            log.info("Copied recent snippet to clipboard from menu.")

    def switchModelAction_(self, sender: NSMenuItem) -> None:
        repo = sender.representedObject()
        if repo and self.engine:
            self.engine.switch_model(str(repo))
            self.rebuild_menu()

    def openHistoryTab_(self, sender: NSMenuItem) -> None:
        self.show_window_with_tab("tab-history")

    def openDictionaryTab_(self, sender: NSMenuItem) -> None:
        self.show_window_with_tab("tab-dictionary")

    def openSettingsTab_(self, sender: NSMenuItem) -> None:
        self.show_window_with_tab("tab-settings")

    @objc.python_method
    def show_window_with_tab(self, tab_id: str) -> None:
        if not self.settings_window:
            self.create_settings_window()

        url_str = f"{self.server.url}/"
        ns_url = AppKit.NSURL.URLWithString_(url_str)
        req = AppKit.NSURLRequest.requestWithURL_(ns_url)
        self.web_view.loadRequest_(req)

        self.settings_window.makeKeyAndOrderFront_(None)
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

        # Trigger tab switch via JS after small delay
        def _switch_tab() -> None:
            time.sleep(0.35)
            js = f"document.querySelector('[data-tab=\"{tab_id}\"]')?.click();"
            self.web_view.evaluateJavaScript_completionHandler_(js, None)

        threading.Thread(target=_switch_tab, daemon=True).start()

    @objc.python_method
    def create_settings_window(self) -> None:
        width: float = 940.0
        height: float = 680.0

        screen = AppKit.NSScreen.mainScreen()
        screen_frame = screen.visibleFrame() if screen else NSRect((0, 0), (1200, 800))
        x = screen_frame.origin.x + (screen_frame.size.width - width) / 2
        y = screen_frame.origin.y + (screen_frame.size.height - height) / 2

        frame = NSRect((x, y), (width, height))
        style_mask = (
            NSWindowStyleMaskTitled
            | NSWindowStyleMaskClosable
            | NSWindowStyleMaskMiniaturizable
            | NSWindowStyleMaskResizable
        )

        self.settings_window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame, style_mask, NSBackingStoreBuffered, False
        )
        self.settings_window.setTitle_("FreeFlow — On-Device Voice Dictation")
        self.settings_window.setBackgroundColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(0.04, 0.05, 0.08, 1.0))
        self.settings_window.setReleasedWhenClosed_(False)

        # Create WKWebView
        config = WKWebViewConfiguration.alloc().init()
        self.web_view = WKWebView.alloc().initWithFrame_configuration_(
            NSRect((0, 0), (width, height)), config
        )
        self.web_view.setAutoresizingMask_(AppKit.NSViewWidthSizable | AppKit.NSViewHeightSizable)
        self.settings_window.setContentView_(self.web_view)

    def quitApp_(self, sender: NSMenuItem) -> None:
        log.info("Quitting FreeFlow...")
        if self.hotkey_monitor:
            self.hotkey_monitor.stop()
        if self.server:
            self.server.stop()
        NSApplication.sharedApplication().terminate_(self)


def run_menu_bar_app(engine: Optional[DictationEngine] = None) -> None:
    """Launches the native FreeFlow Menu Bar App."""
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    engine_instance = engine or DictationEngine()
    server = APIServer(engine=engine_instance)
    server.start()

    delegate = FreeFlowMenuBarApp.alloc().init()
    delegate.start_with_engine(engine_instance, server)

    log.info("⚡ FreeFlow macOS Menu Bar App active! UI URL: %s", server.url)
    app.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_menu_bar_app()
