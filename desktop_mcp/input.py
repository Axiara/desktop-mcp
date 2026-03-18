"""Mouse and keyboard input via pyautogui."""

from __future__ import annotations

import pyautogui

from . import safety

# Disable pyautogui's failsafe (moving mouse to corner aborts) since
# this is intentional automation controlled by an AI agent.
pyautogui.FAILSAFE = False
# Minimal pause between pyautogui actions
pyautogui.PAUSE = 0.01

# Text longer than this threshold is pasted via clipboard instead of
# typed character-by-character, which is dramatically faster.
_PASTE_THRESHOLD = 32


def click(
    x: int,
    y: int,
    button: str = "left",
    clicks: int = 1,
) -> None:
    """Click at screen coordinates."""
    safety.pre_action("click", {"x": x, "y": y, "button": button, "clicks": clicks})
    pyautogui.click(x=x, y=y, button=button, clicks=clicks)


def type_text(text: str, interval: float = 0.01, use_clipboard: bool | None = None) -> None:
    """Type a text string.

    For short ASCII text, types character-by-character.
    For long text or text with non-ASCII characters, pastes via clipboard
    (much faster — 615 chars in ~50ms vs ~12 seconds).

    Args:
        text: The text to type.
        interval: Seconds between each character (only used for short text).
        use_clipboard: Force clipboard paste (True) or char-by-char (False).
                       None = auto-decide based on length and content.
    """
    safety.pre_action("type_text", {"length": len(text), "preview": text[:80]})

    should_paste = use_clipboard
    if should_paste is None:
        has_unicode = any(ord(c) > 127 for c in text)
        has_newlines = "\n" in text
        should_paste = has_unicode or has_newlines or len(text) > _PASTE_THRESHOLD

    if should_paste:
        _paste_text(text)
    else:
        pyautogui.typewrite(text, interval=interval)


def _paste_text(text: str) -> None:
    """Paste text via clipboard — fast path for long/unicode text."""
    import win32clipboard
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
    finally:
        win32clipboard.CloseClipboard()
    pyautogui.hotkey("ctrl", "v")


def press_keys(*keys: str) -> None:
    """Press a key combination."""
    safety.pre_action("press_keys", {"keys": list(keys)})
    pyautogui.hotkey(*keys)


def mouse_move(x: int, y: int, duration: float = 0.05) -> None:
    """Move mouse to coordinates."""
    safety.pre_action("mouse_move", {"x": x, "y": y})
    pyautogui.moveTo(x=x, y=y, duration=duration)


def mouse_drag(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    button: str = "left",
    duration: float = 0.2,
) -> None:
    """Drag from one point to another."""
    safety.pre_action("mouse_drag", {
        "start": [start_x, start_y], "end": [end_x, end_y],
        "button": button,
    })
    pyautogui.moveTo(start_x, start_y)
    pyautogui.drag(
        end_x - start_x, end_y - start_y,
        duration=duration, button=button,
    )


def scroll(amount: int, x: int | None = None, y: int | None = None) -> None:
    """Scroll the mouse wheel."""
    safety.pre_action("scroll", {"amount": amount, "x": x, "y": y})
    pyautogui.scroll(amount, x=x, y=y)


def get_cursor_position() -> tuple[int, int]:
    """Return current mouse cursor coordinates."""
    pos = pyautogui.position()
    return pos.x, pos.y
