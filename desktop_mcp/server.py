"""MCP server for Windows desktop automation."""

from __future__ import annotations

import base64
import io
import json
import subprocess
import time
from typing import Any

from mcp.server.fastmcp import FastMCP
from PIL import Image

from . import safety
from .models import Rect

mcp = FastMCP(
    "desktop-mcp",
    instructions="Windows desktop automation — gives AI agents eyes and hands on the desktop",
)


# ═══════════════════════════════════════════════════════════════════════════
# Observation Tools
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
def list_windows(include_invisible: bool = False) -> str:
    """List all visible top-level windows.

    Returns structured JSON with title, handle, bounds, process ID, and
    window state for each window. This is the fastest way to discover
    what's on screen.

    Args:
        include_invisible: If True, also list hidden/background windows.
    """
    from .uia import list_windows as _list_windows

    windows = _list_windows(include_invisible=include_invisible)
    return json.dumps(
        [w.model_dump() for w in windows],
        indent=2,
    )


@mcp.tool()
def get_window_tree(
    window_title: str | None = None,
    hwnd: int | None = None,
    max_depth: int = 3,
) -> str:
    """Get the UI Automation element tree for a window as structured JSON.

    This is the PRIMARY observation tool — prefer this over screenshots.
    Returns control type, name, automation ID, bounds, enabled state,
    value, and available interaction patterns for each element.

    Use max_depth to control detail level (1=shallow/fast, 5=deep/verbose).

    Args:
        window_title: Partial window title to find (case-insensitive).
        hwnd: Window handle (use instead of title if known).
        max_depth: How deep to traverse the element tree (default 3).
    """
    from .uia import get_window_tree as _get_tree, find_window_by_title

    hwnd = _resolve_hwnd(window_title, hwnd)
    tree = _get_tree(hwnd, max_depth=max_depth)
    return json.dumps(_compact_tree(tree.model_dump()), indent=2)


@mcp.tool()
def get_element_info(
    window_title: str | None = None,
    hwnd: int | None = None,
    automation_id: str | None = None,
    name: str | None = None,
) -> str:
    """Get detailed info about a specific UI element by automation ID or name.

    Returns a single element's properties as JSON — much cheaper than a
    full window tree when you know what you're looking for.

    Args:
        window_title: Partial window title to search within.
        hwnd: Window handle to search within.
        automation_id: The element's automation ID.
        name: The element's name/label text.
    """
    from .uia import get_element_info as _get_info

    hwnd = _resolve_hwnd(window_title, hwnd)
    info = _get_info(hwnd, automation_id=automation_id, name=name)
    if info is None:
        return json.dumps({"error": "Element not found"})
    return json.dumps(info.model_dump(), indent=2)


@mcp.tool()
def find_element(
    window_title: str | None = None,
    hwnd: int | None = None,
    name: str | None = None,
    control_type: str | None = None,
    automation_id: str | None = None,
) -> str:
    """Search for UI elements matching criteria within a window.

    Returns a list of matching elements with their bounds, so you can
    locate buttons, text fields, etc. by name or type.

    Args:
        window_title: Partial window title to search within.
        hwnd: Window handle to search within.
        name: Element name/label to match.
        control_type: Control type (e.g., "Button", "Edit", "CheckBox").
        automation_id: Automation ID to match.
    """
    from .uia import find_elements

    hwnd = _resolve_hwnd(window_title, hwnd)
    elements = find_elements(hwnd, name=name, control_type=control_type, automation_id=automation_id)
    return json.dumps([e.model_dump() for e in elements], indent=2)


@mcp.tool()
def capture_screen(
    region_x: int | None = None,
    region_y: int | None = None,
    region_width: int | None = None,
    region_height: int | None = None,
    monitor_index: int = 0,
    max_width: int = 1280,
    format: str = "png",
    quality: int = 75,
) -> list[dict]:
    """Capture the screen or a specific region as an image.

    Prefer get_window_tree for understanding UI structure. Use this only
    when you need to see visual content (images, charts, colors, layout).

    Args:
        region_x: Left edge of capture region.
        region_y: Top edge of capture region.
        region_width: Width of capture region.
        region_height: Height of capture region.
        monitor_index: Monitor to capture (0=all, 1+=specific).
        max_width: Max image width in pixels (downscales if larger).
        format: Image format — "png" or "jpeg".
        quality: JPEG quality 1-100 (ignored for PNG).
    """
    from .capture import capture_region

    region = None
    if all(v is not None for v in [region_x, region_y, region_width, region_height]):
        region = Rect(x=region_x, y=region_y, width=region_width, height=region_height)

    b64, w, h = capture_region(
        region=region, monitor_index=monitor_index,
        max_width=max_width, format=format, quality=quality,
    )

    mime = "image/png" if format.lower() == "png" else "image/jpeg"
    return [
        {"type": "text", "text": json.dumps({"width": w, "height": h, "format": format})},
        {"type": "image", "data": b64, "mimeType": mime},
    ]


