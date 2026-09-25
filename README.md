# 🎙️ FreeFlow (macOS)

> **Universal 100% On-Device Voice Dictation for Apple Silicon.**
> Fast, private, subscription-free alternative to Wispr Flow and Superwhisper.
> Powered by Apple MLX Metal acceleration, native macOS Menu Bar HUD, two-tier intelligent cleanup, and app context awareness.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: macOS Apple Silicon](https://img.shields.io/badge/Platform-macOS%20Apple%20Silicon-black.svg)]()
[![Privacy: 100% Offline](https://img.shields.io/badge/Privacy-100%25%20On--Device-brightgreen.svg)]()
[![RAM: < 1 GB](https://img.shields.io/badge/RAM-%3C%201%20GB-purple.svg)]()

---

## ⚡ Why FreeFlow?

Closed-source dictation tools charge $12–$20/month, route your private speech and audio to remote cloud servers, or consume multiple gigabytes of memory.

**FreeFlow** delivers the same instant experience entirely offline on your Mac:
- **🔒 100% Offline & Private**: Zero audio or text ever leaves your Mac. Zero telemetry, zero subscriptions.
- **⚡ Blazing Fast**: Sub-350ms transcription latency running locally on Apple Silicon Metal via Apple MLX.
- **🧠 SOTA Accuracy under 1 GB RAM**: Runs `mlx-community/whisper-large-v3-turbo-4bit` in ~740 MB unified memory.
- **🎙️ Dual Mode (App or CLI)**: Run as a native macOS Menu Bar App with a floating Siri-style glowing pill HUD, or as a headless CLI background daemon.
- **⚡ 1-Click Model Downloader & RAM Budgets**: Seamlessly switch between Turbo (SOTA), Low-RAM (~350MB), and Ultra-Lite (~150MB).
- **🎤 Zero Cutoff Syllables**: 400ms rolling ring buffer captures words spoken the exact instant your finger touches the key.
- **🧹 Intelligent Cleanup & Formatting**:
  - **Tier 1 (Instant Rule Cleaner)**: Strips filler words (*um, uh, aa, like*), stutters (*the the*), spoken punctuation (*new paragraph, colon*), and formatted lists (*number one, number two*).
  - **Tier 2 (Local SLM - Qwen 2.5 1.5B)**: Handles in-place mid-sentence self-corrections (*"make it pink no wait blue and save"* ➔ *"Make it blue and save."*).
- **🌐 Multilingual & Auto-Detect**: Transcribes English, Hindi (Devanagari script), Konkani, and Hinglish with zero unwanted English translation.
- **📱 App Context Awareness**: Automatically adapts formatting based on the frontmost app (code syntax in VS Code/Terminal, markdown in Obsidian, search queries in Safari/Chrome).
- **📋 Integrated Clipboard History**: Searchable log of dictated snippets with 1-click re-copying.
- **📖 Custom Vocabulary & Phonetic Rules**: Graphic UI to add technical jargon, personal names, and phonetic mishearings.

---

## 🚀 1-Click Quickstart

### 1. Prerequisites
- Apple Silicon Mac (M1/M2/M3/M4)
- macOS 13+ (Ventura, Sonoma, Sequoia)
- Python 3.10+

### 2. One-Command Setup & Launch
```bash
git clone https://github.com/your-username/whisper-flow.git
cd whisper-flow

# Launch FreeFlow (automatically builds virtualenv and opens the Menu Bar App)
./run.sh
```

Or install in your Python environment:
```bash
pip install -e .

# Launch Menu Bar App
freeflow

# Or run as headless CLI daemon
freeflow --cli
```

---

## ⌨️ How to Trigger Dictation

| Trigger | Action | Behavior |
| :--- | :--- | :--- |
| **Push-to-Talk** | **Hold Right Option (`Key.alt_r`)** | Speak while holding. Releasing immediately transcribes and pastes into the focused app. |
| **Hands-Free Toggle** | **Double-Tap Right Option** | Tap twice within 400ms. Hands-free recording begins. Auto-stops after 2.5s of silence or on another key tap. |
| **Dedicated Hotkey** | **Tap `F8`** | Single-tap hands-free toggle with Voice Activity Detection (VAD). |

*Hotkeys can be customized directly in the Settings UI (Right Option, Left Option, Right Command, F8).*

---

## ⚡ Voice Models & Unified RAM Budgets

FreeFlow supports 1-click model switching to fit any RAM budget:

| Module | Model Repo | Size | RAM Footprint | Typical Latency | Best For |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 🌟 **Turbo (Recommended)** | `whisper-large-v3-turbo-4bit` | ~464 MB | ~740 MB | ~250–350ms | SOTA accuracy & multilingual transcription |
| ⚡ **Low RAM** | `whisper-small-mlx-4bit` | ~197 MB | ~350 MB | ~180–250ms | Multitasking on 8GB / 16GB Macs |
| 🪶 **Ultra-Lite** | `whisper-tiny-mlx-4bit` | ~75 MB | ~150 MB | ~100–180ms | Ultra-fast instant notes |

Switch models anytime with 1-click in the Menu Bar dropdown or App Settings, or via CLI:
```bash
# View model statuses & disk caching
freeflow --models

# 1-click automated download
freeflow --download ultra_lite
```

---

## 📖 Custom Vocabulary & Phonetic Dictionary

Teach FreeFlow your personal vocabulary without touching JSON files:

### Via Native Settings UI
Click the Menu Bar icon ➔ **Custom Dictionary & Slang...** to open the interactive manager:
- **Acoustic Vocabulary**: Add custom names, jargon, company terms to bias Whisper's acoustic decoding prompt.
- **Phonetic Corrections**: Add regex replacement rules (e.g. `visval floor` ➔ `FreeFlow`).

### Via CLI
```bash
# Add a custom vocabulary word
freeflow --add-word "Susegad"

# Add a phonetic correction for commonly misheard phrases
freeflow --add-correction "visval floor" "FreeFlow"

# Inspect current dictionary
freeflow --dict
```

---

## 📋 Clipboard History

Never lose what you dictated:
- View recent snippets right from the macOS Menu Bar submenu.
- Click any snippet to instantly copy it back to your pasteboard.
- Open **Clipboard History...** for a full chronological, searchable timeline with word counts, duration, and target application badges.

---

## 🛠️ CLI Commands & Cheatsheet

```bash
# Launch Menu Bar App (Default)
freeflow

# Run Headless Terminal Daemon
freeflow --cli

# List Models & RAM Usage
freeflow --models

# Download Model Weights
freeflow --download turbo
freeflow --download low_ram
freeflow --download ultra_lite

# Inspect or Add to Dictionary
freeflow --dict
freeflow --add-word "MLX"
freeflow --add-correction "cloud code" "Claude Code"

# View Dictation History
freeflow --history

# Test Text Cleaner Directly
freeflow --test-clean "have pink as the colour wait wait no make it blue and save the file"
```

---

## 🧩 Architecture

```
┌────────────────────────────────────────────────────────┐
│                   FreeFlow App & CLI                   │
├────────────────────────────────────────────────────────┤
│  [Native macOS Menu Bar App] (PyObjC AppKit / WKWebView│
│  ├── Dynamic Status: Idle 🟢 | Dictating 🔴 | Injected 🟣
│  ├── 1-Click Model Switcher (Turbo / Low-RAM / Ultra-Li│
│  ├── Custom Dictionary & Phonetic Corrections Editor   │
│  ├── Clipboard History Timeline (Searchable + 1-Click C│
│  └── Hotkey & Voice Activity Detection (VAD) Settings  │
├────────────────────────────────────────────────────────┤
│  [Floating HUD Overlay] (Swift Native Window)          │
│  ├── Siri-style glowing orb & active waveform bars     │
│  └── Overlays full-screen apps and multiple spaces     │
├────────────────────────────────────────────────────────┤
│  [Core Engine] (whisper_flow)                          │
│  ├── 16kHz Stream with 400ms Rolling Ring Buffer + AGC │
│  ├── Apple MLX Metal Whisper Engine (sub-350ms)        │
│  ├── Context Detector (AppKit / AppleScript inspector) │
│  ├── Tier 1 Instant Rule Cleaner (Fillers & Lists)     │
│  ├── Tier 2 Local SLM Cleaner (Qwen 2.5 1.5B)          │
│  ├── Universal Text Injector (Cmd+V with clip restore) │
│  └── Persistent Config & History Managers              │
└────────────────────────────────────────────────────────┘
```

---

## 🗺️ Cross-Platform Roadmap

- [x] Apple Silicon MLX Whisper Large Turbo, Small, Tiny 4-bit
- [x] 400ms rolling ring buffer & software AGC (zero initial syllable loss)
- [x] Push-to-Talk, Double-Tap Hands-Free Toggle, and F8 shortcut
- [x] Silence Auto-Cutoff (VAD)
- [x] Native macOS Menu Bar status item (idle, recording, processing)
- [x] Siri-Style Floating Pill HUD overlay with active waveforms
- [x] 1-Click Model Downloader & RAM Budget options
- [x] Interactive Frosted Glass Settings & Dictionary UI (WKWebView)
- [x] Persistent Clipboard History Manager
- [x] Modular platform abstraction layer (`whisper_flow.platform`)
- [ ] Linux support (xdotool / wl-clipboard / whisper.cpp)
- [ ] Windows support (win32gui / DirectML)
- [ ] Standalone `.dmg` signed installer

---

## 📄 License

MIT License. Free and open source for everyone.
