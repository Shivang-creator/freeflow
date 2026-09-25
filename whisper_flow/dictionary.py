"""voice/dictation/dictionary.py — Custom Vocabulary & Correction Engine.

Implements two complementary mechanisms:
1. Acoustic Biasing: Biases Whisper's initial_prompt so the decoder leans toward user terms.
2. Post-Correction Pass: Deterministic, longest-match-first regex replacement for glued words
   and mishearings (e.g., "cloud code" -> "Claude Code", "dev borem karu" -> "Dev borem korum").
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any

log = logging.getLogger("dictation.dictionary")
DEFAULT_DICT_PATH = Path(__file__).parent / "dictionary.json"


class DictionaryManager:
    """Manages custom vocabulary biasing and deterministic post-corrections."""

    def __init__(self, dict_path: Path | str | None = None) -> None:
        self.dict_path = Path(dict_path or DEFAULT_DICT_PATH)
        self.vocabulary: list[str] = []
        self.corrections: dict[str, str] = {}
        self._compiled_rules: list[tuple[re.Pattern[str], str, str]] = []
        self.load()

    def load(self) -> None:
        """Loads vocabulary and corrections from JSON file."""
        if not self.dict_path.exists():
            log.warning("Dictionary file not found at %s. Creating default.", self.dict_path)
            self._save_defaults()

        try:
            with open(self.dict_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.vocabulary = data.get("vocabulary", [])
            self.corrections = data.get("corrections", {})
            self._compile_rules()
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

    def _save_defaults(self) -> None:
        self.vocabulary = ["Shivang", "JARVIS", "Dev borem korum", "Kitem cholta", "Susegad", "FastAPI", "MLX"]
        self.corrections = {"cloud code": "Claude Code", "fast api": "FastAPI"}
        self.save()

    def save(self) -> None:
        """Persists dictionary to disk."""
        data = {
            "vocabulary": sorted(list(set(self.vocabulary))),
            "corrections": self.corrections,
        }
        with open(self.dict_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self._compile_rules()

    def add_word(self, word: str) -> None:
        """Adds a vocabulary word for acoustic biasing."""
        w = word.strip()
        if w and w not in self.vocabulary:
            self.vocabulary.append(w)
            self.save()

    def add_correction(self, heard: str, write: str) -> None:
        """Adds a heard -> write correction pair."""
        h = heard.strip().lower()
        w = write.strip()
        if h and w:
            self.corrections[h] = w
            self.save()

    def get_initial_prompt(self, max_words: int = 40) -> str:
        """Generates a concise Whisper initial_prompt string for acoustic biasing.
        
        Note: Whisper prompts should be kept under 40-50 words to prevent model drift
        or hallucination during silent pauses.
        """
        if not self.vocabulary:
            return ""
        # Cap vocabulary to prevent Whisper hallucination
        subset = self.vocabulary[:max_words]
        return ", ".join(subset) + "."

    def _compile_rules(self) -> None:
        """Compiles regex patterns: longest trigger first, glued words support."""
        self._compiled_rules = []
        # Sort by trigger length descending so "Claude Code" wins over "Claude"
        sorted_pairs = sorted(self.corrections.items(), key=lambda p: len(p[0]), reverse=True)

        for trigger, replacement in sorted_pairs:
            trigger_clean = trigger.strip()
            if not trigger_clean:
                continue

            # Handle glued words: "cloud code" should match "cloud code", "cloudcode", "cloud-code"
            # Split tokens by space/hyphen and allow optional spaces/hyphens between them
            tokens = [re.escape(t) for t in re.split(r"[\s\-]+", trigger_clean) if t]
            if not tokens:
                continue

            # Pattern: \bToken1[\s\-]*Token2\b
            pattern_str = r"(?i)\b" + r"[\s\-]*".join(tokens) + r"\b"
            try:
                regex = re.compile(pattern_str)
                self._compiled_rules.append((regex, replacement, trigger_clean))
            except re.error as e:
                log.warning("Invalid regex for trigger '%s': %s", trigger, e)

    def apply_corrections(self, text: str) -> tuple[str, list[dict[str, Any]]]:
        """Applies deterministic corrections with longest-match-first ordering.
        
        Returns:
            (corrected_text, list_of_applied_corrections)
        """
        if not text or not self._compiled_rules:
            return text, []

        result = unicodedata.normalize("NFC", text)
        applied = []

        for regex, replacement, trigger in self._compiled_rules:
            matches = list(regex.finditer(result))
            if matches:
                # Capture what was actually heard
                heard_sample = matches[0].group(0)
                result = regex.sub(replacement, result)
                applied.append({
                    "from": heard_sample,
                    "to": replacement,
                    "count": len(matches),
                    "rule": trigger,
                })

        return result, applied