@mcp.tool()
def capture_window(
    window_title: str | None = None,
    hwnd: int | None = None,
    max_width: int = 1280,
    format: str = "png",
    quality: int = 75,
) -> list[dict]:
    """Capture a specific window as an image.

    Auto-crops to the window's bounds. Prefer get_window_tree for
    understanding UI structure; use this for visual content only.

    Args:
        window_title: Partial window title (case-insensitive).
        hwnd: Window handle (use instead of title if known).
        max_width: Max image width in pixels.
        format: "png" or "jpeg".
        quality: JPEG quality 1-100.
    """
    from .capture import capture_window as _cap_win

    hwnd = _resolve_hwnd(window_title, hwnd)
    b64, w, h = _cap_win(hwnd, max_width=max_width, format=format, quality=quality)

    mime = "image/png" if format.lower() == "png" else "image/jpeg"
    return [
        {"type": "text", "text": json.dumps({"width": w, "height": h, "format": format, "hwnd": hwnd})},
        {"type": "image", "data": b64, "mimeType": mime},
    ]


@mcp.tool()
def read_screen_text(
    region_x: int | None = None,
    region_y: int | None = None,
    region_width: int | None = None,
    region_height: int | None = None,
    window_title: str | None = None,
    hwnd: int | None = None,
    language: str = "en",
) -> str:
    """Extract text from a screen region or window using OCR.

    Returns structured text with bounding boxes. Use this to read
    dialog messages, error text, status bars, or any on-screen text
    without consuming image tokens.

    Args:
        region_x: Left edge of region to OCR.
        region_y: Top edge.
        region_width: Width.
        region_height: Height.
        window_title: Window to OCR (captures and reads entire window).
        hwnd: Window handle to OCR.
        language: OCR language code (default "en").
    """
    from .ocr import read_screen_region_text, read_image_text
    from .capture import capture_window as _cap_win

    if window_title or hwnd:
        resolved = _resolve_hwnd(window_title, hwnd)
        from .uia import _get_rect
        rect = _get_rect(resolved)
        region = Rect(x=rect.x, y=rect.y, width=rect.width, height=rect.height)
        lines = read_screen_region_text(region=region, language=language)
    elif all(v is not None for v in [region_x, region_y, region_width, region_height]):
        region = Rect(x=region_x, y=region_y, width=region_width, height=region_height)
        lines = read_screen_region_text(region=region, language=language)
    else:
        lines = read_screen_region_text(language=language)

    return json.dumps([l.model_dump() for l in lines], indent=2)


@mcp.tool()
def get_cursor_position() -> str:
    """Get the current mouse cursor coordinates."""
    from .input import get_cursor_position as _get_pos

    x, y = _get_pos()
    return json.dumps({"x": x, "y": y})


