"""Tests for the Scryfall client's retry behaviour.

Only the retry/backoff logic is tested here — it's real logic that decides
whether an unattended run survives a transient blip. The HTTP call itself is
stubbed; asserting that a mock returns what it was told to isn't worth a test.
"""

import pytest
import requests

from mtg2anki import scryfall


class FakeResponse:
    def __init__(self, payload=None):
        self._payload = payload or {}

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def patch_get(monkeypatch, side_effects):
    """Stub requests.get with a scripted sequence of results/exceptions."""
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        result = side_effects[len(calls) - 1]
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(scryfall.requests, "get", fake_get)
    return calls


class TestScryfallGet:
    def test_returns_response_on_success(self, monkeypatch):
        expected = FakeResponse({"ok": True})
        calls = patch_get(monkeypatch, [expected])

        result = scryfall.scryfall_get("https://example.test", log=lambda m: None, sleep=lambda s: None)

        assert result is expected
        assert len(calls) == 1

    def test_retries_then_succeeds(self, monkeypatch):
        expected = FakeResponse()
        calls = patch_get(monkeypatch, [
            requests.exceptions.ConnectionError("boom"),
            requests.exceptions.ConnectionError("boom"),
            expected,
        ])

        result = scryfall.scryfall_get("https://example.test", log=lambda m: None, sleep=lambda s: None)

        assert result is expected
        assert len(calls) == 3

    def test_raises_after_final_attempt(self, monkeypatch):
        calls = patch_get(monkeypatch, [requests.exceptions.ConnectionError("boom")] * 4)

        with pytest.raises(requests.exceptions.ConnectionError):
            scryfall.scryfall_get("https://example.test", log=lambda m: None, sleep=lambda s: None)

        assert len(calls) == 4, "should stop after `attempts` tries"

    def test_backoff_doubles_between_retries(self, monkeypatch):
        patch_get(monkeypatch, [requests.exceptions.ConnectionError("boom")] * 4)
        delays = []

        with pytest.raises(requests.exceptions.ConnectionError):
            scryfall.scryfall_get(
                "https://example.test", log=lambda m: None, sleep=delays.append
            )

        assert delays == [2, 4, 8]

    def test_sends_required_headers(self, monkeypatch):
        """Scryfall 400s on requests without a User-Agent/Accept pair."""
        seen = {}

        def fake_get(url, **kwargs):
            seen.update(kwargs)
            return FakeResponse()

        monkeypatch.setattr(scryfall.requests, "get", fake_get)
        scryfall.scryfall_get("https://example.test", log=lambda m: None, sleep=lambda s: None)

        assert "User-Agent" in seen["headers"]
        assert "Accept" in seen["headers"]
        assert seen["timeout"] > 0, "a missing timeout can hang the scheduled run"


class TestFetchSetInfo:
    def test_extracts_the_fields_callers_use(self, monkeypatch):
        monkeypatch.setattr(
            scryfall,
            "scryfall_get",
            lambda url, log=None: FakeResponse(
                {"code": "fra", "name": "Reality Fracture", "released_at": "2026-09-26"}
            ),
        )

        info = scryfall.fetch_set_info("fra")

        assert info == {
            "code": "fra",
            "name": "Reality Fracture",
            "released_at": "2026-09-26",
        }

    def test_defaults_missing_release_date(self, monkeypatch):
        monkeypatch.setattr(
            scryfall,
            "scryfall_get",
            lambda url, log=None: FakeResponse({"code": "xyz", "name": "Unreleased Set"}),
        )

        assert scryfall.fetch_set_info("xyz")["released_at"] == "Unknown"
