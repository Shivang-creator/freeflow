# 🎙️ WhisperFlow (macOS)

> **Universal 100% On-Device Voice Dictation for Apple Silicon.**
> Fast, private, subscription-free alternative to Wispr Flow and Superwhisper.
> Powered by Apple MLX Metal acceleration, two-tier text cleanup, and smart app context awareness.

---

## ⚡ Key Highlights

- **🔒 100% Offline & Private**: Zero audio or text ever leaves your Mac. No cloud APIs, no subscriptions.
- **⚡ Blazing Fast**: ~250–350ms transcription latency running locally on Apple Silicon Metal via Apple MLX.
- **🧠 SOTA Accuracy under 1 GB RAM**: Uses `mlx-community/whisper-large-v3-turbo-4bit` in ~740 MB unified memory.
- **🎤 Zero Cutoff Syllables**: 400ms rolling ring buffer captures words spoken the exact instant your finger hits the key.
- **🧹 Intelligent Cleanup & Formatting**:
  - **Tier 1 (Instant Rule Cleaner)**: Strips filler words (*um, uh, aa, like*), stutters (*the the*), spoken punctuation (*new paragraph, colon*), and formatted lists (*number one, number two*).
  - **Tier 2 (Local SLM - Qwen 2.5 1.5B)**: Handles in-place mid-sentence self-corrections (*"pink no wait make it blue and save"*) without moving words to the end.
- **🌐 Multilingual & Auto-Detect**: Transcribes English, Hindi (Devanagari script), Konkani, and Hinglish with zero unwanted English translation.
- **📱 macOS App Context Awareness**: Automatically adapts formatting based on the frontmost app (code syntax in VS Code/Terminal, markdown in Obsidian, query format in Chrome/Safari).
- **📋 Universal Text Injection**: Seamlessly pastes into any active application with transparent clipboard restoration.
- **🎧 Voice Activity Detection (VAD)**: Hands-free toggle mode auto-stops and pastes after 2.5s of silence.

---

## 🚀 Quickstart

### 1. Prerequisites
- Apple Silicon Mac (M1/M2/M3/M4)
- macOS 13+ (Ventura or later)
- Python 3.10+
- (Optional for Smart Formatting): [Ollama](https://ollama.ai) with `qwen2.5:1.5b`

### 2. Installation
```bash
git clone https://github.com/your-username/whisper-flow.git
cd whisper-flow

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Running Dictation
```bash
# Start background dictation engine
python -m whisper_flow.main
```

---

## ⌨️ How to Trigger Dictation

| Trigger | Action | Behavior |
| :--- | :--- | :--- |
| **Push-to-Talk** | **Hold Right Option (`Key.alt_r`)** | Speak while holding. Releasing immediately transcribes and pastes into the focused app. |
| **Hands-Free Toggle** | **Double-Tap Right Option** | Tap twice within 400ms. Hands-free recording begins. Auto-stops after 2.5s of silence or on another key tap. |
| **Dedicated Hotkey** | **Tap `F8`** | Single-tap hands-free toggle with Voice Activity Detection (VAD). |

---

## 📖 Custom Vocabulary & Phonetic Dictionary

Add your own names, slang, and phonetic corrections:

```bash
# Add a custom vocabulary word to bias Whisper's initial prompt
python -m whisper_flow.main --add-word "Susegad"

# Add a phonetic correction for commonly misheard phrases
python -m whisper_flow.main --add-correction "visval floor" "Wispr Flow"

# Inspect current dictionary
python -m whisper_flow.main --dict
```

Or edit `whisper_flow/dictionary.json` directly.

---

## ⚙️ Model Options

WhisperFlow supports multiple quantized MLX Whisper weights to fit any RAM budget:

```bash
# Default: SOTA Accuracy (~464MB model, ~740MB RAM)
python -m whisper_flow.main --whisper-model mlx-community/whisper-large-v3-turbo-4bit

# Low RAM: (~197MB model, ~350MB RAM)
python -m whisper_flow.main --whisper-model mlx-community/whisper-small-mlx-4bit

# Fast Mode: Disable SLM and run purely on zero-latency rule cleaner
python -m whisper_flow.main --no-slm
```

---

## 🗺️ Roadmap to 1-Click App

- [x] Apple Silicon MLX Whisper Large Turbo integration
- [x] 400ms rolling ring buffer & software AGC
- [x] Push-to-Talk, Double-Tap Hands-Free Toggle, and F8 shortcut
- [x] Silence Auto-Cutoff (VAD)
- [x] Context-aware formatting & mid-sentence self-correction
- [x] Multilingual auto-detection & Hindi preservation
- [ ] Native macOS Menu Bar status item (idle, listening, processing)
- [ ] 1-Click Settings GUI (hotkey configuration, model selector, dictionary manager)
- [ ] Integrated Clipboard History Viewer
- [ ] Standalone `.dmg` installer with pre-bundled weights

---

## 📄 License
MIT License. Free and open source for everyone.
