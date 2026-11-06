#!/usr/bin/env python3
"""Remove the dark flat iron backing plate from the ghost room hook meshes.

Owner check build 40 (decision 697) still saw dark flat panels at the ghost room wall: they were the
"Worn hook backing" plates (0.34 x 0.80 dark iron board, assets-src/rooms/ghostroom/create_models.py hook())
behind every GhostHook and GhostHookEmpty. The hook, its two brass wall bolts and the backpack stay.

The backing is the only GhostIron part of a hook that lies in the rear 0.07 of the iron depth and away from the
centre line (the forged hook and the pack straps are narrow or further forward). Its triangles are made degenerate
in the index buffer, so the chunk layout, the bounds and the placement depth of the mesh stay unchanged.
The script is idempotent; run it again after any Blender rebuild of the hook meshes.

Usage: strip_ghost_hook_backing.py [REPO]
"""
import struct
import sys
from pathlib import Path

MESHES = ("GhostHook", "GhostHookEmpty")
BACK_DEPTH = 0.07
SIDE = 0.1


# Read a newline-terminated OGRE string.
def ogre_string(data, position):
    end = data.index(b"\n", position)
    return data[position:end].decode("utf-8"), end + 1


# Return the shared vertex positions of a binary OGRE mesh and the (offset, count, wide, material) of each index buffer.
def layout(data):
    _, position = ogre_string(data, 2)
    kind, length = struct.unpack_from("<HI", data, position)
    assert kind == 0x3000
    positions, submeshes = None, []
    cursor = position + 7
    while cursor < position + length:
        kind, size = struct.unpack_from("<HI", data, cursor)
        if kind == 0x4000:
            material, inner = ogre_string(data, cursor + 6)
            shared, count, wide = struct.unpack_from("<BIB", data, inner)
            assert shared == 1, material
            start = inner + 6
            after = start + count * (4 if wide else 2)
            operation = 4
            while after < cursor + size:
                child, child_size = struct.unpack_from("<HI", data, after)
                if child == 0x4010:
                    operation = struct.unpack_from("<H", data, after + 6)[0]
                after += child_size
            assert operation == 4, (material, operation)
            submeshes.append((start, count, wide, material))
        elif kind == 0x5000:
            vertices = struct.unpack_from("<I", data, cursor + 6)[0]
            inner, elements, buffers = cursor + 10, [], {}
            while inner < cursor + size:
                child, child_size = struct.unpack_from("<HI", data, inner)
                if child == 0x5100:
                    element = inner + 6
                    while element < inner + child_size:
                        _, element_size = struct.unpack_from("<HI", data, element)
                        elements.append(struct.unpack_from("<5H", data, element + 6))
                        element += element_size
                elif child == 0x5200:
                    binding, stride = struct.unpack_from("<HH", data, inner + 6)
                    buffers[binding] = (stride, inner + 16)
                inner += child_size
            source, _, _, offset, _ = next(element for element in elements if element[2] == 1)
            stride, begin = buffers[source]
            positions = [struct.unpack_from("<3f", data, begin + index * stride + offset) for index in range(vertices)]
        cursor += size
    return positions, submeshes


# Return the visible triangles of a submesh as (first index position, (a, b, c)).
def triangles(data, start, count, wide):
    indices = struct.unpack_from(("<%dI" if wide else "<%dH") % count, data, start)
    for first in range(0, count, 3):
        tri = indices[first:first + 3]
        if len(set(tri)) == 3:
            yield first, tri


# Return the backing triangles of one hook mesh: rear iron triangles that lie fully off the centre line.
def backing(data):
    positions, submeshes = layout(data)
    found = []
    for start, count, wide, material in submeshes:
        if material != "GhostIron":
            continue
        indices = struct.unpack_from(("<%dI" if wide else "<%dH") % count, data, start)
        rear = min(positions[index][1] for index in indices)
        for first, tri in triangles(data, start, count, wide):
            if all(abs(positions[i][0]) > SIDE and positions[i][1] < rear + BACK_DEPTH for i in tri):
                found.append((start, first, wide, tri))
    return found


# Degenerate every backing triangle of the given mesh file and return how many were removed.
def strip(path):
    data = bytearray(path.read_bytes())
    found = backing(bytes(data))
    for start, first, wide, tri in found:
        struct.pack_into("<3I" if wide else "<3H", data, start + first * (4 if wide else 2), tri[0], tri[0], tri[0])
    if found:
        path.write_bytes(bytes(data))
    return len(found)


def main():
    repo = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
    for name in MESHES:
        print(name, strip(repo / "models" / (name + ".mesh")), "backing triangles removed")


if __name__ == "__main__":
    main()
