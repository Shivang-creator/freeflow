"""whisper_flow/dictionary.py — Custom Vocabulary & Phonetic Correction Engine for FreeFlow.

Implements two complementary mechanisms:
1. Acoustic Biasing: Biases Whisper's initial_prompt so the decoder leans toward user terms.
2. Post-Correction Pass: Deterministic, longest-match-first regex replacement for glued words
   and mishearings (e.g., "cloud code" -> "Claude Code", "dev borem karu" -> "Dev borem korum").
"""

from __future__ import annotations

import json
import logging
import re
import threading
import unicodedata
from pathlib import Path
from typing import Any, Optional

from whisper_flow.constants import DEFAULT_DICTIONARY_FILE, USER_DICTIONARY_FILE

log = logging.getLogger("freeflow.dictionary")


class DictionaryManager:
    """Manages custom vocabulary biasing and deterministic post-corrections."""

    def __init__(self, dict_path: Path | str | None = None) -> None:
        self.dict_path = Path(dict_path or USER_DICTIONARY_FILE)
        self.vocabulary: list[str] = []
        self.corrections: dict[str, str] = {}
        self._compiled_rules: list[tuple[re.Pattern[str], str, str]] = []
        self._lock = threading.Lock()
        self.load()

    def load(self) -> None:
        """Loads vocabulary and corrections from JSON file, initializing if needed."""
        with self._lock:
            if not self.dict_path.exists():
                self._seed_default_dictionary()

            try:
                with open(self.dict_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.vocabulary = sorted(list(set(data.get("vocabulary", []))))
                self.corrections = data.get("corrections", {})
                self._compile_rules_unlocked()
                log.info(
                    "Loaded %d vocabulary words and %d correction pairs from %s",
                    len(self.vocabulary),
                    len(self.corrections),
                    self.dict_path.name,
                )
            except Exception as e:
                log.error("Failed to load dictionary from %s: %s", self.dict_path, e)
                self.vocabulary = []
                self.corrections = {}

    def _seed_default_dictionary(self) -> None:
        """Seeds user dictionary from bundled repository dictionary or fallback defaults."""
        seed_data = None
        if DEFAULT_DICTIONARY_FILE.exists():
            try:
                with open(DEFAULT_DICTIONARY_FILE, "r", encoding="utf-8") as f:
                    seed_data = json.load(f)
            except Exception as e:
                log.warning("Could not read bundled default dictionary: %s", e)

        if not seed_data:
            seed_data = {
                "vocabulary": [
                    "FreeFlow", "Whisper", "MLX", "Apple Silicon", "Python",
                    "FastAPI", "Obsidian", "Claude Code", "Dev borem korum", "Susegad",
                ],
                "corrections": {
                    "visval floor": "FreeFlow",
                    "wispr flow": "FreeFlow",
                    "whisper flow": "FreeFlow",
                    "cloud code": "Claude Code",
                    "fast api": "FastAPI",
                },
            }

        try:
            self.dict_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.dict_path, "w", encoding="utf-8") as f:
                json.dump(seed_data, f, indent=2, ensure_ascii=False)
            log.info("Seeded initial dictionary at %s", self.dict_path)
        except Exception as e:
            log.error("Failed to seed initial dictionary at %s: %s", self.dict_path, e)

    def _save_unlocked(self) -> None:
        """Persists dictionary to disk."""
        data = {
            "vocabulary": sorted(list(set(self.vocabulary))),
            "corrections": self.corrections,
        }
        try:
            self.dict_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.dict_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._compile_rules_unlocked()
        except Exception as e:
            log.error("Failed to save dictionary: %s", e)

    def save(self) -> None:
        with self._lock:
            self._save_unlocked()

    def add_word(self, word: str) -> bool:
        """Adds a vocabulary word for acoustic biasing."""
        w = word.strip()
        if not w:
            return False
        with self._lock:
            if w not in self.vocabulary:
                self.vocabulary.append(w)
                self.vocabulary.sort()
                self._save_unlocked()
                return True
        return False

    def remove_word(self, word: str) -> bool:
        """Removes a vocabulary word."""
        w = word.strip()
        with self._lock:
            if w in self.vocabulary:
                self.vocabulary.remove(w)
                self._save_unlocked()
                return True
        return False

    def add_correction(self, heard: str, write: str) -> bool:
        """Adds a heard -> write correction pair."""
        h = heard.strip().lower()
        w = write.strip()
        if not h or not w:
            return False
        with self._lock:
            self.corrections[h] = w
            self._save_unlocked()
            return True

    def remove_correction(self, heard: str) -> bool:
        """Removes a correction rule by its trigger phrase."""
        h = heard.strip().lower()
        with self._lock:
            if h in self.corrections:
                del self.corrections[h]
                self._save_unlocked()
                return True
        return False

    def get_initial_prompt(self, max_words: int = 40) -> str:
        """Generates a concise Whisper initial_prompt string for acoustic biasing."""
        with self._lock:
            if not self.vocabulary:
                return ""
            subset = self.vocabulary[:max_words]
            return ", ".join(subset) + "."

    def _compile_rules_unlocked(self) -> None:
        """Compiles regex patterns: longest trigger first, glued words support."""
        self._compiled_rules = []
        sorted_pairs = sorted(self.corrections.items(), key=lambda p: len(p[0]), reverse=True)

        for trigger, replacement in sorted_pairs:
            trigger_clean = trigger.strip()
            if not trigger_clean:
                continue

            tokens = [re.escape(t) for t in re.split(r"[\s\-]+", trigger_clean) if t]
            if not tokens:
                continue

            pattern_str = r"(?i)\b" + r"[\s\-]*".join(tokens) + r"\b"
            try:
                regex = re.compile(pattern_str)
                self._compiled_rules.append((regex, replacement, trigger_clean))
            except re.error as e:
                log.warning("Invalid regex for trigger '%s': %s", trigger, e)

    def apply_corrections(self, text: str) -> tuple[str, list[dict[str, Any]]]:
        """Applies deterministic corrections with longest-match-first ordering."""
        with self._lock:
            rules = list(self._compiled_rules)

        if not text or not rules:
            return text, []

        result = unicodedata.normalize("NFC", text)
        applied = []

        for regex, replacement, trigger in rules:
            matches = list(regex.finditer(result))
            if matches:
                heard_sample = matches[0].group(0)
                result = regex.sub(replacement, result)
                applied.append({
                    "from": heard_sample,
                    "to": replacement,
                    "count": len(matches),
                    "rule": trigger,
                })

        return result, applied

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "vocabulary": list(self.vocabulary),
                "corrections": dict(self.corrections),
                "vocab_count": len(self.vocabulary),
                "corrections_count": len(self.corrections),
            }
