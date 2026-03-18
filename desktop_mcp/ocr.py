"""OCR text extraction via Windows built-in OCR (winocr)."""

from __future__ import annotations

import asyncio
import concurrent.futures

from PIL import Image

from .models import OcrLine, Rect

# Reusable thread pool so we don't create/destroy one per OCR call.
_ocr_pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)


def _recognize_sync(image: Image.Image, language: str = "en") -> list[OcrLine]:
    """Run Windows OCR synchronously in a dedicated thread.

    winocr is async-only, so we spin up a fresh event loop in a
    worker thread.  This keeps the MCP server's own event loop free.
    """
    import winocr

    async def _inner():
        return await winocr.recognize_pil(image, lang=language)

    result = asyncio.run(_inner())

    lines = []
    for line in result.lines:
        # OcrLine only has .text and .words — bounding boxes live on
        # OcrWord.bounding_rect.  Compute line bbox from word union.
        if not line.words:
            lines.append(OcrLine(
                text=line.text,
                bounding_box=Rect(x=0, y=0, width=0, height=0),
            ))
            continue

        min_x = float("inf")
        min_y = float("inf")
        max_x = 0.0
        max_y = 0.0
        for word in line.words:
            br = word.bounding_rect
            min_x = min(min_x, br.x)
            min_y = min(min_y, br.y)
            max_x = max(max_x, br.x + br.width)
            max_y = max(max_y, br.y + br.height)

        lines.append(
            OcrLine(
                text=line.text,
                bounding_box=Rect(
                    x=int(min_x),
                    y=int(min_y),
                    width=int(max_x - min_x),
                    height=int(max_y - min_y),
                ),
            )
        )
    return lines


def read_image_text(image: Image.Image, language: str = "en") -> list[OcrLine]:
    """Extract text from a PIL Image using Windows OCR.

    Args:
        image: PIL Image to OCR.
        language: OCR language code (default "en").

    Returns:
        List of OcrLine with text and bounding boxes.
    """
    future = _ocr_pool.submit(_recognize_sync, image, language)
    return future.result(timeout=30)


def read_screen_region_text(
    region: Rect | None = None,
    language: str = "en",
) -> list[OcrLine]:
    """Capture a screen region and extract text.

    Args:
        region: Screen region to OCR, or None for full screen.
        language: OCR language code.

    Returns:
        List of OcrLine with text and bounding boxes.
    """
    import mss

    with mss.mss() as sct:
        if region:
            monitor = {
                "left": region.x, "top": region.y,
                "width": region.width, "height": region.height,
            }
        else:
            monitor = sct.monitors[0]
        screenshot = sct.grab(monitor)
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

    return read_image_text(img, language)
