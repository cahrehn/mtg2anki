"""Tests for config.toml handling.

A wrong set code here is expensive: the importer would write into the wrong
deck, and lowwinrate.py --delete would evaluate the wrong deck for deletion.
Every unusable config must raise rather than fall back to a default.
"""

import pytest

from mtg2anki.config import ConfigError, resolve_set_code, state_file


def write_config(tmp_path, contents):
    path = tmp_path / "config.toml"
    path.write_text(contents)
    return path


class TestResolveSetCode:
    def test_reads_the_set_code(self, tmp_path):
        path = write_config(tmp_path, 'set = "fra"\n')
        assert resolve_set_code(path) == "fra"

    def test_lowercases_and_strips(self, tmp_path):
        path = write_config(tmp_path, 'set = "  HOB  "\n')
        assert resolve_set_code(path) == "hob"

    def test_ignores_other_keys(self, tmp_path):
        path = write_config(tmp_path, 'set = "fra"\nunrelated = 3\n')
        assert resolve_set_code(path) == "fra"

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(ConfigError, match="not found"):
            resolve_set_code(tmp_path / "config.toml")

    def test_malformed_toml_raises(self, tmp_path):
        path = write_config(tmp_path, 'set = "unclosed\n')
        with pytest.raises(ConfigError, match="Could not read"):
            resolve_set_code(path)

    def test_missing_set_key_raises(self, tmp_path):
        path = write_config(tmp_path, 'other = "thing"\n')
        with pytest.raises(ConfigError, match="non-empty"):
            resolve_set_code(path)

    def test_empty_set_raises(self, tmp_path):
        path = write_config(tmp_path, 'set = ""\n')
        with pytest.raises(ConfigError, match="non-empty"):
            resolve_set_code(path)

    def test_whitespace_only_set_raises(self, tmp_path):
        path = write_config(tmp_path, 'set = "   "\n')
        with pytest.raises(ConfigError, match="non-empty"):
            resolve_set_code(path)

    def test_non_string_set_raises(self, tmp_path):
        path = write_config(tmp_path, "set = 42\n")
        with pytest.raises(ConfigError, match="non-empty"):
            resolve_set_code(path)


class TestStateFile:
    def test_names_the_file_after_the_set(self):
        assert state_file("fra").name == "fra_state.json"

    def test_sets_get_separate_state_files(self):
        assert state_file("fra") != state_file("hob")
