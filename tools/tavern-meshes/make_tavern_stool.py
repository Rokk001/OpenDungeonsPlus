#!/usr/bin/env python3
"""Builds models/TavernStool.mesh, the round stool at the ends of a tavern table (decision 863).

The stool carries the guests whose seated clips rest the body on the seat instead of sitting on legs (spider, roach,
rat, slime, cave hornet, wyvern, tentacles, lava spawn, scarab, the grey creature). Its seat lies at the height of the
bench (0.2575, BENCH_TOP of tools/author_tavern_seats.py), is round with radius 0.16 and 0.035 thick, with an iron band
round its edge; it stands on one turned post and a round foot. The origin is the middle of the floor under the seat, so
RoomTavern places it on the floor point where its guest sits. Materials TavernWood and TavernIron of
materials/scripts/TavernObjects.material; the texture coordinates wrap.

Call (needs OgreXMLConverter on the PATH or in OGRE_XML_CONVERTER):
  python tools/tavern-meshes/make_tavern_stool.py [output directory, default models]
"""
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

SEAT_TOP = 0.2575
SEAT_RADIUS = 0.16
SEAT_THICKNESS = 0.035
SEAT_BEVEL = 0.008
BAND_RADIUS = 0.1625
BAND_TOP = SEAT_TOP - 0.010
BAND_BOTTOM = SEAT_TOP - SEAT_THICKNESS + 0.004
POST_RADIUS = 0.034
POST_WAIST = 0.026
FOOT_RADIUS = 0.115
FOOT_HEIGHT = 0.022
SEGMENTS = 32


class Part:
    """Vertices (position, normal, uv) and triangles of one material."""
    def __init__(self, material):
        self.material = material
        self.triangles = []


VERTICES = []


def vertex(position, normal, uv):
    VERTICES.append((position, normal, uv))
    return len(VERTICES) - 1


def ring(radius, z, normal_of, v):
    indices = []
    for i in range(SEGMENTS + 1):
        a = 2.0 * math.pi * i / SEGMENTS
        x, y = radius * math.cos(a), radius * math.sin(a)
        indices.append(vertex((x, y, z), normal_of(a), (2.0 * i / SEGMENTS, v)))
    return indices


def side(part, profile):
    """A surface of revolution through the (radius, z) points of profile, from the bottom up."""
    rings = []
    for k, (radius, z) in enumerate(profile):
        if k + 1 < len(profile):
            dr, dz = profile[k + 1][0] - radius, profile[k + 1][1] - z
        else:
            dr, dz = radius - profile[k - 1][0], z - profile[k - 1][1]
        length = math.hypot(dr, dz) or 1.0
        nr, nz = dz / length, -dr / length
        rings.append(ring(radius, z, lambda a, nr=nr, nz=nz: (nr * math.cos(a), nr * math.sin(a), nz), z * 4.0))
    for lower, upper in zip(rings, rings[1:]):
        for i in range(SEGMENTS):
            part.triangles.append((lower[i], lower[i + 1], upper[i + 1]))
            part.triangles.append((lower[i], upper[i + 1], upper[i]))


def cap(part, radius, z, up):
    middle = vertex((0.0, 0.0, z), (0.0, 0.0, 1.0 if up else -1.0), (0.5, 0.5))
    edge = []
    for i in range(SEGMENTS + 1):
        a = 2.0 * math.pi * i / SEGMENTS
        x, y = radius * math.cos(a), radius * math.sin(a)
        edge.append(vertex((x, y, z), (0.0, 0.0, 1.0 if up else -1.0), (0.5 + 1.5 * x, 0.5 + 1.5 * y)))
    for i in range(SEGMENTS):
        part.triangles.append((middle, edge[i], edge[i + 1]) if up else (middle, edge[i + 1], edge[i]))


def build():
    wood = Part('TavernWood')
    iron = Part('TavernIron')
    bottom = SEAT_TOP - SEAT_THICKNESS
    # Seat: underside, rounded edge, top
    cap(wood, SEAT_RADIUS - SEAT_BEVEL, bottom, False)
    side(wood, [(SEAT_RADIUS - SEAT_BEVEL, bottom), (SEAT_RADIUS, bottom + SEAT_BEVEL),
                (SEAT_RADIUS, SEAT_TOP - SEAT_BEVEL), (SEAT_RADIUS - SEAT_BEVEL, SEAT_TOP)])
    cap(wood, SEAT_RADIUS - SEAT_BEVEL, SEAT_TOP, True)
    # Iron band round the edge of the seat
    side(iron, [(BAND_RADIUS, BAND_BOTTOM), (BAND_RADIUS + 0.003, BAND_BOTTOM + 0.003),
                (BAND_RADIUS + 0.003, BAND_TOP - 0.003), (BAND_RADIUS, BAND_TOP)])
    # Turned post with a waist, then the round foot
    side(wood, [(POST_RADIUS, FOOT_HEIGHT), (POST_WAIST, 0.09), (POST_WAIST, 0.15), (POST_RADIUS, bottom)])
    side(wood, [(FOOT_RADIUS - 0.006, 0.0), (FOOT_RADIUS, 0.006), (FOOT_RADIUS - 0.01, FOOT_HEIGHT),
                (POST_RADIUS + 0.004, FOOT_HEIGHT)])
    cap(wood, FOOT_RADIUS - 0.006, 0.0, False)
    return [wood, iron]


def xml(parts):
    lines = ['<mesh>', '    <sharedgeometry vertexcount="%d">' % len(VERTICES),
             '        <vertexbuffer positions="true" normals="true" texture_coords="1" texture_coord_dimensions_0="2">']
    for (p, n, uv) in VERTICES:
        lines += ['            <vertex>',
                  '                <position x="%.6f" y="%.6f" z="%.6f" />' % p,
                  '                <normal x="%.6f" y="%.6f" z="%.6f" />' % n,
                  '                <texcoord u="%.6f" v="%.6f" />' % uv,
                  '            </vertex>']
    lines += ['        </vertexbuffer>', '    </sharedgeometry>', '    <submeshes>']
    for part in parts:
        lines += ['        <submesh material="%s" usesharedvertices="true" use32bitindexes="false" operationtype="triangle_list">' % part.material,
                  '            <faces count="%d">' % len(part.triangles)]
        lines += ['                <face v1="%d" v2="%d" v3="%d" />' % t for t in part.triangles]
        lines += ['            </faces>', '        </submesh>']
    lines += ['    </submeshes>', '</mesh>', '']
    return '\n'.join(lines)


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / 'models'
    out.mkdir(parents=True, exist_ok=True)
    target = out / 'TavernStool.mesh.xml'
    target.write_text(xml(build()), encoding='ascii')
    converter = os.environ.get('OGRE_XML_CONVERTER') or shutil.which('OgreXMLConverter') or shutil.which('OgreXMLConverter.exe')
    if converter is None:
        print('OgreXMLConverter not found: wrote only', target)
        return 1
    subprocess.run([converter, '-q', str(target), str(out / 'TavernStool.mesh')], check=True)
    target.unlink()
    log = Path('OgreXMLConverter.log')
    if log.exists():
        log.unlink()
    print('wrote', out / 'TavernStool.mesh', len(VERTICES), 'vertices')
    return 0


if __name__ == '__main__':
    sys.exit(main())
