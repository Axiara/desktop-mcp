"""Tests for the capture module."""

import base64
import io

import pytest
from PIL import Image

from desktop_mcp.capture import _downscale, _encode, compare_captures
from desktop_mcp.models import Rect


class TestDownscale:
    def test_no_downscale_when_smaller(self):
        img = Image.new("RGB", (800, 600), "red")
        result = _downscale(img, 1280)
        assert result.size == (800, 600)

    def test_downscale_when_larger(self):
        img = Image.new("RGB", (2560, 1440), "red")
        result = _downscale(img, 1280)
        assert result.width == 1280
        assert result.height == 720  # Maintains aspect ratio

    def test_exact_match_no_downscale(self):
        img = Image.new("RGB", (1280, 720), "red")
        result = _downscale(img, 1280)
        assert result.size == (1280, 720)


class TestEncode:
    def test_encode_png(self):
        img = Image.new("RGB", (100, 100), "blue")
        b64, w, h = _encode(img, "png", 75)
        assert w == 100
        assert h == 100
        decoded = base64.b64decode(b64)
        result = Image.open(io.BytesIO(decoded))
        assert result.format == "PNG"

    def test_encode_jpeg(self):
        img = Image.new("RGB", (100, 100), "green")
        b64, w, h = _encode(img, "jpeg", 50)
        assert w == 100
        decoded = base64.b64decode(b64)
        result = Image.open(io.BytesIO(decoded))
        assert result.format == "JPEG"


class TestCompareCaptures:
    def test_identical_images(self):
        img = Image.new("RGB", (100, 100), "red")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()

        result = compare_captures(b64, b64)
        assert result.diff_percentage == 0.0
        assert result.changed_region is None

    def test_different_images(self):
        img1 = Image.new("RGB", (100, 100), "red")
        img2 = Image.new("RGB", (100, 100), "blue")

        buf1 = io.BytesIO()
        img1.save(buf1, format="PNG")
        b64_1 = base64.b64encode(buf1.getvalue()).decode()

        buf2 = io.BytesIO()
        img2.save(buf2, format="PNG")
        b64_2 = base64.b64encode(buf2.getvalue()).decode()

        result = compare_captures(b64_1, b64_2)
        assert result.diff_percentage == 100.0
        assert result.changed_region is not None
        assert result.changed_region.width == 100

    def test_partial_diff(self):
        img1 = Image.new("RGB", (100, 100), "white")
        img2 = img1.copy()
        # Change a 10x10 region
        for x in range(10):
            for y in range(10):
                img2.putpixel((x, y), (0, 0, 0))

        buf1 = io.BytesIO()
        img1.save(buf1, format="PNG")
        b64_1 = base64.b64encode(buf1.getvalue()).decode()

        buf2 = io.BytesIO()
        img2.save(buf2, format="PNG")
        b64_2 = base64.b64encode(buf2.getvalue()).decode()

        result = compare_captures(b64_1, b64_2)
        assert 0 < result.diff_percentage < 100
        assert result.changed_region is not None
        assert result.changed_region.x == 0
        assert result.changed_region.y == 0
