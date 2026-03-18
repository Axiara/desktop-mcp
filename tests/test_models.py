"""Tests for Pydantic models."""

from desktop_mcp.models import (
    ActionRecord,
    CompareResult,
    ElementNode,
    Rect,
    WindowInfo,
)


class TestRect:
    def test_create(self):
        r = Rect(x=10, y=20, width=100, height=200)
        assert r.x == 10
        assert r.y == 20
        assert r.width == 100
        assert r.height == 200

    def test_serialization(self):
        r = Rect(x=0, y=0, width=1920, height=1080)
        d = r.model_dump()
        assert d == {"x": 0, "y": 0, "width": 1920, "height": 1080}


class TestWindowInfo:
    def test_create(self, sample_window_info):
        assert sample_window_info.hwnd == 12345
        assert sample_window_info.title == "Test Window"
        assert sample_window_info.is_visible is True

    def test_serialization(self, sample_window_info):
        d = sample_window_info.model_dump()
        assert d["hwnd"] == 12345
        assert d["rect"]["width"] == 800


class TestElementNode:
    def test_nested_tree(self, sample_element_tree):
        assert sample_element_tree.name == "Main Window"
        assert len(sample_element_tree.children) == 3
        assert sample_element_tree.children[0].name == "File"
        assert sample_element_tree.children[1].value == "Hello World"

    def test_empty_defaults(self):
        node = ElementNode()
        assert node.name == ""
        assert node.children == []
        assert node.patterns == []
        assert node.value is None


class TestCompareResult:
    def test_no_diff(self):
        r = CompareResult(diff_percentage=0.0, changed_region=None)
        assert r.diff_percentage == 0.0
        assert r.changed_region is None

    def test_with_diff(self):
        r = CompareResult(
            diff_percentage=5.5,
            changed_region=Rect(x=10, y=10, width=50, height=30),
        )
        assert r.diff_percentage == 5.5
        assert r.changed_region.width == 50


class TestActionRecord:
    def test_create(self):
        r = ActionRecord(action="click", params={"x": 100, "y": 200})
        assert r.action == "click"
        assert r.params["x"] == 100
        assert r.timestamp is not None
