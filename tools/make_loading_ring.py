#!/usr/bin/env python3
"""Draw the rotating ember ring of the loading indicator as a 256x256 RGBA PNG."""
import math
import struct
import sys
import zlib
from pathlib import Path

SIZE = 256
CENTER = SIZE / 2.0
SAMPLES = 3
ARC_DEGREES = 270.0


# Return premultiplied RGBA for one sample point of the ring.
def shade(x, y):
    dx = x - CENTER
    dy = y - CENTER
    radius = math.hypot(dx, dy)
    angle = (math.degrees(math.atan2(dx, -dy)) + 360.0) % 360.0
    red = green = blue = alpha = 0.0
    # Soft outer glow along the ember arc.
    if angle <= ARC_DEGREES:
        heat = (angle / ARC_DEGREES) ** 1.5
        glow = math.exp(-((radius - 92.0) / 11.0) ** 2) * heat * 0.55
        red, green, blue, alpha = 1.0 * glow, 0.35 * glow, 0.05 * glow, glow
    # Spikes: long on the four main directions, short on the diagonals.
    for index in range(8):
        phi = math.radians(index * 45.0)
        length = 124.0 if index % 2 == 0 else 112.0
        delta = math.atan2(dx, -dy) - phi
        radial = radius * math.cos(delta)
        lateral = radius * math.sin(delta)
        if 94.0 <= radial <= length and abs(lateral) <= 9.0 * (length - radial) / (length - 94.0):
            shade_value = 0.30 + 0.25 * (1.0 - abs(lateral) / 9.0)
            red, green, blue, alpha = shade_value * 0.95, shade_value * 0.88, shade_value * 0.82, 1.0
    # Metal band, darker at both edges.
    if 84.0 <= radius <= 100.0:
        edge = min(radius - 84.0, 100.0 - radius) / 8.0
        metal = 0.16 + 0.22 * min(1.0, edge * 1.6)
        red, green, blue, alpha = metal * 1.0, metal * 0.92, metal * 0.85, 1.0
        # Ember channel inside the band.
        if angle <= ARC_DEGREES and 88.0 <= radius <= 96.0:
            heat = (angle / ARC_DEGREES) ** 1.5
            core = 1.0 - abs(radius - 92.0) / 4.0
            red = 0.25 + 0.75 * heat * (0.6 + 0.4 * core)
            green = 0.04 + 0.62 * heat * core ** 2
            blue = 0.02 + 0.25 * heat * heat * core ** 2
            alpha = 1.0
    return red, green, blue, alpha


# Average SAMPLES x SAMPLES samples per pixel and write straight (non-premultiplied) RGBA.
def render():
    rows = []
    for py in range(SIZE):
        row = bytearray([0])
        for px in range(SIZE):
            sums = [0.0, 0.0, 0.0, 0.0]
            for sy in range(SAMPLES):
                for sx in range(SAMPLES):
                    values = shade(px + (sx + 0.5) / SAMPLES, py + (sy + 0.5) / SAMPLES)
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


# Write the picture next to the loading screens unless another path is given.
def main():
    root = Path(__file__).resolve().parents[1]
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "materials/textures/loading/loading_ring.png"
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(render(), 9)) + chunk(b"IEND", b"")
    target.write_bytes(png)


if __name__ == "__main__":
    main()
