#!/usr/bin/env python3
"""Checks that no main menu camera flight passes through scene geometry (no compile needed).

The flights of config/mainmenuscene.cfg (outward routes and their reversed return routes)
are sampled the same way RenderSceneMenu::samplePath does (Catmull-Rom through the waypoints)
and every sample is tested against the triangles of every AddEntity mesh at its configured
position. A sample closer than CLEARANCE to a triangle fails the check.
"""
import math
import os
import struct
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONFIG = os.path.join(ROOT, "config", "mainmenuscene.cfg")
MODELS = os.path.join(ROOT, "models")
#: Smallest allowed distance in tiles between the camera and any triangle (the gate portcullis slot between two bars is 0.29 wide).
CLEARANCE = 0.08
#: Glowing crack and eye materials are painted onto surfaces and are no obstacle.
DECAL_MATERIALS = ("MenuEmberCrack", "MenuLavaCrack", "MenuGateEyes")
SAMPLES_PER_SEGMENT = 80
#: Triangles narrower than this many tiles are crack lines, not solid geometry.
MIN_SLIVER_HEIGHT = 0.05


def chunks(data, offset, end):
    """Yields (id, payload start, chunk end) of the Ogre chunks between offset and end."""
    while offset + 6 <= end:
        chunk_id, length = struct.unpack_from("<HI", data, offset)
        yield chunk_id, offset + 6, offset + length
        offset += length


def read_geometry(data, start, end):
    """Returns the vertex positions of one Ogre geometry chunk."""
    count, = struct.unpack_from("<I", data, start)
    elements = []
    buffers = {}
    for chunk_id, s, e in chunks(data, start + 4, end):
        if chunk_id == 0x5100:
            for _, s3, _ in chunks(data, s, e):
                source, _, semantic, offset, _ = struct.unpack_from("<HHHHH", data, s3)
                elements.append((source, semantic, offset))
        elif chunk_id == 0x5200:
            bind, stride = struct.unpack_from("<HH", data, s)
            for kind, s3, _ in chunks(data, s + 4, e):
                if kind == 0x5210:
                    buffers[bind] = (stride, s3)
    source, _, offset = [x for x in elements if x[1] == 1][0]
    stride, base = buffers[source]
    return [struct.unpack_from("<3f", data, base + v * stride + offset) for v in range(count)]


def load_mesh(path):
    """Returns (vertices, triangles) of an Ogre binary mesh as numpy arrays, decal submeshes left out."""
    data = open(path, "rb").read()
    offset = data.index(b"\n") + 1
    vertices = []
    triangles = []
    for chunk_id, s, e in chunks(data, offset, len(data)):
        if chunk_id != 0x3000:
            continue
        shared = None
        shared_base = None
        subs = []
        for kind, s2, e2 in chunks(data, s + 1, e):
            if kind == 0x5000:
                shared = read_geometry(data, s2, e2)
            elif kind == 0x4000:
                subs.append((s2, e2))
        for s2, e2 in subs:
            material = data[s2:data.index(b"\n", s2)].decode("ascii")
            p = data.index(b"\n", s2) + 1
            uses_shared = data[p]
            count, = struct.unpack_from("<I", data, p + 1)
            wide = data[p + 5]
            p += 6
            fmt = "<%d%s" % (count, "I" if wide else "H")
            indices = struct.unpack_from(fmt, data, p)
            p += count * (4 if wide else 2)
            if uses_shared:
                if shared_base is None:
                    shared_base = len(vertices)
                    vertices += shared
                base = shared_base
            else:
                base = len(vertices)
                for kind, s3, e3 in chunks(data, p, e2):
                    if kind == 0x5000:
                        vertices += read_geometry(data, s3, e3)
                        break
            if material in DECAL_MATERIALS:
                continue
            triangles += [(base + indices[i], base + indices[i + 1], base + indices[i + 2])
                          for i in range(0, count - 2, 3)]
    return np.array(vertices, dtype=np.float64), np.array(triangles, dtype=np.int64)


def parse_config():
    """Returns (entities {name: (mesh, position)}, poses {name: position}, flights {name: waypoints})."""
    entities = {}
    poses = {}
    flights = {}
    for line in open(CONFIG, encoding="utf-8"):
        words = line.split()
        if not words or words[0].startswith("#"):
            continue
        if words[0] == "AddEntity":
            entities[words[1]] = (words[2], np.array([float(v) for v in words[3:6]]))
        elif words[0] == "Pose":
            poses[words[1]] = np.array([float(v) for v in words[2:5]])
        elif words[0] == "Flight":
            flights[words[1]] = words[3:]
    return entities, poses, flights


def routes(poses, flights):
    """Yields (label, list of positions) for each outward flight, return flight and the arrival."""
    for name, waypoints in flights.items():
        if name == "overview":
            continue
        if name == "arrival":
            yield name, [poses["arrival"]] + [poses[w] for w in waypoints]
            continue
        outward = ["overview"] + waypoints
        yield name + " out", [poses[w] for w in outward]
        yield name + " back", [poses[w] for w in reversed(outward)]


