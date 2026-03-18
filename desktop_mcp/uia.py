"""Windows UI Automation wrapper using comtypes COM interfaces."""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from typing import Any

from .models import ElementNode, ElementInfo, Rect, WindowInfo

# ── UIA Control Type IDs → friendly names ─────────────────────────────────
_CONTROL_TYPES: dict[int, str] = {
    50000: "Button",
    50001: "Calendar",
    50002: "CheckBox",
    50003: "ComboBox",
    50004: "Edit",
    50005: "Hyperlink",
    50006: "Image",
    50007: "ListItem",
    50008: "List",
    50009: "Menu",
    50010: "MenuBar",
    50011: "MenuItem",
    50012: "ProgressBar",
    50013: "RadioButton",
    50014: "ScrollBar",
    50015: "Slider",
    50016: "Spinner",
    50017: "StatusBar",
    50018: "Tab",
    50019: "TabItem",
    50020: "Text",
    50021: "ToolBar",
    50022: "ToolTip",
    50023: "Tree",
    50024: "TreeItem",
    50025: "Custom",
    50026: "Group",
    50027: "Thumb",
    50028: "DataGrid",
    50029: "DataItem",
    50030: "Document",
    50031: "SplitButton",
    50032: "Window",
    50033: "Pane",
    50034: "Header",
    50035: "HeaderItem",
    50036: "Table",
    50037: "TitleBar",
    50038: "Separator",
}

# ── UIA Pattern IDs → friendly names ──────────────────────────────────────
_PATTERN_IDS: dict[int, str] = {
    10000: "Invoke",
    10001: "Selection",
    10002: "Value",
    10003: "RangeValue",
    10004: "Scroll",
    10005: "ExpandCollapse",
    10006: "Grid",
    10007: "GridItem",
    10008: "MultipleView",
    10009: "Window",
    10010: "SelectionItem",
    10011: "Dock",
    10012: "Table",
    10013: "TableItem",
    10014: "Text",
    10015: "Toggle",
    10016: "Transform",
    10017: "ScrollItem",
    10018: "LegacyIAccessible",
}

# Subset of patterns worth probing per element (the common interactive ones).
# Checking all 19 patterns on every element is slow; limit to actionable ones.
_PROBE_PATTERN_IDS: dict[int, str] = {
    10000: "Invoke",
    10002: "Value",
    10005: "ExpandCollapse",
    10010: "SelectionItem",
    10015: "Toggle",
}

# ── Win32 helpers ─────────────────────────────────────────────────────────
user32 = ctypes.windll.user32

GW_HWNDNEXT = 2
GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_VISIBLE = 0x10000000
WS_MINIMIZE = 0x20000000
WS_MAXIMIZE = 0x01000000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000

_GetWindowTextW = user32.GetWindowTextW
_GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
_GetWindowTextW.restype = ctypes.c_int

_GetClassNameW = user32.GetClassNameW
_GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
_GetClassNameW.restype = ctypes.c_int

_GetWindowThreadProcessId = user32.GetWindowThreadProcessId
_GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
_GetWindowThreadProcessId.restype = wintypes.DWORD

_GetWindowRect = user32.GetWindowRect
_GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
_GetWindowRect.restype = wintypes.BOOL

_GetWindowLongW = user32.GetWindowLongW
_GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
_GetWindowLongW.restype = ctypes.c_long

_IsWindowVisible = user32.IsWindowVisible
_IsWindowVisible.argtypes = [wintypes.HWND]
_IsWindowVisible.restype = wintypes.BOOL

_IsIconic = user32.IsIconic
_IsIconic.argtypes = [wintypes.HWND]
_IsIconic.restype = wintypes.BOOL

_IsZoomed = user32.IsZoomed
_IsZoomed.argtypes = [wintypes.HWND]
_IsZoomed.restype = wintypes.BOOL

_SetForegroundWindow = user32.SetForegroundWindow
_SetForegroundWindow.argtypes = [wintypes.HWND]
_SetForegroundWindow.restype = wintypes.BOOL

