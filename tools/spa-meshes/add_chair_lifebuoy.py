#!/usr/bin/env python3
"""Hangs a lifebuoy on the side of the pool attendant's chair (models/SpaChair.mesh), decision 837.

The owner compared the spa with variant 1 of the attendant design (D-7-v2): a red and white life ring hangs at the
lifeguard chair. SpaChair had none. This script reads the OgreXML of the chair (OgreXMLConverter output of the shipped
models/SpaChair.mesh), keeps every existing vertex and face unchanged and adds three submeshes with their own geometry:
the ring in eight alternating segments (SpaLifebuoyRed, SpaLifebuoyWhite) and an iron peg it hangs on (SpaIron, the
chair's existing iron material). The ring hangs upright on the +x side of the chair, beside the seat legs, at the height
of the attendant's lower legs, on a peg in the side rail (x 0.258, z 0.83), so it is seen from the dungeon camera.

Deterministic, no randomness. Original work of the project, licence GPLv3+. Needs only the Python standard library.

Usage: python add_chair_lifebuoy.py <SpaChair.mesh.xml in> <SpaChair.mesh.xml out>
Then: OgreXMLConverter <out> models/SpaChair.mesh
"""

import math
import sys
import xml.etree.ElementTree as ET

# Ring: centre, major radius (middle of the tube), minor radius (tube), all in tiles; the ring stands in the y-z plane
RING_CENTRE = (0.31, 0.04, 0.759)
RING_MAJOR = 0.125
RING_MINOR = 0.042
RING_SEGMENTS = 8          # alternating red and white bands
RING_STEPS_PER_SEGMENT = 6
TUBE_STEPS = 12
# Peg: a short iron rod out of the chair side, the ring hangs on it with the inside of its top
PEG_RADIUS = 0.012
PEG_FROM_X = 0.25
PEG_TO_X = 0.37
PEG_STEPS = 10


def torus_part(first_segment, segments):
    """Vertices and triangles of every second ring segment, starting with first_segment."""
    vertices, faces = [], []
    cx, cy, cz = RING_CENTRE
    for segment in range(first_segment, RING_SEGMENTS, 2):
        base = len(vertices)
        for i in range(RING_STEPS_PER_SEGMENT + 1):
            angle = 2.0 * math.pi * (segment + i / RING_STEPS_PER_SEGMENT) / RING_SEGMENTS
            # Direction from the ring centre to the middle of the tube, in the y-z plane
            dy, dz = math.cos(angle), math.sin(angle)
            for j in range(TUBE_STEPS):
                tube = 2.0 * math.pi * j / TUBE_STEPS
                nx = math.sin(tube)
                radial = math.cos(tube)
                normal = (nx, radial * dy, radial * dz)
                position = (cx + RING_MINOR * nx,
                            cy + (RING_MAJOR + RING_MINOR * radial) * dy,
                            cz + (RING_MAJOR + RING_MINOR * radial) * dz)
                vertices.append((position, normal))
        for i in range(RING_STEPS_PER_SEGMENT):
            for j in range(TUBE_STEPS):
                a = base + i * TUBE_STEPS + j
                b = base + i * TUBE_STEPS + (j + 1) % TUBE_STEPS
                c = base + (i + 1) * TUBE_STEPS + j
                d = base + (i + 1) * TUBE_STEPS + (j + 1) % TUBE_STEPS
                faces.append((a, c, b))
                faces.append((b, c, d))
    return vertices, faces


def peg():
    """A closed cylinder along x through the top of the ring hole."""
    cy = RING_CENTRE[1]
    cz = RING_CENTRE[2] + RING_MAJOR - RING_MINOR - PEG_RADIUS
    vertices, faces = [], []
    for x in (PEG_FROM_X, PEG_TO_X):
        for j in range(PEG_STEPS):
            angle = 2.0 * math.pi * j / PEG_STEPS
            normal = (0.0, math.cos(angle), math.sin(angle))
            vertices.append(((x, cy + PEG_RADIUS * normal[1], cz + PEG_RADIUS * normal[2]), normal))
    for j in range(PEG_STEPS):
        a, b = j, (j + 1) % PEG_STEPS
        faces.append((a, b, PEG_STEPS + a))
        faces.append((b, PEG_STEPS + b, PEG_STEPS + a))
    # The outer end cap
    centre = len(vertices)
    vertices.append(((PEG_TO_X, cy, cz), (1.0, 0.0, 0.0)))
    cap = len(vertices)
    for j in range(PEG_STEPS):
        angle = 2.0 * math.pi * j / PEG_STEPS
        vertices.append(((PEG_TO_X, cy + PEG_RADIUS * math.cos(angle), cz + PEG_RADIUS * math.sin(angle)), (1.0, 0.0, 0.0)))
    for j in range(PEG_STEPS):
        faces.append((centre, cap + j, cap + (j + 1) % PEG_STEPS))
    return vertices, faces


def fmt(value):
    return ('%.6f' % value).rstrip('0').rstrip('.') if value != 0 else '0'


def add_submesh(submeshes, material, vertices, faces):
    submesh = ET.SubElement(submeshes, 'submesh', material=material, usesharedvertices='false',
                            use32bitindexes='false', operationtype='triangle_list')
    faces_element = ET.SubElement(submesh, 'faces', count=str(len(faces)))
    for a, b, c in faces:
        ET.SubElement(faces_element, 'face', v1=str(a), v2=str(b), v3=str(c))
    geometry = ET.SubElement(submesh, 'geometry', vertexcount=str(len(vertices)))
    buffer = ET.SubElement(geometry, 'vertexbuffer', positions='true', normals='true')
    for position, normal in vertices:
        vertex = ET.SubElement(buffer, 'vertex')
        ET.SubElement(vertex, 'position', x=fmt(position[0]), y=fmt(position[1]), z=fmt(position[2]))
        ET.SubElement(vertex, 'normal', x=fmt(normal[0]), y=fmt(normal[1]), z=fmt(normal[2]))


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    tree = ET.parse(sys.argv[1])
    submeshes = tree.getroot().find('submeshes')
    if any(s.get('material', '').startswith('SpaLifebuoy') for s in submeshes):
        print('the chair already has a lifebuoy')
        return 1
    add_submesh(submeshes, 'SpaLifebuoyRed', *torus_part(0, RING_SEGMENTS))
    add_submesh(submeshes, 'SpaLifebuoyWhite', *torus_part(1, RING_SEGMENTS))
    add_submesh(submeshes, 'SpaIron', *peg())
    tree.write(sys.argv[2], encoding='utf-8', xml_declaration=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
