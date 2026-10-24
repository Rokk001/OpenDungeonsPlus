#!/usr/bin/env python3
"""Check the complete loading-picture set against the production selector."""
from pathlib import Path
import re
import struct


# Read JPEG frame dimensions without requiring an optional image package.
def jpeg_dimensions(path):
    data = path.read_bytes()
    if data[:2] != b"\xff\xd8":
        raise AssertionError(f"not a JPEG: {path}")
    offset = 2
    while offset < len(data):
        if data[offset] != 0xFF:
            raise AssertionError(f"invalid JPEG marker: {path}")
        while data[offset] == 0xFF:
            offset += 1
        marker = data[offset]
        offset += 1
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            continue
        length = struct.unpack_from(">H", data, offset)[0]
        if marker in (0xC0, 0xC1, 0xC2):
            height, width = struct.unpack_from(">HH", data, offset + 3)
            return width, height
        offset += length
    raise AssertionError(f"missing JPEG dimensions: {path}")


# Verify every named selector entry, every asset and the requested total size limit.
def main():
    root = Path(__file__).resolve().parents[2]
    source = (root / "source/render/LoadingScreen.cpp").read_text(encoding="utf-8")
    table = source.split("const char* const LOADING_TEXTURES[] = {", 1)[1].split("};", 1)[0]
    names = re.findall(r'"(loading_\d{2}\.jpg)"', table)
    expected = [f"loading_{number:02d}.jpg" for number in range(1, 26)]
    assert names == expected, "selector must reference exactly the 25 loading pictures"
    folder = root / "materials/textures/loading"
    assert sorted(path.name for path in folder.glob("*.jpg")) == expected, "loading picture set is incomplete"
    total = 0
    for name in names:
        path = folder / name
        assert jpeg_dimensions(path) == (1920, 1080), f"wrong dimensions: {name}"
        total += path.stat().st_size
    assert total < 25_000_000, f"loading picture set exceeds 25 MB: {total}"
    resources = (root / "cmake/config/resources.cfg.in").read_text(encoding="utf-8")
    assert "FileSystem=materials/textures/loading" in resources, "loading images must be discoverable by Ogre"
    print(f"OK: 25 referenced loading pictures, 1920x1080, {total} bytes")


if __name__ == "__main__":
    main()
