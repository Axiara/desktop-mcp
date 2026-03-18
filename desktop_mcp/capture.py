"""Screen and window capture via mss and Pillow."""

from __future__ import annotations

import base64
import io

import mss
from PIL import Image

from .models import Rect, CompareResult
from .uia import _get_rect


DEFAULT_MAX_WIDTH = 1280
DEFAULT_JPEG_QUALITY = 75


def capture_region(
    region: Rect | None = None,
    monitor_index: int = 0,
    max_width: int = DEFAULT_MAX_WIDTH,
    format: str = "png",
    quality: int = DEFAULT_JPEG_QUALITY,
) -> tuple[str, int, int]:
    """Capture a screen region or full monitor.

    Args:
        region: Specific region to capture, or None for full monitor.
        monitor_index: Which monitor (0 = all monitors combined, 1+ = specific).
        max_width: Maximum width for downscaling.
        format: Output format ("png" or "jpeg").
        quality: JPEG quality (1-100), ignored for PNG.

    Returns:
        Tuple of (base64_encoded_image, width, height).
    """
    with mss.mss() as sct:
        if region:
            monitor = {
                "left": region.x,
                "top": region.y,
                "width": region.width,
                "height": region.height,
            }
        else:
            if monitor_index < len(sct.monitors):
                monitor = sct.monitors[monitor_index]
            else:
                monitor = sct.monitors[0]

        screenshot = sct.grab(monitor)
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

    img = _downscale(img, max_width)
    return _encode(img, format, quality)


def capture_window(
    hwnd: int,
    max_width: int = DEFAULT_MAX_WIDTH,
    format: str = "png",
    quality: int = DEFAULT_JPEG_QUALITY,
) -> tuple[str, int, int]:
    """Capture a specific window by its handle.

    Args:
        hwnd: Window handle.
        max_width: Maximum width for downscaling.
        format: Output format ("png" or "jpeg").
        quality: JPEG quality (1-100), ignored for PNG.

    Returns:
        Tuple of (base64_encoded_image, width, height).
    """
    rect = _get_rect(hwnd)
    if rect.width <= 0 or rect.height <= 0:
        raise ValueError(f"Window {hwnd} has invalid dimensions: {rect}")
    return capture_region(
        region=rect, max_width=max_width, format=format, quality=quality
    )


def compare_captures(img1_b64: str, img2_b64: str) -> CompareResult:
    """Compare two base64-encoded images and return diff info.

    Args:
        img1_b64: First image (base64).
        img2_b64: Second image (base64).

    Returns:
        CompareResult with diff percentage and bounding box of changes.
    """
    img1 = Image.open(io.BytesIO(base64.b64decode(img1_b64)))
    img2 = Image.open(io.BytesIO(base64.b64decode(img2_b64)))

    if img1.size != img2.size:
        img2 = img2.resize(img1.size)

    img1_rgb = img1.convert("RGB")
    img2_rgb = img2.convert("RGB")

    px1 = img1_rgb.load()
    px2 = img2_rgb.load()
    w, h = img1_rgb.size

    diff_count = 0
    min_x, min_y, max_x, max_y = w, h, 0, 0
    threshold = 30  # per-channel difference threshold

    for y in range(h):
        for x in range(w):
            r1, g1, b1 = px1[x, y]
            r2, g2, b2 = px2[x, y]
            if abs(r1 - r2) > threshold or abs(g1 - g2) > threshold or abs(b1 - b2) > threshold:
                diff_count += 1
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)

    total_pixels = w * h
    diff_pct = (diff_count / total_pixels) * 100 if total_pixels > 0 else 0.0

    changed_region = None
    if diff_count > 0:
        changed_region = Rect(
            x=min_x, y=min_y, width=max_x - min_x + 1, height=max_y - min_y + 1
        )

    return CompareResult(diff_percentage=round(diff_pct, 2), changed_region=changed_region)


def _downscale(img: Image.Image, max_width: int) -> Image.Image:
    """Downscale image if wider than max_width, preserving aspect ratio."""
    if img.width <= max_width:
        return img
    ratio = max_width / img.width
    new_height = int(img.height * ratio)
    return img.resize((max_width, new_height), Image.LANCZOS)


def _encode(img: Image.Image, format: str, quality: int) -> tuple[str, int, int]:
    """Encode a PIL Image to base64 string."""
    buf = io.BytesIO()
    fmt = format.upper()
    if fmt == "JPEG" or fmt == "JPG":
        img = img.convert("RGB")
        img.save(buf, format="JPEG", quality=quality)
    else:
        img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return b64, img.width, img.height
