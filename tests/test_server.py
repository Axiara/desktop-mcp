"""Tests for MCP server tool functions."""

import json
from unittest.mock import patch, MagicMock

import pytest

from desktop_mcp.models import Rect, WindowInfo, ElementNode, ElementInfo


class TestCompactTree:
    def test_removes_empty_fields(self):
        from desktop_mcp.server import _compact_tree
        node = {
            "name": "", "control_type": "Pane", "automation_id": "",
            "class_name": "", "rect": {"x": 0, "y": 0, "width": 100, "height": 50},
            "is_enabled": True, "value": None, "patterns": [], "children": [],
        }
        result = _compact_tree(node)
        assert "name" not in result
        assert result["type"] == "Pane"
        assert result["rect"] == [0, 0, 100, 50]
        assert "patterns" not in result
        assert "children" not in result

    def test_keeps_meaningful_fields(self):
        from desktop_mcp.server import _compact_tree
        node = {
            "name": "Save", "control_type": "Button", "automation_id": "btnSave",
            "class_name": "Button", "rect": {"x": 10, "y": 20, "width": 80, "height": 30},
            "is_enabled": False, "value": None, "patterns": ["Invoke"], "children": [],
        }
        result = _compact_tree(node)
        assert result["name"] == "Save"
        assert result["type"] == "Button"
        assert result["id"] == "btnSave"
        assert result["enabled"] is False
        assert result["patterns"] == ["Invoke"]

    def test_recursive_children(self):
        from desktop_mcp.server import _compact_tree
        node = {
            "name": "Window", "control_type": "Window", "automation_id": "",
            "class_name": "", "rect": None, "is_enabled": True, "value": None,
            "patterns": [],
            "children": [{
                "name": "OK", "control_type": "Button", "automation_id": "okBtn",
                "class_name": "", "rect": {"x": 0, "y": 0, "width": 50, "height": 25},
                "is_enabled": True, "value": None, "patterns": ["Invoke"], "children": [],
            }],
        }
        result = _compact_tree(node)
        assert len(result["children"]) == 1
        assert result["children"][0]["name"] == "OK"


class TestResolveHwnd:
    def test_direct_hwnd(self):
        from desktop_mcp.server import _resolve_hwnd
        assert _resolve_hwnd(None, 12345) == 12345

    def test_no_args_raises(self):
        from desktop_mcp.server import _resolve_hwnd
        with pytest.raises(ValueError, match="Must provide"):
            _resolve_hwnd(None, None)

    @patch("desktop_mcp.uia.find_window_by_title", return_value=None)
    def test_title_not_found_raises(self, mock_find):
        from desktop_mcp.server import _resolve_hwnd
        with pytest.raises(ValueError, match="No window found"):
            _resolve_hwnd("nonexistent", None)


class TestAutoFocus:
    def test_no_window_returns_none(self):
        from desktop_mcp.server import _auto_focus
        assert _auto_focus(None, None) is None

    @patch("desktop_mcp.uia.focus_window", return_value=True)
    def test_focuses_by_hwnd(self, mock_focus):
        from desktop_mcp.server import _auto_focus
        result = _auto_focus(None, 12345)
        assert result == 12345
        mock_focus.assert_called_once_with(12345)


class TestClickTool:
    def test_click_no_coords_or_element(self):
        from desktop_mcp.server import click
        result = json.loads(click())
        assert "error" in result

    @patch("desktop_mcp.input.pyautogui")
    def test_click_with_coords(self, mock_pag, monkeypatch):
        import desktop_mcp.safety as s
        monkeypatch.setattr(s, "ACTION_DELAY_MS", 0)
        from desktop_mcp.server import click
        result = json.loads(click(x=100, y=200))
        assert result["clicked"]["x"] == 100
        assert result["clicked"]["y"] == 200


class TestTypeTextTool:
    @patch("desktop_mcp.input.pyautogui")
    def test_type_returns_info(self, mock_pag, monkeypatch):
        import desktop_mcp.safety as s
        monkeypatch.setattr(s, "ACTION_DELAY_MS", 0)
        from desktop_mcp.server import type_text
        result = json.loads(type_text("hello world", use_clipboard=False))
        assert result["typed"] == 11
        assert "hello" in result["text_preview"]


class TestPressKeysTool:
    @patch("desktop_mcp.input.pyautogui")
    def test_press_combo(self, mock_pag, monkeypatch):
        import desktop_mcp.safety as s
        monkeypatch.setattr(s, "ACTION_DELAY_MS", 0)
        from desktop_mcp.server import press_keys
        result = json.loads(press_keys("ctrl+s"))
        assert result["pressed"] == "ctrl+s"

    @patch("desktop_mcp.input.pyautogui")
    @patch("desktop_mcp.uia.focus_window", return_value=True)
    def test_press_with_auto_focus(self, mock_focus, mock_pag, monkeypatch):
        import desktop_mcp.safety as s
        monkeypatch.setattr(s, "ACTION_DELAY_MS", 0)
        from desktop_mcp.server import press_keys
        result = json.loads(press_keys("ctrl+n", hwnd=12345))
        assert result["pressed"] == "ctrl+n"
        mock_focus.assert_called_once_with(12345)
