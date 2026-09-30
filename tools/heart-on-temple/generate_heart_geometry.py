#!/usr/bin/env python3
"""Generates the geometry of the three dungeon heart tiers (see heart_shape.py for the shape).

Writes DungeonHeart<Tier>.geo into the output folder, a plain text file that build_heart_on_temple.cpp packs
into the .mesh files. The coordinates are already the game's (Z up), the heart's apex touches the pedestal's
top step. Lines:
  pivot x y z         centre of the heart, the pivot of the pulse
  sub <name>          starts a submesh: "flesh" (heart material) or "iron" (the pedestal's metal material)
  v x y z nx ny nz u v w   vertex; w is the weight of the "Pulse" bone (the rest belongs to the "Root" bone)
  f a b c             triangle (indices count from 0 inside the submesh)

Usage: python generate_heart_geometry.py <output folder>
Needs numpy.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import heart_shape as hs

STEP_Z = 0.418      # top step of the pedestal
APEX_Z = 0.42       # the apex of the heart sits on it
LEVEL = 4           # subdivisions of the body's icosphere
VEIN_SAMPLES = 22   # points along a vein
VEIN_SCALE = 1.3    # thickness of the raised veins relative to VEINS in heart_shape.py


class Submesh:
    def __init__(self):
        self.pos = []
        self.nrm = []
        self.uv = []
        self.w = []
        self.tris = []
        self.count = 0

    def add(self, pos, nrm, uv, w):
        pos = np.asarray(pos, dtype=float)
        start = self.count
        self.pos.append(pos)
        self.nrm.append(np.asarray(nrm, dtype=float))
        self.uv.append(np.asarray(uv, dtype=float))
        self.w.append(np.broadcast_to(np.asarray(w, dtype=float), (len(pos),)).copy())
        self.count += len(pos)
        return start

    def add_tris(self, tris):
        self.tris.append(np.asarray(tris, dtype=np.int64))

    def arrays(self):
        return (np.vstack(self.pos), np.vstack(self.nrm), np.vstack(self.uv), np.concatenate(self.w),
                np.vstack(self.tris))


def icosphere(level):
    t = (1.0 + 5.0 ** 0.5) / 2.0
    v = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
         (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
         (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10),
         (8, 6, 7), (9, 8, 1)]
    v = [tuple(np.array(p, dtype=float) / np.linalg.norm(p)) for p in v]
    for _ in range(level):
        cache = {}
        nf = []

        def mid(a, b):
            key = (min(a, b), max(a, b))
            if key not in cache:
                m = np.array(v[a]) + np.array(v[b])
                v.append(tuple(m / np.linalg.norm(m)))
                cache[key] = len(v) - 1
            return cache[key]
        for a, b, c in f:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        f = nf
    return np.array(v), np.array(f)


def rotation(ax, ay):
    cx, sx, cy, sy = np.cos(ax), np.sin(ax), np.cos(ay), np.sin(ay)
    rz = np.array([[cx, -sx, 0], [sx, cx, 0], [0, 0, 1]])
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    return ry @ rz


def pulse_weight(z, apex_z):
    return hs.smoothstep(0.15, 1.10, z - apex_z)


def add_spherical(mesh, pos, nrm, tris, w):
    """Adds vertices with the spherical texture coordinates; triangles across the u seam get shifted copies."""
    u, v = hs.uv_from_direction(pos)
    base = mesh.add(pos, nrm, np.stack([u, v], axis=1), w)
    tris = np.asarray(tris) + base
    local = tris - base
    cu = u[local]
    crossing = (cu.max(axis=1) - cu.min(axis=1)) > 0.5
    shifted = (cu < 0.5) & crossing[:, None]
    ids = np.unique(local[shifted])
    if len(ids):
        copy = mesh.add(pos[ids], nrm[ids], np.stack([u[ids] + 1.0, v[ids]], axis=1), w[ids])
        lookup = {int(i): copy + k for k, i in enumerate(ids)}
        for t, k in zip(*np.nonzero(shifted)):
            tris[t, k] = lookup[int(local[t, k])]
    mesh.add_tris(tris)


def frames_for(points):
    """Parallel transport frames along a polyline: tangents, normals, binormals."""
    tangents = np.gradient(points, axis=0)
    tangents = hs.unit(tangents)
    normal = np.cross(tangents[0], [0.0, 0.0, 1.0])
    if np.linalg.norm(normal) < 1.0e-3:
        normal = np.cross(tangents[0], [1.0, 0.0, 0.0])
    normals = []
    for t in tangents:
        normal = normal - t * (normal @ t)
        normal = normal / np.linalg.norm(normal)
        normals.append(normal)
    normals = np.array(normals)
    return tangents, normals, np.cross(tangents, normals)


def sweep(points, ra, rb, sides, normals=None, binormals=None, closed=False):
    """Vertices (positions, normals, u along the ring, s along the path) and triangles of a tube; a ring has sides + 1 columns."""
    points = np.asarray(points)
    if normals is None:
        _, normals, binormals = frames_for(points)
    ra = np.broadcast_to(np.asarray(ra, dtype=float), (len(points),))
    rb = np.broadcast_to(np.asarray(rb, dtype=float), (len(points),))
    angles = np.linspace(0.0, 2.0 * np.pi, sides + 1)
    ca, sa = np.cos(angles), np.sin(angles)
    pos = (points[:, None, :] + (ca[None, :, None] * normals[:, None, :] * ra[:, None, None])
           + (sa[None, :, None] * binormals[:, None, :] * rb[:, None, None]))
    nrm = hs.unit((ca[None, :, None] * normals[:, None, :] / ra[:, None, None])
                  + (sa[None, :, None] * binormals[:, None, :] / rb[:, None, None]))
    u = np.broadcast_to(angles / (2.0 * np.pi), (len(points), sides + 1))
    s = np.broadcast_to(np.linspace(0.0, 1.0, len(points))[:, None], (len(points), sides + 1))
    rings = len(points)
    index = np.arange(rings * (sides + 1)).reshape(rings, sides + 1)
    tris = []
    last = rings if closed else rings - 1
    for i in range(last):
        a = index[i]
        b = index[(i + 1) % rings]
        for j in range(sides):
            tris.append((a[j], a[j + 1], b[j]))
            tris.append((a[j + 1], b[j + 1], b[j]))
    return pos.reshape(-1, 3), nrm.reshape(-1, 3), u.reshape(-1), s.reshape(-1), np.array(tris)


def lerp_radius(r0, r1, count):
    return np.linspace(r0, r1, count)


def add_veins(flesh, heart, apex_z):
    for r0, r1, control in hs.VEINS:
        path = hs.path_points(heart.f, control, VEIN_SAMPLES)
        normals = hs.gradient(heart.f, path)
        radii = lerp_radius(r0 * VEIN_SCALE, r1 * VEIN_SCALE, len(path))
        radii[-1] *= 0.5
        centre = path + normals * (0.32 * radii[:, None])
        # the tube keeps the surface normal as its own "up", so that it lies flat on the surface
        tangents = hs.unit(np.gradient(centre, axis=0))
        binormals = hs.unit(np.cross(tangents, normals))
        nrm_frame = hs.unit(np.cross(binormals, tangents))
        pos, nrm, _, _, tris = sweep(centre, radii, radii, 6, nrm_frame, binormals)
        add_spherical(flesh, pos, nrm, tris, pulse_weight(pos[:, 2], apex_z))


def add_vessels(flesh, apex_z):
    for r0, r1, control in hs.VESSELS:
        centre = hs.catmull_rom(np.array(control, dtype=float), 12)
        radii = lerp_radius(r0, r1, len(centre))
        tangents, normals, binormals = frames_for(centre)
        pos, nrm, u, s, tris = sweep(centre, radii, radii, 12, normals, binormals)
        v = hs.WALL_V[0] + (hs.WALL_V[1] - hs.WALL_V[0]) * s
        base = flesh.add(pos, nrm, np.stack([u * 2.0, v], axis=1), 1.0)
        flesh.add_tris(tris + base)
        end, t_end, n_end, b_end = centre[-1], tangents[-1], normals[-1], binormals[-1]
        # lip: a torus around the opening
        lip_r, lip_minor = 0.86 * r1, 0.17 * r1
        ring_angles = np.linspace(0.0, 2.0 * np.pi, 25)
        ring = end + lip_r * (np.cos(ring_angles)[:, None] * n_end + np.sin(ring_angles)[:, None] * b_end)
        out_n = hs.unit(ring - end)
        pos, nrm, u, s, tris = sweep(ring, lip_minor, lip_minor, 8, out_n, np.broadcast_to(t_end, ring.shape))
        rim_v = 0.5 * (hs.RIM_V[0] + hs.RIM_V[1])
        base = flesh.add(pos, nrm, np.stack([u * 2.0, np.full(len(u), rim_v)], axis=1), 1.0)
        flesh.add_tris(tris + base)
        # inside: a short wall and the floor of the opening
        inner_r, depth = 0.74 * r1, 0.10
        top = end + inner_r * (np.cos(ring_angles)[:, None] * n_end + np.sin(ring_angles)[:, None] * b_end)
        bottom = top - t_end * depth
        wall_pos = np.vstack([top, bottom])
        wall_nrm = hs.unit(-np.vstack([top - end, bottom - (end - t_end * depth)]))
        wall_uv = np.stack([np.tile(np.linspace(0, 2, 25), 2), np.repeat([hs.HOLE_V[0], hs.HOLE_V[1] - 0.03], 25)], axis=1)
        base = flesh.add(wall_pos, wall_nrm, wall_uv, 1.0)
        wall_tris = []
        for j in range(24):
            wall_tris.append((base + j, base + j + 1, base + 25 + j))
            wall_tris.append((base + j + 1, base + 26 + j, base + 25 + j))
        flesh.add_tris(np.array(wall_tris))
        floor_centre = end - t_end * depth
        floor_pos = np.vstack([floor_centre[None, :], bottom])
        floor_uv = np.vstack([[1.0, hs.HOLE_V[1]], np.stack([np.linspace(0, 2, 25), np.full(25, hs.HOLE_V[1] - 0.03)], axis=1)])
        floor_nrm = np.broadcast_to(t_end, floor_pos.shape)
        base = flesh.add(floor_pos, floor_nrm, floor_uv, 1.0)
        flesh.add_tris(np.array([(base, base + 1 + j, base + 2 + j) for j in range(24)]))


def strap(iron, heart, apex_z, centre, tilt, width, thickness, level_w):
    """A metal strap around the body in a plane through centre, tilted about the x axis; returns the path."""
    angles = np.linspace(0.0, 2.0 * np.pi, 64, endpoint=False)
    plane_y = np.array([0.0, np.cos(tilt), np.sin(tilt)])
    directions = np.cos(angles)[:, None] * np.array([1.0, 0.0, 0.0]) + np.sin(angles)[:, None] * plane_y
    surf = centre + hs.surface(directions, lambda p: heart.f(p + centre), 1.6)
    normals = hs.gradient(heart.f, surf)
    path = surf + normals * (0.8 * thickness)
    path = np.vstack([path, path[:1]])
    normals = np.vstack([normals, normals[:1]])
    tangents = hs.unit(np.gradient(path, axis=0))
    binormals = hs.unit(np.cross(tangents, normals))
    nrm_frame = hs.unit(np.cross(binormals, tangents))
    pos, nrm, u, s, tris = sweep(path, thickness, width, 8, nrm_frame, binormals, closed=False)
    total = np.linalg.norm(np.diff(path, axis=0), axis=1).sum()
    base = iron.add(pos, nrm, np.stack([s * total * 1.5, u * 0.5], axis=1), level_w)
    iron.add_tris(tris + base)
    return path, normals


def add_rivets(iron, path, normals, count, radius, weight):
    unit_pos, unit_faces = icosphere(1)
    picks = np.linspace(0, len(path) - 2, count).astype(int)
    for i in picks:
        centre = path[i] + normals[i] * 0.05
        pos = centre + unit_pos * radius
        base = iron.add(pos, unit_pos, np.stack([unit_pos[:, 0] * 0.5 + 0.5, unit_pos[:, 1] * 0.5 + 0.5], axis=1), weight)
        iron.add_tris(unit_faces + base)


def add_cradle(iron, heart, apex_local, apex_z):
    """A collar around the lowest part of the body and four struts down to the step."""
    ring_z = apex_local[2] + 0.30
    centre = np.array([apex_local[0], apex_local[1], ring_z])
    angles = np.linspace(0.0, 2.0 * np.pi, 33)
    dirs = np.stack([np.cos(angles), np.sin(angles), np.zeros_like(angles)], axis=1)
    surf = centre + hs.surface(dirs, lambda p: heart.f(p + centre), 1.0)
    out = dirs
    path = surf + out * 0.03
    binorm = np.broadcast_to(np.array([0.0, 0.0, 1.0]), path.shape)
    pos, nrm, u, s, tris = sweep(path, 0.05, 0.065, 8, out, binorm, closed=False)
    base = iron.add(pos, nrm, np.stack([s * 3.0, u * 0.5], axis=1), 0.0)
    iron.add_tris(tris + base)
    for k in range(4):
        angle = np.pi / 4.0 + k * np.pi / 2.0
        d = np.array([np.cos(angle), np.sin(angle), 0.0])
        top = centre + hs.surface(d[None, :], lambda p: heart.f(p + centre), 1.0)[0] + d * 0.03
        foot = top + d * 0.10
        foot[2] = apex_local[2]
        strut = np.linspace(top, foot, 5)
        tangents = hs.unit(np.gradient(strut, axis=0))
        n2 = hs.unit(np.cross(tangents, [0.0, 0.0, 1.0]))
        b2 = hs.unit(np.cross(tangents, n2))
        pos, nrm, u, s, tris = sweep(strut, 0.042, 0.042, 6, n2, b2)
        base = iron.add(pos, nrm, np.stack([u, s], axis=1), 0.0)
        iron.add_tris(tris + base)


def build(tier):
    heart = hs.Heart(tier)
    flesh = Submesh()
    iron = Submesh()
    dirs, tris = icosphere(LEVEL)
    dirs = dirs @ rotation(0.043, 0.061).T
    body = hs.surface(dirs, heart.f)
    normals = hs.gradient(heart.f, body)
    apex_local = body[np.argmin(body[:, 2])]
    apex_z = apex_local[2]
    add_spherical(flesh, body, normals, tris, pulse_weight(body[:, 2], apex_z))
    add_veins(flesh, heart, apex_z)
    add_vessels(flesh, apex_z)
    band_path, band_normals = strap(iron, heart, apex_z, np.array([0.0, 0.0, -0.05]), 0.22, 0.095, 0.060, 1.0)
    add_rivets(iron, band_path, band_normals, 14, 0.062, 1.0)
    add_cradle(iron, heart, apex_local, apex_z)
    return heart, flesh, iron, apex_local


def place(mesh_arrays, scale, apex_local, offset_z):
    pos, nrm, uv, w, tris = mesh_arrays
    pos = apex_local + scale * (pos - apex_local)
    pos = pos + np.array([0.0, 0.0, offset_z])
    return pos, nrm, uv, w, tris


def write_geo(path, pivot, subs):
    with open(path, 'w') as out:
        out.write('pivot %.5f %.5f %.5f\n' % tuple(pivot))
        for name, (pos, nrm, uv, w, tris) in subs:
            out.write('sub %s\n' % name)
            for p, n, t, k in zip(pos, nrm, uv, w):
                out.write('v %.5f %.5f %.5f %.4f %.4f %.4f %.5f %.5f %.4f\n' % (p[0], p[1], p[2], n[0], n[1], n[2], t[0], t[1], k))
            for a, b, c in tris:
                out.write('f %d %d %d\n' % (a, b, c))


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for tier in hs.TIERS:
        heart, flesh, iron, apex_local = build(tier)
        scale = hs.TIER_SCALE[tier]
        offset_z = APEX_Z - apex_local[2]
        subs = [('flesh', place(flesh.arrays(), scale, apex_local, offset_z)),
                ('iron', place(iron.arrays(), scale, apex_local, offset_z))]
        pivot = apex_local + scale * (np.zeros(3) - apex_local) + np.array([0.0, 0.0, offset_z])
        write_geo(os.path.join(out, 'DungeonHeart%s.geo' % tier), pivot, subs)
        verts = sum(len(s[1][0]) for s in subs)
        faces = sum(len(s[1][4]) for s in subs)
        print('%s: %d vertices, %d triangles, pivot %s, bottom z %.3f' % (tier, verts, faces, np.round(pivot, 3),
              min(s[1][0][:, 2].min() for s in subs)))


if __name__ == '__main__':
    main()
