"""OCR text extraction via Windows built-in OCR (winocr)."""

from __future__ import annotations

import asyncio
import io

from PIL import Image

from .models import OcrLine, Rect


async def _recognize_async(image: Image.Image, language: str = "en") -> list[OcrLine]:
    """Run Windows OCR on a PIL Image."""
    import winocr

    buf = io.BytesIO()
    image.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    result = await winocr.recognize_pil(image, lang=language)

    lines = []
    for line in result.lines:
        lines.append(
            OcrLine(
                text=line.text,
                bounding_box=Rect(
                    x=int(line.x),
                    y=int(line.y),
                    width=int(line.width),
                    height=int(line.height),
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
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, _recognize_async(image, language))
            return future.result()
    else:
        return asyncio.run(_recognize_async(image, language))


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
