"""Mouse and keyboard input via pyautogui."""

from __future__ import annotations

import pyautogui

from . import safety

# Disable pyautogui's failsafe (moving mouse to corner aborts) since
# this is intentional automation controlled by an AI agent.
pyautogui.FAILSAFE = False
# Set a short default pause between pyautogui actions
pyautogui.PAUSE = 0.02


def click(
    x: int,
    y: int,
    button: str = "left",
    clicks: int = 1,
) -> None:
    """Click at screen coordinates.

    Args:
        x: X coordinate.
        y: Y coordinate.
        button: "left", "right", or "middle".
        clicks: Number of clicks (1=single, 2=double, 3=triple).
    """
    safety.pre_action("click", {"x": x, "y": y, "button": button, "clicks": clicks})
    pyautogui.click(x=x, y=y, button=button, clicks=clicks)


def type_text(text: str, interval: float = 0.02) -> None:
    """Type a text string character by character.

    Args:
        text: The text to type.
        interval: Seconds between each character.
    """
    safety.pre_action("type_text", {"text": text[:100], "interval": interval})
    pyautogui.typewrite(text, interval=interval) if all(ord(c) < 128 for c in text) else _type_unicode(text, interval)


def _type_unicode(text: str, interval: float) -> None:
    """Type unicode text using pyperclip + paste, falling back to write()."""
    import time
    for char in text:
        if ord(char) < 128:
            pyautogui.press(char) if len(char) == 1 else pyautogui.typewrite(char)
        else:
            # For non-ASCII, use the clipboard
            import pyperclip
            pyperclip.copy(char)
            pyautogui.hotkey("ctrl", "v")
        time.sleep(interval)


def press_keys(*keys: str) -> None:
    """Press a key combination.

    Args:
        keys: Key names (e.g., "ctrl", "s"). Pressed as a hotkey combination.
    """
    safety.pre_action("press_keys", {"keys": list(keys)})
    pyautogui.hotkey(*keys)


def mouse_move(x: int, y: int, duration: float = 0.1) -> None:
    """Move mouse to coordinates.

    Args:
        x: Target X coordinate.
        y: Target Y coordinate.
        duration: Seconds for the movement animation.
    """
    safety.pre_action("mouse_move", {"x": x, "y": y, "duration": duration})
    pyautogui.moveTo(x=x, y=y, duration=duration)


def mouse_drag(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    button: str = "left",
    duration: float = 0.3,
) -> None:
    """Drag from one point to another.

    Args:
        start_x: Starting X.
        start_y: Starting Y.
        end_x: Ending X.
        end_y: Ending Y.
        button: Mouse button to hold.
        duration: Seconds for the drag.
    """
    safety.pre_action("mouse_drag", {
        "start": [start_x, start_y], "end": [end_x, end_y],
        "button": button, "duration": duration,
    })
    pyautogui.moveTo(start_x, start_y)
    pyautogui.drag(
        end_x - start_x, end_y - start_y,
        duration=duration, button=button,
    )


def scroll(amount: int, x: int | None = None, y: int | None = None) -> None:
    """Scroll the mouse wheel.

    Args:
        amount: Positive = scroll up, negative = scroll down.
        x: X coordinate to scroll at (None = current position).
        y: Y coordinate to scroll at (None = current position).
    """
    safety.pre_action("scroll", {"amount": amount, "x": x, "y": y})
    pyautogui.scroll(amount, x=x, y=y)


def get_cursor_position() -> tuple[int, int]:
    """Return current mouse cursor coordinates."""
    pos = pyautogui.position()
    return pos.x, pos.y
