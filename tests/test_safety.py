"""Tests for the safety module."""

import pytest

from desktop_mcp import safety
from desktop_mcp.safety import AutomationPausedError


@pytest.fixture(autouse=True)
def reset_safety():
    """Ensure safety state is clean for each test."""
    safety.resume()
    safety.clear_action_log()
    yield
    safety.resume()
    safety.clear_action_log()


class TestPauseResume:
    def test_initially_not_paused(self):
        assert safety.is_paused() is False

    def test_pause(self):
        safety.pause()
        assert safety.is_paused() is True

    def test_resume(self):
        safety.pause()
        safety.resume()
        assert safety.is_paused() is False

    def test_pre_action_raises_when_paused(self):
        safety.pause()
        with pytest.raises(AutomationPausedError, match="paused"):
            safety.pre_action("click", {"x": 0, "y": 0})

    def test_pre_action_succeeds_when_not_paused(self, monkeypatch):
        monkeypatch.setattr(safety, "ACTION_DELAY_MS", 0)
        safety.pre_action("click", {"x": 0, "y": 0})


class TestActionLog:
    def test_log_records_actions(self, monkeypatch):
        monkeypatch.setattr(safety, "ACTION_DELAY_MS", 0)
        safety.pre_action("click", {"x": 10, "y": 20})
        safety.pre_action("type_text", {"text": "hi"})

        log = safety.get_action_log()
        assert len(log) == 2
        assert log[0].action == "click"
        assert log[1].action == "type_text"

    def test_log_respects_last_n(self, monkeypatch):
        monkeypatch.setattr(safety, "ACTION_DELAY_MS", 0)
        for i in range(10):
            safety.pre_action(f"action_{i}")

        log = safety.get_action_log(last_n=3)
        assert len(log) == 3
        assert log[0].action == "action_7"

    def test_clear_log(self, monkeypatch):
        monkeypatch.setattr(safety, "ACTION_DELAY_MS", 0)
        safety.pre_action("click")
        safety.clear_action_log()
        assert len(safety.get_action_log()) == 0