@mcp.tool()
def get_clipboard() -> str:
    """Read the current clipboard contents (text only)."""
    try:
        import win32clipboard
        win32clipboard.OpenClipboard()
        try:
            text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
        except Exception:
            text = None
        finally:
            win32clipboard.CloseClipboard()
        return json.dumps({"text": text})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def wait_for_element(
    window_title: str | None = None,
    hwnd: int | None = None,
    name: str | None = None,
    automation_id: str | None = None,
    timeout_seconds: float = 10.0,
    poll_interval: float = 0.5,
    wait_until: str = "exists",
) -> str:
    """Wait for a UI element to appear, disappear, or change.

    Essential for waiting on dialogs, loading states, and async operations.

    Args:
        window_title: Window to search within.
        hwnd: Window handle.
        name: Element name to wait for.
        automation_id: Element automation ID to wait for.
        timeout_seconds: Max time to wait.
        poll_interval: Seconds between checks.
        wait_until: "exists" (appear) or "gone" (disappear).
    """
    from .uia import get_element_info as _get_info, find_window_by_title

    start = time.monotonic()
    while True:
        resolved = None
        try:
            resolved = _resolve_hwnd(window_title, hwnd)
        except ValueError:
            if wait_until == "gone":
                return json.dumps({"found": False, "elapsed": round(time.monotonic() - start, 2)})

        if resolved:
            info = _get_info(resolved, automation_id=automation_id, name=name)
            if wait_until == "exists" and info is not None:
                return json.dumps({
                    "found": True,
                    "element": info.model_dump(),
                    "elapsed": round(time.monotonic() - start, 2),
                })
            if wait_until == "gone" and info is None:
                return json.dumps({"found": False, "elapsed": round(time.monotonic() - start, 2)})

        if time.monotonic() - start > timeout_seconds:
            return json.dumps({
                "timeout": True,
                "elapsed": round(time.monotonic() - start, 2),
                "wait_until": wait_until,
            })

        time.sleep(poll_interval)


@mcp.tool()
def compare_captures(image1_b64: str, image2_b64: str) -> str:
    """Compare two captures and return what changed.

    Provide the base64 image data from two capture_screen/capture_window
    calls. Returns the percentage of pixels that changed and a bounding
    box around the changed region.

    Args:
        image1_b64: First image (base64 from a previous capture).
        image2_b64: Second image (base64 from a later capture).
    """
    from .capture import compare_captures as _compare

    result = _compare(image1_b64, image2_b64)
    return json.dumps(result.model_dump(), indent=2)


# ═══════════════════════════════════════════════════════════════════════════
# Interaction Tools
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
def click(
    x: int | None = None,
    y: int | None = None,
    button: str = "left",
    clicks: int = 1,
    window_title: str | None = None,
    hwnd: int | None = None,
    element_name: str | None = None,
    element_automation_id: str | None = None,
) -> str:
    """Click at coordinates or on a named UI element.

    You can specify coordinates directly, or provide a window + element
    identifier to auto-locate and click the element's center.

    Args:
        x: X screen coordinate.
        y: Y screen coordinate.
        button: "left", "right", or "middle".
        clicks: 1=single, 2=double, 3=triple click.
        window_title: Window containing the element.
        hwnd: Window handle containing the element.
        element_name: Click element with this name (finds center automatically).
        element_automation_id: Click element with this automation ID.
    """
    from . import input as inp
    from .uia import get_element_info as _get_info

    if (element_name or element_automation_id) and (window_title or hwnd):
        resolved = _resolve_hwnd(window_title, hwnd)
        info = _get_info(resolved, automation_id=element_automation_id, name=element_name)
        if info and info.rect:
            x = info.rect.x + info.rect.width // 2
            y = info.rect.y + info.rect.height // 2
        else:
            return json.dumps({"error": "Element not found", "element_name": element_name, "element_automation_id": element_automation_id})

    if x is None or y is None:
        return json.dumps({"error": "No coordinates or element specified"})

    inp.click(x=x, y=y, button=button, clicks=clicks)
    return json.dumps({"clicked": {"x": x, "y": y, "button": button, "clicks": clicks}})


@mcp.tool()
def type_text(
    text: str,
    interval: float = 0.02,
) -> str:
    """Type a text string. Types into whatever has focus.

    For typing into a specific field, first use click or focus_window
    to set focus, then type_text.

    Args:
        text: The text to type.
        interval: Seconds between keystrokes (default 0.02).
    """
    from . import input as inp

    inp.type_text(text=text, interval=interval)
    return json.dumps({"typed": len(text), "text_preview": text[:80]})


@mcp.tool()
def press_keys(keys: str) -> str:
    """Press a key combination (e.g., "ctrl+s", "alt+f4", "enter").

    Separate keys with "+". Common keys: ctrl, alt, shift, enter, tab,
    escape, space, backspace, delete, up, down, left, right, f1-f12.

    Args:
        keys: Key combination string like "ctrl+s" or single key like "enter".
    """
    from . import input as inp

    key_list = [k.strip() for k in keys.split("+")]
    inp.press_keys(*key_list)
    return json.dumps({"pressed": keys})


