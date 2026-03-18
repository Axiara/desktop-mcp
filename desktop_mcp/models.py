"""Pydantic models for desktop-mcp tool inputs and outputs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Rect(BaseModel):
    """Screen rectangle."""

    x: int
    y: int
    width: int
    height: int


class WindowInfo(BaseModel):
    """Information about a top-level window."""

    hwnd: int
    title: str
    class_name: str
    pid: int
    rect: Rect
    is_visible: bool
    is_minimized: bool
    is_maximized: bool


class ElementNode(BaseModel):
    """A node in the UI Automation element tree."""

    name: str = ""
    control_type: str = ""
    automation_id: str = ""
    class_name: str = ""
    rect: Rect | None = None
    is_enabled: bool = True
    value: str | None = None
    patterns: list[str] = Field(default_factory=list)
    children: list[ElementNode] = Field(default_factory=list)


class ElementInfo(BaseModel):
    """Detailed information about a single UI element."""

    name: str = ""
    control_type: str = ""
    automation_id: str = ""
    class_name: str = ""
    rect: Rect | None = None
    is_enabled: bool = True
    is_offscreen: bool = False
    value: str | None = None
    patterns: list[str] = Field(default_factory=list)
    hwnd: int = 0


class OcrLine(BaseModel):
    """A line of text extracted by OCR."""

    text: str
    bounding_box: Rect


class CompareResult(BaseModel):
    """Result of comparing two screen captures."""

    diff_percentage: float
    changed_region: Rect | None = None


class MonitorInfo(BaseModel):
    """Information about a display monitor."""

    index: int
    x: int
    y: int
    width: int
    height: int
    is_primary: bool = False


class DisplayInfo(BaseModel):
    """Information about the display configuration."""

    monitor_count: int
    monitors: list[MonitorInfo]


class ActionRecord(BaseModel):
    """Record of an action performed by the automation."""

    action: str
    params: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
