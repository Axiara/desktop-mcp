"""Integration tests that interact with real Windows desktop.

These tests are marked as slow and require a live desktop session.
Run with: pytest -m slow
"""

import json

import pytest

pytestmark = pytest.mark.slow


class TestListWindowsLive:
    def test_lists_real_windows(self):
        from desktop_mcp.uia import list_windows

        windows = list_windows()
        assert len(windows) > 0
        # Should find at least one window with a title
        titled = [w for w in windows if w.title]
        assert len(titled) > 0

    def test_window_has_valid_rect(self):
        from desktop_mcp.uia import list_windows

        windows = list_windows()
        for w in windows[:5]:  # Check first 5
            assert w.rect.width >= 0
            assert w.rect.height >= 0


class TestCaptureScreenLive:
    def test_capture_full_screen(self):
        from desktop_mcp.capture import capture_region

        b64, w, h = capture_region(max_width=640)
        assert len(b64) > 100  # Should have image data
        assert w <= 640
        assert h > 0


class TestGetWindowTreeLive:
    def test_get_desktop_tree(self):
        """Get the tree of any visible window."""
        from desktop_mcp.uia import list_windows, get_window_tree

        windows = list_windows()
        if not windows:
            pytest.skip("No windows available")

        # Use the first window with a title
        win = windows[0]
        tree = get_window_tree(win.hwnd, max_depth=1)
        assert tree.control_type != ""


class TestServerToolsLive:
    def test_list_windows_tool(self):
        from desktop_mcp.server import list_windows

        result = json.loads(list_windows())
        assert isinstance(result, list)
        assert len(result) > 0
        assert "title" in result[0]
        assert "hwnd" in result[0]

    def test_get_display_info(self):
        from desktop_mcp.server import get_display_info

        result = json.loads(get_display_info())
        assert result["monitor_count"] >= 1
        assert len(result["monitors"]) >= 1
        assert result["monitors"][0]["width"] > 0

    def test_get_cursor_position(self):
        from desktop_mcp.server import get_cursor_position

        result = json.loads(get_cursor_position())
        assert "x" in result
        assert "y" in result
