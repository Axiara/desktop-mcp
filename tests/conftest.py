"""Shared test fixtures for desktop-mcp tests."""

from __future__ import annotations

import pytest

from desktop_mcp.models import (
    ElementNode,
    Rect,
    WindowInfo,
)


@pytest.fixture
def sample_window_info() -> WindowInfo:
    return WindowInfo(
        hwnd=12345,
        title="Test Window",
        class_name="TestClass",
        pid=1000,
        rect=Rect(x=100, y=100, width=800, height=600),
        is_visible=True,
        is_minimized=False,
        is_maximized=False,
    )


@pytest.fixture
def sample_element_tree() -> ElementNode:
    return ElementNode(
        name="Main Window",
        control_type="Window",
        automation_id="MainWindow",
        rect=Rect(x=0, y=0, width=800, height=600),
        children=[
            ElementNode(
                name="File",
                control_type="MenuItem",
                automation_id="FileMenu",
                rect=Rect(x=0, y=0, width=50, height=25),
                patterns=["Invoke"],
            ),
            ElementNode(
                name="Editor",
                control_type="Edit",
                automation_id="MainEditor",
                rect=Rect(x=0, y=25, width=800, height=550),
                value="Hello World",
                patterns=["Value"],
            ),
            ElementNode(
                name="Save",
                control_type="Button",
                automation_id="SaveButton",
                rect=Rect(x=700, y=575, width=80, height=25),
                patterns=["Invoke"],
            ),
        ],
    )


@pytest.fixture
def sample_rect() -> Rect:
    return Rect(x=100, y=200, width=300, height=400)
