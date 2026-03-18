"""Tests for the input module (mocked pyautogui)."""

from unittest.mock import patch, MagicMock

import pytest

from desktop_mcp import safety


@pytest.fixture(autouse=True)
def reset_safety():
    safety.resume()
    safety.clear_action_log()
    original = safety.ACTION_DELAY_MS
    safety.ACTION_DELAY_MS = 0
    yield
    safety.ACTION_DELAY_MS = original
    safety.resume()
    safety.clear_action_log()


class TestClick:
    @patch("desktop_mcp.input.pyautogui")
    def test_single_click(self, mock_pag):
        from desktop_mcp.input import click
        click(100, 200)
        mock_pag.click.assert_called_once_with(x=100, y=200, button="left", clicks=1)

    @patch("desktop_mcp.input.pyautogui")
    def test_double_click(self, mock_pag):
        from desktop_mcp.input import click
        click(50, 75, button="left", clicks=2)
        mock_pag.click.assert_called_once_with(x=50, y=75, button="left", clicks=2)

    @patch("desktop_mcp.input.pyautogui")
    def test_right_click(self, mock_pag):
        from desktop_mcp.input import click
        click(0, 0, button="right")
        mock_pag.click.assert_called_once_with(x=0, y=0, button="right", clicks=1)

    @patch("desktop_mcp.input.pyautogui")
    def test_click_logs_action(self, mock_pag):
        from desktop_mcp.input import click
        click(100, 200)
        log = safety.get_action_log()
        assert len(log) == 1
        assert log[0].action == "click"

    @patch("desktop_mcp.input.pyautogui")
    def test_click_blocked_when_paused(self, mock_pag):
        from desktop_mcp.input import click
        safety.pause()
        with pytest.raises(safety.AutomationPausedError):
            click(100, 200)
        mock_pag.click.assert_not_called()


class TestTypeText:
    @patch("desktop_mcp.input.pyautogui")
    def test_type_short_ascii(self, mock_pag):
        from desktop_mcp.input import type_text
        type_text("hi", use_clipboard=False)
        mock_pag.typewrite.assert_called_once()

    @patch("desktop_mcp.input.pyautogui")
    @patch("desktop_mcp.input.win32clipboard", create=True)
    def test_type_long_text_uses_clipboard(self, mock_clip, mock_pag):
        from desktop_mcp.input import type_text
        # Patch win32clipboard at the module level for _paste_text
        import desktop_mcp.input as inp_mod
        mock_wc = MagicMock()
        with patch.dict("sys.modules", {"win32clipboard": mock_wc}):
            type_text("x" * 100, use_clipboard=True)
        mock_pag.hotkey.assert_called_with("ctrl", "v")

    @patch("desktop_mcp.input.pyautogui")
    def test_type_logs_action(self, mock_pag):
        from desktop_mcp.input import type_text
        type_text("test", use_clipboard=False)
        log = safety.get_action_log()
        assert len(log) == 1
        assert log[0].action == "type_text"


class TestPressKeys:
    @patch("desktop_mcp.input.pyautogui")
    def test_single_key(self, mock_pag):
        from desktop_mcp.input import press_keys
        press_keys("enter")
        mock_pag.hotkey.assert_called_once_with("enter")

    @patch("desktop_mcp.input.pyautogui")
    def test_combo(self, mock_pag):
        from desktop_mcp.input import press_keys
        press_keys("ctrl", "s")
        mock_pag.hotkey.assert_called_once_with("ctrl", "s")


class TestMouseMove:
    @patch("desktop_mcp.input.pyautogui")
    def test_move(self, mock_pag):
        from desktop_mcp.input import mouse_move
        mouse_move(500, 300, duration=0.0)
        mock_pag.moveTo.assert_called_once_with(x=500, y=300, duration=0.0)


class TestScroll:
    @patch("desktop_mcp.input.pyautogui")
    def test_scroll_up(self, mock_pag):
        from desktop_mcp.input import scroll
        scroll(3, x=100, y=200)
        mock_pag.scroll.assert_called_once_with(3, x=100, y=200)


class TestGetCursorPosition:
    @patch("desktop_mcp.input.pyautogui")
    def test_get_position(self, mock_pag):
        from desktop_mcp.input import get_cursor_position
        mock_pag.position.return_value = MagicMock(x=500, y=300)
        x, y = get_cursor_position()
        assert x == 500
        assert y == 300
