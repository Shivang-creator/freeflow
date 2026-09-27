"""freeflow/history.py — Persistent Transcription & Clipboard History for FreeFlow."""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

from freeflow.constants import HISTORY_FILE

log = logging.getLogger("freeflow.history")


@dataclass
class HistoryEntry:
    id: str
    timestamp: float
    iso_time: str
    text: str
    raw_text: str
    app_name: str
    mode: str
    duration_s: float
    model_name: str
    char_count: int
    word_count: int

    @classmethod
    def create(
        cls,
        text: str,
        raw_text: str = "",
        app_name: str = "General",
        mode: str = "general",
        duration_s: float = 0.0,
        model_name: str = "Turbo",
    ) -> HistoryEntry:
        now = time.time()
        iso = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
        clean_text = text.strip()
        return cls(
            id=str(uuid.uuid4())[:8],
            timestamp=now,
            iso_time=iso,
            text=clean_text,
            raw_text=(raw_text or clean_text).strip(),
            app_name=app_name or "General",
            mode=mode or "general",
            duration_s=round(duration_s, 2),
            model_name=model_name,
            char_count=len(clean_text),
            word_count=len(clean_text.split()) if clean_text else 0,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HistoryEntry:
        known_fields = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)


class HistoryManager:
    """Thread-safe persistent store for dictation clipboard history."""

    def __init__(self, history_path: Optional[Path] = None, max_entries: int = 500) -> None:
        self.history_path = history_path or HISTORY_FILE
        self.max_entries = max_entries
        self._lock = threading.Lock()
        self.entries: list[HistoryEntry] = []
        self.load()

    def load(self) -> list[HistoryEntry]:
        with self._lock:
            if not self.history_path.exists():
                self.entries = []
                return self.entries

            try:
                with open(self.history_path, "r", encoding="utf-8") as f:
                    raw_list = json.load(f)
                self.entries = [HistoryEntry.from_dict(item) for item in raw_list if isinstance(item, dict)]
                log.info("Loaded %d history entries from %s", len(self.entries), self.history_path)
            except Exception as e:
                log.warning("Failed to load history from %s (%s). Starting fresh.", self.history_path, e)
                self.entries = []
            return self.entries

    def _save_unlocked(self) -> None:
        try:
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            data = [e.to_dict() for e in self.entries[: self.max_entries]]
            with open(self.history_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log.error("Failed to write history to %s: %s", self.history_path, e)

    def add_entry(
        self,
        text: str,
        raw_text: str = "",
        app_name: str = "General",
        mode: str = "general",
        duration_s: float = 0.0,
        model_name: str = "Turbo",
    ) -> HistoryEntry:
        if not text.strip():
            return None  # type: ignore

        entry = HistoryEntry.create(
            text=text,
            raw_text=raw_text,
            app_name=app_name,
            mode=mode,
            duration_s=duration_s,
            model_name=model_name,
        )

        with self._lock:
            # Prepend newest entry to the top
            self.entries.insert(0, entry)
            if len(self.entries) > self.max_entries:
                self.entries = self.entries[: self.max_entries]
            self._save_unlocked()

        log.info("Appended history entry [%s]: %d chars into %s", entry.id, len(entry.text), entry.app_name)
        return entry

    def get_recent(self, limit: int = 50, query: str = "") -> list[dict[str, Any]]:
        with self._lock:
            items = self.entries
            if query.strip():
                q = query.lower()
                items = [
                    e for e in items
                    if q in e.text.lower() or q in e.app_name.lower() or q in e.mode.lower()
                ]
            return [e.to_dict() for e in items[:limit]]

    def get_entry(self, entry_id: str) -> Optional[HistoryEntry]:
        with self._lock:
            for e in self.entries:
                if e.id == entry_id:
                    return e
        return None

    def delete_entry(self, entry_id: str) -> bool:
        with self._lock:
            before_len = len(self.entries)
            self.entries = [e for e in self.entries if e.id != entry_id]
            if len(self.entries) < before_len:
                self._save_unlocked()
                return True
        return False

    def clear(self) -> None:
        with self._lock:
            self.entries = []
            self._save_unlocked()
        log.info("Cleared all dictation history.")
