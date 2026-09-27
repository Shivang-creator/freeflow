"""Unit tests for FreeFlow Dictation Engine components."""

import tempfile
from pathlib import Path

from freeflow.cleaner import RuleCleaner
from freeflow.config import AppConfig, ConfigManager
from freeflow.dictionary import DictionaryManager
from freeflow.history import HistoryManager


def test_rule_cleaner_fillers():
    cleaner = RuleCleaner()
    text = "um, so basically uh we are launching the product"
    res = cleaner.clean(text)
    assert "um" not in res.lower()
    assert "uh" not in res.lower()
    assert "launching the product" in res


def test_rule_cleaner_stutters():
    cleaner = RuleCleaner()
    text = "the the issue was resolved"
    res = cleaner.clean(text)
    assert "the the" not in res.lower()
    assert "The issue was resolved." == res


def test_rule_cleaner_spoken_punctuation():
    cleaner = RuleCleaner()
    text = "hello world new paragraph this is item one question mark"
    res = cleaner.clean(text)
    assert "\n" in res
    assert "?" in res


def test_dictionary_longest_match_and_glued_words():
    with tempfile.NamedTemporaryFile(suffix=".json") as f:
        tmp_path = Path(f.name)
        mgr = DictionaryManager(dict_path=tmp_path)
        mgr.add_word("FreeFlow")
        mgr.add_correction("cloud code", "Claude Code")
        mgr.add_correction("visval floor", "FreeFlow")

        # Test acoustic prompt
        prompt = mgr.get_initial_prompt()
        assert "FreeFlow" in prompt

        # Test glued word replacement: "cloud code" vs "cloudcode"
        text1, _ = mgr.apply_corrections("I was testing cloud code today")
        assert "Claude Code" in text1

        text2, _ = mgr.apply_corrections("visval floor is blazing fast")
        assert "FreeFlow" in text2


def test_history_manager():
    with tempfile.NamedTemporaryFile(suffix=".json") as f:
        tmp_path = Path(f.name)
        hist = HistoryManager(history_path=tmp_path)
        entry = hist.add_entry(
            text="Hello world test dictation",
            raw_text="hello world test dictation",
            app_name="VS Code",
            mode="code",
            duration_s=2.3,
            model_name="Turbo",
        )
        assert entry.id is not None
        assert entry.word_count == 4
        assert len(hist.get_recent()) == 1

        # Search query
        found = hist.get_recent(query="test")
        assert len(found) == 1
        not_found = hist.get_recent(query="nonexistent")
        assert len(not_found) == 0

        # Delete
        hist.delete_entry(entry.id)
        assert len(hist.get_recent()) == 0


def test_config_manager():
    with tempfile.NamedTemporaryFile(suffix=".json") as f:
        tmp_path = Path(f.name)
        cfg_mgr = ConfigManager(config_path=tmp_path)
        assert cfg_mgr.config.hotkey == "alt_r"

        cfg_mgr.update(hotkey="f8", enable_slm=False)
        assert cfg_mgr.config.hotkey == "f8"
        assert cfg_mgr.config.enable_slm is False

        # Reload from disk
        cfg_mgr2 = ConfigManager(config_path=tmp_path)
        assert cfg_mgr2.config.hotkey == "f8"
        assert cfg_mgr2.config.enable_slm is False


if __name__ == "__main__":
    test_rule_cleaner_fillers()
    test_rule_cleaner_stutters()
    test_rule_cleaner_spoken_punctuation()
    test_dictionary_longest_match_and_glued_words()
    test_history_manager()
    test_config_manager()
    print("✅ All FreeFlow core tests passed successfully!")
