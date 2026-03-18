# desktop-mcp

Windows desktop automation MCP server — gives AI agents eyes and hands on the desktop.

**Repo:** `C:\Users\mfox\source\repos\desktop-mcp\`
**GitHub:** `Axiara/desktop-mcp` (public)
**Entry point:** `desktop-mcp-server` (console script on PATH via `pip install -e .`)
**MCP config:** `C:\Users\mfox\.mcp.json` → `"desktop-mcp": {"command": "desktop-mcp-server"}`

## Quick Start

```bash
pip install -e ".[dev]"       # Install + dev deps (editable)
pytest tests/ -v              # Run all tests (58 tests)
pytest tests/ -v -m "not slow"  # Unit tests only (skip live desktop tests)
desktop-mcp-server            # Start MCP server (stdio transport)
```

## Architecture

Flat package — 7 modules, no subpackages:

| Module | What it does |
|--------|-------------|
| `server.py` | FastMCP instance, all 29 tool registrations, `main_stdio()` entry point |
| `uia.py` | Windows UI Automation via comtypes COM — element trees, window enumeration, element search/invoke |
| `capture.py` | Screen/window capture via mss + Pillow — auto-downscale, format control, image diff |
| `input.py` | Mouse/keyboard via pyautogui — click, type, keys, drag, scroll |
| `ocr.py` | OCR via winocr (Windows.Media.Ocr WinRT API) |
| `safety.py` | Pause/resume, action logging, configurable delays |
| `models.py` | Pydantic models shared across modules |

### Module Dependency Flow

```
server.py (MCP tools)
  ├── uia.py (COM/UI Automation)
  ├── capture.py (screenshots)
  ├── input.py (mouse/keyboard)
  ├── ocr.py (text extraction)
  ├── safety.py (logging/pause)
  └── models.py (shared types)
```

Core modules (`uia`, `capture`, `input`, `ocr`) know nothing about MCP — they're independently testable. Only `server.py` imports `mcp.server.fastmcp`.

## Critical Design Decisions

### COM Initialization Must Happen Before Async Event Loop

`main_stdio()` calls `uia.initialize()` **before** `mcp.run()`. This eagerly:
1. Calls `comtypes.CoInitialize()` on the main thread
2. Generates the UIAutomationClient type library wrappers (from UIAutomationCore.dll)
3. Creates the `IUIAutomation` COM singleton

If this happens lazily inside a tool call (during the async event loop), comtypes hangs trying to generate Python wrappers. This was the original server-hang bug.

### Auto-Focus Before Interaction

All interaction tools (`click`, `type_text`, `press_keys`, `invoke_element`) accept `window_title`/`hwnd` and call `_auto_focus()` before acting. This prevents the "action goes to wrong window" bug that happened when Word lost focus after launching.

### Clipboard Paste for Long Text

`type_text` auto-detects when to paste via clipboard vs type char-by-char:
- Text >32 chars → clipboard paste (~50ms)
- Text with newlines or unicode → clipboard paste
- Short ASCII → `pyautogui.typewrite()` char-by-char

This is controlled by `_PASTE_THRESHOLD` in `input.py`. Typing 615 chars char-by-char took 12 seconds; clipboard paste takes ~50ms.

### Token Efficiency

The #1 design constraint. Strategies:
- `_compact_tree()` strips empty fields and compresses rects to `[x,y,w,h]` arrays
- `get_window_tree` is the PRIMARY observation tool — structured JSON, not screenshots
- Screenshots auto-downscale to 1280px max, support JPEG for smaller payloads
- Only 5 interactive UIA patterns are probed per element (not all 19)
- Server instructions tell the AI to avoid redundant verification

### OCR Line Bounding Boxes

winocr's `OcrLine` only has `.text` and `.words`. Bounding boxes live on `OcrWord.bounding_rect` (`.x`, `.y`, `.width`, `.height`). Line bounding boxes are computed as the union of word bounding rects. Do NOT try to access `.x`/`.y` on `OcrLine` — it will crash.

## 29 MCP Tools

### Observation (12)
`list_windows`, `get_window_tree`, `get_element_info`, `find_element`, `capture_screen`, `capture_window`, `read_screen_text`, `get_cursor_position`, `get_clipboard`, `wait_for_element`, `wait_for_window`, `compare_captures`

### Interaction (10)
`click`, `type_text`, `press_keys`, `mouse_move`, `mouse_drag`, `scroll`, `set_clipboard`, `focus_window`, `move_window`, `invoke_element`

### Composite / System (7)
`launch_and_focus`, `run_command`, `take_action_sequence`, `get_display_info`, `pause_input`, `resume_input`, `get_action_log`

### Key Composite Tools

**`launch_and_focus`** — Opens an app in one call: runs command → waits for window → focuses → optionally clicks an element (e.g., "Blank document" in Word). Replaces the old 4+ step pattern.

**`take_action_sequence`** — Batches multiple tool calls in one round-trip. Supports ALL tools (interaction + observation). Stops on error.

## Testing

```bash
pytest tests/ -v              # All 58 tests
pytest tests/ -v -m "not slow"  # Unit tests only (no live desktop)
pytest tests/ -v -m slow      # Integration tests (needs live desktop session)
```

| Test file | What it covers |
|-----------|---------------|
| `test_models.py` | Pydantic model creation and serialization |
| `test_safety.py` | Pause/resume, action logging, delay behavior |
| `test_capture.py` | Image downscale, encode, compare (no live desktop needed) |
| `test_input.py` | Mouse/keyboard with mocked pyautogui |
| `test_server.py` | Tool helper functions, `_compact_tree`, `_resolve_hwnd`, `_auto_focus` |
| `test_integration.py` | Live desktop: real window enumeration, capture, element trees |

Integration tests use real windows and are marked `@pytest.mark.slow`.

## Environment Variables

| Variable | Default | Effect |
|----------|---------|--------|
| `DESKTOP_MCP_ACTION_DELAY_MS` | `10` | Milliseconds to sleep between input actions |

## Known Issues / Gotchas

- **comtypes.gen cache**: If the generated UIAutomationClient wrappers get corrupted, delete `Lib/site-packages/comtypes/gen/` and restart. The server will regenerate them.
- **SetForegroundWindow limitations**: Windows restricts which processes can steal focus. The server uses `SetForegroundWindow` which works when Claude Code is the foreground process, but may not work from a background service.
- **pyautogui FAILSAFE is disabled**: Moving the mouse to (0,0) will NOT abort automation. Use the `pause_input` tool instead.
- **DPI scaling**: Coordinates are in screen pixels. On high-DPI displays, element coordinates from UIA should match what mss captures, but pyautogui may need DPI awareness if the Python process isn't DPI-aware.

## Deployment Pattern

Same as other CRG MCP servers:
- **Source:** `C:\Users\mfox\source\repos\desktop-mcp\`
- **Install:** `pip install -e .` creates `desktop-mcp-server` console script on PATH
- **MCP config:** `C:\Users\mfox\.mcp.json` entry with `"command": "desktop-mcp-server"`
- **No separate deploy path** yet (runs from dev install)