@mcp.tool()
def mouse_move(x: int, y: int, duration: float = 0.1) -> str:
    """Move the mouse cursor to coordinates.

    Args:
        x: Target X coordinate.
        y: Target Y coordinate.
        duration: Seconds for the movement (0 = instant).
    """
    from . import input as inp

    inp.mouse_move(x=x, y=y, duration=duration)
    return json.dumps({"moved_to": {"x": x, "y": y}})


@mcp.tool()
def mouse_drag(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    button: str = "left",
    duration: float = 0.3,
) -> str:
    """Drag from one point to another.

    Args:
        start_x: Starting X coordinate.
        start_y: Starting Y coordinate.
        end_x: Ending X coordinate.
        end_y: Ending Y coordinate.
        button: Mouse button to hold during drag.
        duration: Seconds for the drag motion.
    """
    from . import input as inp

    inp.mouse_drag(start_x=start_x, start_y=start_y, end_x=end_x, end_y=end_y, button=button, duration=duration)
    return json.dumps({"dragged": {"from": [start_x, start_y], "to": [end_x, end_y]}})


@mcp.tool()
def scroll(
    amount: int,
    x: int | None = None,
    y: int | None = None,
) -> str:
    """Scroll the mouse wheel.

    Args:
        amount: Scroll amount. Positive = up, negative = down.
        x: X coordinate to scroll at (None = current position).
        y: Y coordinate to scroll at (None = current position).
    """
    from . import input as inp

    inp.scroll(amount=amount, x=x, y=y)
    return json.dumps({"scrolled": amount, "at": {"x": x, "y": y}})


@mcp.tool()
def set_clipboard(text: str) -> str:
    """Set the clipboard contents.

    Args:
        text: Text to copy to clipboard.
    """
    try:
        import win32clipboard
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        return json.dumps({"set": True, "length": len(text)})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def focus_window(
    window_title: str | None = None,
    hwnd: int | None = None,
) -> str:
    """Bring a window to the foreground.

    Args:
        window_title: Partial window title (case-insensitive).
        hwnd: Window handle.
    """
    from .uia import focus_window as _focus

    resolved = _resolve_hwnd(window_title, hwnd)
    result = _focus(resolved)
    return json.dumps({"focused": result, "hwnd": resolved})


@mcp.tool()
def move_window(
    window_title: str | None = None,
    hwnd: int | None = None,
    x: int | None = None,
    y: int | None = None,
    width: int | None = None,
    height: int | None = None,
) -> str:
    """Reposition and/or resize a window.

    Args:
        window_title: Partial window title.
        hwnd: Window handle.
        x: New X position (None = keep current).
        y: New Y position (None = keep current).
        width: New width (None = keep current).
        height: New height (None = keep current).
    """
    import ctypes
    from .uia import _get_rect

    resolved = _resolve_hwnd(window_title, hwnd)
    current = _get_rect(resolved)

    new_x = x if x is not None else current.x
    new_y = y if y is not None else current.y
    new_w = width if width is not None else current.width
    new_h = height if height is not None else current.height

    ctypes.windll.user32.MoveWindow(resolved, new_x, new_y, new_w, new_h, True)
    return json.dumps({"moved": {"x": new_x, "y": new_y, "width": new_w, "height": new_h}})


@mcp.tool()
def invoke_element(
    window_title: str | None = None,
    hwnd: int | None = None,
    automation_id: str | None = None,
    name: str | None = None,
) -> str:
    """Invoke a UI element's default action via UI Automation.

    More reliable than coordinate clicking — uses the Invoke or Toggle
    pattern to activate buttons, checkboxes, menu items, etc.

    Args:
        window_title: Window containing the element.
        hwnd: Window handle.
        automation_id: Element's automation ID.
        name: Element's name/label.
    """
    from .uia import invoke_element as _invoke

    resolved = _resolve_hwnd(window_title, hwnd)
    result = _invoke(resolved, automation_id=automation_id, name=name)
    return json.dumps({"invoked": result})