def catmull_rom(points, per_segment):
    """Samples the path like RenderSceneMenu::samplePath (end points repeated)."""
    result = []
    count = len(points)
    for index in range(count - 1):
        first, second = points[index], points[index + 1]
        before = points[max(index - 1, 0)]
        after = points[min(index + 2, count - 1)]
        for step in range(per_segment + 1):
            t = step / float(per_segment)
            result.append(0.5 * ((2 * first) + (-before + second) * t
                                 + (2 * before - 5 * first + 4 * second - after) * t * t
                                 + (-before + 3 * first - 3 * second + after) * t * t * t))
    return np.array(result)


def distance_point_triangles(point, a, b, c):
    """Returns the distances from point to the triangles (a, b, c) (Ericson, closest point)."""
    ab = b - a
    ac = c - a
    ap = point - a
    count = len(a)
    closest = np.zeros((count, 3))
    d1 = np.einsum("ij,ij->i", ab, ap)
    d2 = np.einsum("ij,ij->i", ac, ap)
    bp = point - b
    d3 = np.einsum("ij,ij->i", ab, bp)
    d4 = np.einsum("ij,ij->i", ac, bp)
    cp = point - c
    d5 = np.einsum("ij,ij->i", ab, cp)
    d6 = np.einsum("ij,ij->i", ac, cp)
    vc = d1 * d4 - d3 * d2
    vb = d5 * d2 - d1 * d6
    va = d3 * d6 - d5 * d4
    for i in range(count):
        if d1[i] <= 0 and d2[i] <= 0:
            closest[i] = a[i]
        elif d3[i] >= 0 and d4[i] <= d3[i]:
            closest[i] = b[i]
        elif vc[i] <= 0 and d1[i] >= 0 and d3[i] <= 0:
            closest[i] = a[i] + ab[i] * (d1[i] / (d1[i] - d3[i]))
        elif d6[i] >= 0 and d5[i] <= d6[i]:
            closest[i] = c[i]
        elif vb[i] <= 0 and d2[i] >= 0 and d6[i] <= 0:
            closest[i] = a[i] + ac[i] * (d2[i] / (d2[i] - d6[i]))
        elif va[i] <= 0 and (d4[i] - d3[i]) >= 0 and (d5[i] - d6[i]) >= 0:
            w = (d4[i] - d3[i]) / ((d4[i] - d3[i]) + (d5[i] - d6[i]))
            closest[i] = b[i] + (c[i] - b[i]) * w
        else:
            denom = 1.0 / (va[i] + vb[i] + vc[i])
            closest[i] = a[i] + ab[i] * (vb[i] * denom) + ac[i] * (vc[i] * denom)
    return np.linalg.norm(closest - point, axis=1)


def main():
    entities, poses, flights = parse_config()
    meshes = {}
    world = {}
    for name, (mesh, position) in entities.items():
        if mesh not in meshes:
            meshes[mesh] = load_mesh(os.path.join(MODELS, mesh.replace(".mesh", "") + ".mesh"))
        vertices, triangles = meshes[mesh]
        if len(triangles) == 0:
            continue
        tri = vertices[triangles] + position
        area2 = np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
        longest = np.maximum.reduce([np.linalg.norm(tri[:, 1] - tri[:, 0], axis=1),
                                     np.linalg.norm(tri[:, 2] - tri[:, 1], axis=1),
                                     np.linalg.norm(tri[:, 0] - tri[:, 2], axis=1)])
        # Crack decals are hair-thin slivers (height below MIN_SLIVER_HEIGHT) and are no obstacle.
        tri = tri[area2 > MIN_SLIVER_HEIGHT * np.maximum(longest, 1e-9)]
        if len(tri) == 0:
            continue
        world[name] = (tri[:, 0], tri[:, 1], tri[:, 2], tri.min(axis=1), tri.max(axis=1))
    failures = []
    for label, points in routes(poses, flights):
        samples = catmull_rom(points, SAMPLES_PER_SEGMENT)
        worst = {}
        for sample in samples:
            for name, (a, b, c, low, high) in world.items():
                near = np.all(low - CLEARANCE <= sample, axis=1) & np.all(sample <= high + CLEARANCE, axis=1)
                if not near.any():
                    continue
                distance = distance_point_triangles(sample, a[near], b[near], c[near]).min()
                if distance < CLEARANCE and distance < worst.get(name, (9e9, None))[0]:
                    worst[name] = (distance, sample.copy())
        for name, (distance, sample) in worst.items():
            failures.append("%s: camera within %.2f of %s at (%.1f, %.1f, %.1f)"
                            % (label, distance, name, sample[0], sample[1], sample[2]))
    for line in failures:
        print("FAIL " + line)
    if failures:
        return 1
    print("OK: %d menu routes keep %.2f clearance to %d entities" % (len(list(routes(poses, flights))), CLEARANCE, len(world)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
