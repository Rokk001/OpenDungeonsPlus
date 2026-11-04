#!/usr/bin/env python3
"""Draw the thorned iron ring of the loading indicator as 256x256 RGBA PNGs: the empty track and the ember fill."""
import math
import struct
import sys
import zlib
from pathlib import Path

SIZE = 256
CENTER = SIZE / 2.0
SAMPLES = 3
BAND_INNER = 74.0
BAND_OUTER = 102.0
EMBER_INNER = 80.0
EMBER_OUTER = 97.0


# Return premultiplied RGBA for one sample point; with ember the channel is filled all the way round.
def shade(x, y, ember):
    dx = x - CENTER
    dy = y - CENTER
    radius = math.hypot(dx, dy)
    heading = math.atan2(dx, -dy)
    red = green = blue = alpha = 0.0
    # Soft glow around the ember channel, the same strength everywhere.
    if ember:
        glow = math.exp(-((radius - 88.0) / 16.0) ** 2) * 0.55
        red, green, blue, alpha = 1.0 * glow, 0.38 * glow, 0.04 * glow, glow
    # Thorns: long on the four main directions with a flared base, short on the diagonals.
    for index in range(8):
        phi = math.radians(index * 45.0)
        length = 126.0 if index % 2 == 0 else 112.0
        base = 12.0 if index % 2 == 0 else 8.0
        delta = heading - phi
        radial = radius * math.cos(delta)
        lateral = radius * math.sin(delta)
        if 84.0 <= radial <= length and abs(lateral) <= base * (length - radial) / (length - 84.0):
            shade_value = 0.22 + 0.20 * (1.0 - abs(lateral) / base)
            red, green, blue, alpha = shade_value * 0.95, shade_value * 0.88, shade_value * 0.82, 1.0
    # Thick dark iron band, darker at both edges.
    if BAND_INNER <= radius <= BAND_OUTER:
        edge = min(radius - BAND_INNER, BAND_OUTER - radius) / 8.0
        metal = 0.10 + 0.14 * min(1.0, edge * 1.4)
        red, green, blue, alpha = metal * 1.0, metal * 0.92, metal * 0.85, 1.0
        # Continuous ember channel inside the band: no angle dependence, so no gap and no colour step.
        if ember and EMBER_INNER <= radius <= EMBER_OUTER:
            core = 1.0 - abs(radius - 88.0) / 9.0
            grain = 0.5 + 0.5 * math.sin(math.degrees(heading) * 0.9) * math.sin(radius * 1.7)
            hot = min(1.0, core ** 1.5 * (0.85 + 0.15 * grain))
            red = 0.90 + 0.10 * hot
            green = 0.25 + 0.55 * hot
            blue = 0.03 + 0.25 * hot * hot
            alpha = 1.0
    return red, green, blue, alpha


# Average SAMPLES x SAMPLES samples per pixel and write straight (non-premultiplied) RGBA.
def render(ember):
    rows = []
    for py in range(SIZE):
        row = bytearray([0])
        for px in range(SIZE):
            sums = [0.0, 0.0, 0.0, 0.0]
            for sy in range(SAMPLES):
                for sx in range(SAMPLES):
                    values = shade(px + (sx + 0.5) / SAMPLES, py + (sy + 0.5) / SAMPLES, ember)
                    for k in range(4):
                        sums[k] += values[k]
            count = float(SAMPLES * SAMPLES)
            alpha = sums[3] / count
            if alpha <= 0.0:
                row += bytes([0, 0, 0, 0])
                continue
            # Colour of covered samples: sums hold colour already weighted by their own alpha only for glow.
            colour = [min(1.0, sums[k] / count / alpha) for k in range(3)]
            row += bytes([int(c * 255 + 0.5) for c in colour] + [int(min(1.0, alpha) * 255 + 0.5)])
        rows.append(bytes(row))
    return b"".join(rows)


# Encode a PNG chunk.
def chunk(kind, data):
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


# Write the ember fill and the empty track next to the loading screens unless a folder is given.
def main():
    root = Path(__file__).resolve().parents[1]
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "materials/textures/loading"
    for name, ember in (("loading_ring.png", True), ("loading_ring_empty.png", False)):
        png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0))
        png += chunk(b"IDAT", zlib.compress(render(ember), 9)) + chunk(b"IEND", b"")
        (folder / name).write_bytes(png)


if __name__ == "__main__":
    main()