# ═══════════════════════════════════════════════════════════════════════════
# System Tools
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
def run_command(command: str, timeout_seconds: float = 30.0) -> str:
    """Execute a shell command and return output.

    Args:
        command: The command to run.
        timeout_seconds: Max execution time.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        return json.dumps({
            "returncode": result.returncode,
            "stdout": result.stdout[:5000],
            "stderr": result.stderr[:2000],
        })
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Command timed out", "timeout": timeout_seconds})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def take_action_sequence(actions: list[dict]) -> str:
    """Execute a batch of actions in sequence to reduce round-trips.

    Each action is a dict with "tool" (tool name) and "params" (tool parameters).
    Optional "delay_ms" between actions.

    Example:
    [
        {"tool": "click", "params": {"x": 100, "y": 200}},
        {"tool": "type_text", "params": {"text": "hello"}, "delay_ms": 500},
        {"tool": "press_keys", "params": {"keys": "enter"}}
    ]

    Args:
        actions: List of action dicts with tool name and parameters.
    """
    tool_map = {
        "click": click,
        "type_text": type_text,
        "press_keys": press_keys,
        "mouse_move": mouse_move,
        "mouse_drag": mouse_drag,
        "scroll": scroll,
        "focus_window": focus_window,
        "invoke_element": invoke_element,
    }

    results = []
    for i, action in enumerate(actions):
        tool_name = action.get("tool", "")
        params = action.get("params", {})
        delay_ms = action.get("delay_ms", 0)

        if tool_name not in tool_map:
            results.append({"step": i, "error": f"Unknown tool: {tool_name}"})
            continue

        try:
            result = tool_map[tool_name](**params)
            results.append({"step": i, "result": json.loads(result) if isinstance(result, str) else result})
        except Exception as e:
            results.append({"step": i, "error": str(e)})
            break  # Stop sequence on error

        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)

    return json.dumps(results, indent=2)


@mcp.tool()
def get_display_info() -> str:
    """Get display configuration: monitor count, resolutions, DPI."""
    import mss as mss_module

    with mss_module.mss() as sct:
        monitors = []
        for i, m in enumerate(sct.monitors):
            if i == 0:
                continue  # Skip the "all monitors" entry
            monitors.append({
                "index": i,
                "x": m["left"],
                "y": m["top"],
                "width": m["width"],
                "height": m["height"],
            })

    return json.dumps({
        "monitor_count": len(monitors),
        "monitors": monitors,
    }, indent=2)


@mcp.tool()
def pause_input() -> str:
    """Emergency stop — pause all mouse/keyboard automation."""
    safety.pause()
    return json.dumps({"paused": True})


@mcp.tool()
def resume_input() -> str:
    """Resume automation after a pause."""
    safety.resume()
    return json.dumps({"resumed": True})


@mcp.tool()
def get_action_log(last_n: int = 20) -> str:
    """View the log of recent automation actions.

    Args:
        last_n: Number of recent actions to return.
    """
    records = safety.get_action_log(last_n=last_n)
    return json.dumps(
        [{"action": r.action, "params": r.params, "timestamp": r.timestamp.isoformat()} for r in records],
        indent=2,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════


def _resolve_hwnd(window_title: str | None, hwnd: int | None) -> int:
    """Resolve a window handle from title or direct handle."""
    if hwnd is not None:
        return hwnd
    if window_title:
        from .uia import find_window_by_title

        found = find_window_by_title(window_title)
        if found is None:
            raise ValueError(f"No window found matching '{window_title}'")
        return found
    raise ValueError("Must provide either window_title or hwnd")


def _compact_tree(node: dict) -> dict:
    """Remove empty/default fields from element tree to save tokens."""
    compact = {}
    if node.get("name"):
        compact["name"] = node["name"]
    if node.get("control_type"):
        compact["type"] = node["control_type"]
    if node.get("automation_id"):
        compact["id"] = node["automation_id"]
    if node.get("rect"):
        r = node["rect"]
        compact["rect"] = [r["x"], r["y"], r["width"], r["height"]]
    if not node.get("is_enabled", True):
        compact["enabled"] = False
    if node.get("value"):
        compact["value"] = node["value"]
    if node.get("patterns"):
        compact["patterns"] = node["patterns"]
    if node.get("children"):
        compact["children"] = [_compact_tree(c) for c in node["children"]]
    return compact


def main_stdio():
    """Entry point for the desktop-mcp-server console script."""
    import sys

    # Pre-initialize COM + UIA type library on the main thread BEFORE
    # the async event loop starts.  This prevents comtypes from lazily
    # generating wrappers inside an async context (which hangs).
    try:
        from .uia import initialize
        initialize()
    except Exception as exc:
        print(f"[desktop-mcp] UIA init failed: {exc}", file=sys.stderr, flush=True)
        # Continue anyway — window enumeration & capture still work
        # without UIA; only tree/element tools will fail.

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main_stdio()