_GetForegroundWindow = user32.GetForegroundWindow
_GetForegroundWindow.argtypes = []
_GetForegroundWindow.restype = wintypes.HWND

_EnumWindows = user32.EnumWindows
_WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
_EnumWindows.argtypes = [_WNDENUMPROC, wintypes.LPARAM]
_EnumWindows.restype = wintypes.BOOL


def _get_window_text(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(512)
    _GetWindowTextW(hwnd, buf, 512)
    return buf.value


def _get_class_name(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    _GetClassNameW(hwnd, buf, 256)
    return buf.value


def _get_pid(hwnd: int) -> int:
    pid = wintypes.DWORD()
    _GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def _get_rect(hwnd: int) -> Rect:
    r = wintypes.RECT()
    _GetWindowRect(hwnd, ctypes.byref(r))
    return Rect(x=r.left, y=r.top, width=r.right - r.left, height=r.bottom - r.top)


def _get_style(hwnd: int) -> int:
    return _GetWindowLongW(hwnd, GWL_STYLE)


def _get_ex_style(hwnd: int) -> int:
    return _GetWindowLongW(hwnd, GWL_EXSTYLE)


# ── Public API ────────────────────────────────────────────────────────────


def list_windows(include_invisible: bool = False) -> list[WindowInfo]:
    """Enumerate top-level windows.

    By default only returns visible, non-tool windows with a title.
    """
    results: list[WindowInfo] = []

    def _callback(hwnd: int, _lparam: int) -> bool:
        title = _get_window_text(hwnd)
        is_visible = bool(_IsWindowVisible(hwnd))

        if not include_invisible:
            if not is_visible or not title:
                return True
            ex_style = _get_ex_style(hwnd)
            if (ex_style & WS_EX_TOOLWINDOW) and not (ex_style & WS_EX_APPWINDOW):
                return True

        style = _get_style(hwnd)
        results.append(
            WindowInfo(
                hwnd=hwnd,
                title=title,
                class_name=_get_class_name(hwnd),
                pid=_get_pid(hwnd),
                rect=_get_rect(hwnd),
                is_visible=is_visible,
                is_minimized=bool(style & WS_MINIMIZE),
                is_maximized=bool(style & WS_MAXIMIZE),
            )
        )
        return True

    _EnumWindows(_WNDENUMPROC(_callback), 0)
    return results


def find_window_by_title(title_substring: str) -> int | None:
    """Find a window handle by partial title match (case-insensitive)."""
    title_lower = title_substring.lower()
    for win in list_windows():
        if title_lower in win.title.lower():
            return win.hwnd
    return None


def focus_window(hwnd: int) -> bool:
    """Bring a window to the foreground."""
    return bool(_SetForegroundWindow(hwnd))


# ── UI Automation ─────────────────────────────────────────────────────────

_uia: Any = None
_uia_initialized: bool = False
_UIAutomationClient: Any = None  # cached module reference


def _log(msg: str) -> None:
    """Log to stderr (never stdout — that's the MCP transport)."""
    print(f"[desktop-mcp] {msg}", file=sys.stderr, flush=True)


def initialize() -> None:
    """Eagerly initialize COM and generate UIA type library wrappers.

    MUST be called once on the main thread before the async event loop
    starts. This prevents comtypes from trying to generate wrappers
    lazily during a tool call (which hangs).
    """
    global _uia, _uia_initialized, _UIAutomationClient

    if _uia_initialized:
        return

    import comtypes
    import comtypes.client
    from comtypes import GUID

    _log("Initializing COM...")
    comtypes.CoInitialize()

    _log("Generating UIAutomation type library wrappers...")
    try:
        from comtypes.gen import UIAutomationClient
    except ImportError:
        comtypes.client.GetModule("UIAutomationCore.dll")
        from comtypes.gen import UIAutomationClient

    _UIAutomationClient = UIAutomationClient

    _log("Creating IUIAutomation instance...")
    CLSID_CUIAutomation = GUID("{FF48DBA4-60EF-4201-AA87-54103EEF594E}")
    _uia = comtypes.CoCreateInstance(
        CLSID_CUIAutomation,
        interface=UIAutomationClient.IUIAutomation,
        clsctx=comtypes.CLSCTX_INPROC_SERVER,
    )

    _uia_initialized = True
    _log("UIA ready.")


def _get_uia():
    """Return the IUIAutomation COM singleton.

    Raises RuntimeError if initialize() hasn't been called.
    """
    if not _uia_initialized:
        # Fallback: initialize now (slower, but avoids hard crash)
        _log("WARNING: UIA not pre-initialized, initializing lazily...")
        initialize()
    return _uia


def _get_uia_module():
    """Return the generated UIAutomationClient module."""
    if _UIAutomationClient is None:
        initialize()
    return _UIAutomationClient


def _element_to_node(element: Any, walker: Any, max_depth: int, current_depth: int = 0) -> ElementNode:
    """Recursively convert a UIA element to an ElementNode."""
    try:
        name = element.CurrentName or ""
    except Exception:
        name = ""

    try:
        control_type_id = element.CurrentControlType
        control_type = _CONTROL_TYPES.get(control_type_id, f"Unknown({control_type_id})")
    except Exception:
        control_type = "Unknown"

    try:
        automation_id = element.CurrentAutomationId or ""
    except Exception:
        automation_id = ""

    try:
        class_name = element.CurrentClassName or ""
    except Exception:
        class_name = ""

    try:
        r = element.CurrentBoundingRectangle
        rect = Rect(
            x=int(r.left), y=int(r.top),
            width=int(r.right - r.left), height=int(r.bottom - r.top),
        )
    except Exception:
        rect = None

    try:
        is_enabled = bool(element.CurrentIsEnabled)
    except Exception:
        is_enabled = True

    # Only probe the small subset of interactive patterns
    value = None
    patterns: list[str] = []
    for pattern_id, pattern_name in _PROBE_PATTERN_IDS.items():
        try:
            pat = element.GetCurrentPattern(pattern_id)
            if pat is not None:
                patterns.append(pattern_name)
                if pattern_name == "Value" and value is None:
                    try:
                        uia_mod = _get_uia_module()
                        val_pat = pat.QueryInterface(uia_mod.IUIAutomationValuePattern)
                        value = val_pat.CurrentValue
                    except Exception:
                        pass
        except Exception:
            pass

    children: list[ElementNode] = []
    if current_depth < max_depth:
        try:
            child = walker.GetFirstChildElement(element)
            while child is not None:
                children.append(
                    _element_to_node(child, walker, max_depth, current_depth + 1)
                )
                child = walker.GetNextSiblingElement(child)
        except Exception:
            pass

    return ElementNode(
        name=name,
        control_type=control_type,
        automation_id=automation_id,
        class_name=class_name,
        rect=rect,
        is_enabled=is_enabled,
        value=value,
        patterns=patterns,
        children=children,
    )


def get_window_tree(hwnd: int, max_depth: int = 3) -> ElementNode:
    """Get the UI Automation element tree for a window.

    Args:
        hwnd: Window handle.
        max_depth: Maximum tree depth to traverse (default 3 for token efficiency).

    Returns:
        The element tree as nested ElementNode objects.
    """
    uia = _get_uia()
    element = uia.ElementFromHandle(hwnd)
    walker = uia.ControlViewWalker
    return _element_to_node(element, walker, max_depth)


def get_element_info(hwnd: int, automation_id: str | None = None, name: str | None = None) -> ElementInfo | None:
    """Find and return detailed info about a specific UI element.

    Searches by automation_id or name within the given window.
    """
    uia = _get_uia()
    uia_mod = _get_uia_module()
    root = uia.ElementFromHandle(hwnd)

    condition = None
    if automation_id:
        condition = uia.CreatePropertyCondition(30011, automation_id)  # AutomationId
    elif name:
        condition = uia.CreatePropertyCondition(30005, name)  # Name
    else:
        return None

    found = root.FindFirst(4, condition)  # 4 = TreeScope_Descendants
    if found is None:
        return None

    try:
        r = found.CurrentBoundingRectangle
        rect = Rect(x=int(r.left), y=int(r.top),
                     width=int(r.right - r.left), height=int(r.bottom - r.top))
    except Exception:
        rect = None

    patterns = []
    for pattern_id, pattern_name in _PATTERN_IDS.items():
        try:
            if found.GetCurrentPattern(pattern_id) is not None:
                patterns.append(pattern_name)
        except Exception:
            pass

    value = None
    try:
        val_pat = found.GetCurrentPattern(10002)  # Value pattern
        if val_pat is not None:
            vp = val_pat.QueryInterface(uia_mod.IUIAutomationValuePattern)
            value = vp.CurrentValue
    except Exception:
        pass

    return ElementInfo(
        name=found.CurrentName or "",
        control_type=_CONTROL_TYPES.get(found.CurrentControlType, "Unknown"),
        automation_id=found.CurrentAutomationId or "",
        class_name=found.CurrentClassName or "",
        rect=rect,
        is_enabled=bool(found.CurrentIsEnabled),
        is_offscreen=bool(found.CurrentIsOffscreen),
        value=value,
        patterns=patterns,
        hwnd=found.CurrentNativeWindowHandle or 0,
    )


def find_elements(
    hwnd: int,
    name: str | None = None,
    control_type: str | None = None,
    automation_id: str | None = None,
) -> list[ElementInfo]:
    """Search for UI elements matching the given criteria."""
    uia = _get_uia()
    root = uia.ElementFromHandle(hwnd)

    conditions = []
    if name:
        conditions.append(uia.CreatePropertyCondition(30005, name))
    if automation_id:
        conditions.append(uia.CreatePropertyCondition(30011, automation_id))
    if control_type:
        type_id = None
        for tid, tname in _CONTROL_TYPES.items():
            if tname.lower() == control_type.lower():
                type_id = tid
                break
        if type_id:
            conditions.append(uia.CreatePropertyCondition(30003, type_id))

    if not conditions:
        return []

    if len(conditions) == 1:
        condition = conditions[0]
    else:
        condition = conditions[0]
        for c in conditions[1:]:
            condition = uia.CreateAndCondition(condition, c)

    found_all = root.FindAll(4, condition)  # TreeScope_Descendants
    results = []
    if found_all is not None:
        for i in range(found_all.Length):
            el = found_all.GetElement(i)
            try:
                r = el.CurrentBoundingRectangle
                rect = Rect(x=int(r.left), y=int(r.top),
                             width=int(r.right - r.left), height=int(r.bottom - r.top))
            except Exception:
                rect = None

            results.append(ElementInfo(
                name=el.CurrentName or "",
                control_type=_CONTROL_TYPES.get(el.CurrentControlType, "Unknown"),
                automation_id=el.CurrentAutomationId or "",
                class_name=el.CurrentClassName or "",
                rect=rect,
                is_enabled=bool(el.CurrentIsEnabled),
                hwnd=el.CurrentNativeWindowHandle or 0,
            ))
    return results


def invoke_element(hwnd: int, automation_id: str | None = None, name: str | None = None) -> bool:
    """Invoke a UI element's default action (click button, toggle checkbox, etc.)."""
    uia = _get_uia()
    uia_mod = _get_uia_module()
    root = uia.ElementFromHandle(hwnd)

    condition = None
    if automation_id:
        condition = uia.CreatePropertyCondition(30011, automation_id)
    elif name:
        condition = uia.CreatePropertyCondition(30005, name)
    else:
        return False

    found = root.FindFirst(4, condition)
    if found is None:
        return False

    try:
        pat = found.GetCurrentPattern(10000)  # Invoke
        if pat is not None:
            invoke_pat = pat.QueryInterface(uia_mod.IUIAutomationInvokePattern)
            invoke_pat.Invoke()
            return True
    except Exception:
        pass

    try:
        pat = found.GetCurrentPattern(10015)  # Toggle
        if pat is not None:
            toggle_pat = pat.QueryInterface(uia_mod.IUIAutomationTogglePattern)
            toggle_pat.Toggle()
            return True
    except Exception:
        pass

    return False
