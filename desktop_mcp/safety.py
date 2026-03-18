"""Safety layer: action logging, pause control, and configurable delays."""

from __future__ import annotations

import os
import time
import threading
from collections import deque
from datetime import datetime

from .models import ActionRecord

_paused = False
_lock = threading.Lock()
_action_log: deque[ActionRecord] = deque(maxlen=1000)

ACTION_DELAY_MS = int(os.environ.get("DESKTOP_MCP_ACTION_DELAY_MS", "50"))


class AutomationPausedError(Exception):
    """Raised when an action is attempted while automation is paused."""


def pause() -> None:
    """Pause all automation actions."""
    global _paused
    with _lock:
        _paused = True


def resume() -> None:
    """Resume automation actions."""
    global _paused
    with _lock:
        _paused = False


def is_paused() -> bool:
    """Check if automation is paused."""
    with _lock:
        return _paused


def pre_action(action_name: str, params: dict | None = None) -> None:
    """Call before every input action. Checks pause state, logs, and delays."""
    with _lock:
        if _paused:
            raise AutomationPausedError(
                f"Automation is paused. Cannot execute '{action_name}'. "
                "Call resume_input to continue."
            )

    record = ActionRecord(
        action=action_name,
        params=params or {},
        timestamp=datetime.now(),
    )
    _action_log.append(record)

    if ACTION_DELAY_MS > 0:
        time.sleep(ACTION_DELAY_MS / 1000.0)


def get_action_log(last_n: int = 50) -> list[ActionRecord]:
    """Return the most recent action records."""
    items = list(_action_log)
    return items[-last_n:]


def clear_action_log() -> None:
    """Clear the action log."""
    _action_log.clear()
