"""Ectoplasm in the ghost cauldron (owner decision 998 point 6).

The liquid in the cauldron mouth was one flat, untextured GhostEctoplasm disc. This tool gives it a look of its own
without touching the rest of the accepted cauldron or the trap seat:

- textures: paints the swirl texture GhostCauldronEctoplasm.png (512 px, the disc spans the inscribed circle, so the
  material can turn it round the centre) and the tileable glint/bubble layer GhostCauldronEctoGlint.png (256 px);
- meshes: moves the mouth surface of GhostCauldron.mesh (every GhostEctoplasm triangle below z 1.06; the trap seat glow
  at z 1.1 stays GhostEctoplasm) into a submesh of its own with the material GhostCauldronEctoplasm and planar UVs
  centred on the mouth, and gives the window fill GhostCauldronFill.mesh the same material and planar UVs at the same
  texture scale. Positions, normals, indices, bone assignments, bounds and the skeleton link stay byte for byte.

Run with any Python 3 that has numpy and Pillow: python tools/gen_ghost_cauldron_ectoplasm.py [textures] [meshes]
The mesh step refuses to run twice (it needs the GhostEctoplasm export as input).
"""
from pathlib import Path
import struct
import sys

import numpy as np
from PIL import Image

repo = Path(__file__).resolve().parents[1]
MATERIAL = b'GhostCauldronEctoplasm'
SEAT_Z = 1.06            # mouth surface z 1.019 to 1.049, trap seat glow z 1.1 (decision 894 export)
MOUTH_RADIUS = 0.565     # measured mouth surface radius around (0, 0)
UV_SPAN = 2*MOUTH_RADIUS # one texture width per mouth diameter, also in the window fill
FILL_MID_Z = 0.30        # middle of the 0.6 high fill column


# Smooth value noise: random grid bicubically enlarged, several octaves.
def fbm(size, seed, octaves=5, base=4):
    rng = np.random.default_rng(seed)
    total = np.zeros((size, size))
    amplitude, weight = 1.0, 0.0
    for octave in range(octaves):
        cells = base*2**octave
        grid = rng.random((cells, cells)).astype(np.float32)
        layer = np.asarray(Image.fromarray(grid, 'F').resize((size, size), Image.BICUBIC))
        total += amplitude*layer
        weight += amplitude
        amplitude *= 0.5
    total /= weight
    return (total-total.min())/(total.max()-total.min())


# Periodic noise (tiles seamlessly): white noise filtered in frequency space.
def periodic_noise(size, seed, falloff):
    rng = np.random.default_rng(seed)
    spectrum = np.fft.fft2(rng.standard_normal((size, size)))
    fx = np.fft.fftfreq(size)[:, None]
    fy = np.fft.fftfreq(size)[None, :]
    radius = np.sqrt(fx*fx+fy*fy)*size
    field = np.real(np.fft.ifft2(spectrum*np.exp(-(radius/falloff)**2)))
    return (field-field.min())/(field.max()-field.min())


def smoothstep(a, b, x):
    t = np.clip((x-a)/(b-a), 0.0, 1.0)
    return t*t*(3-2*t)


# Base layer: slow green ectoplasm swirling round the centre, glowing core, darker meniscus, sunk bubbles.
def swirl_texture(size=512):
    axis = (np.arange(size)+0.5)/size*2-1
    x, y = np.meshgrid(axis, -axis)
    r = np.sqrt(x*x+y*y)
    theta = np.arctan2(y, x)
    n1 = fbm(size, 9981)
    n2 = fbm(size, 9982, octaves=6, base=8)
    # The arms fade out towards the centre, where the angle would pinch them into a star.
    centre = smoothstep(0.05, 0.35, r)
    arms = (0.5+0.5*np.sin(5*theta+10*r+3.2*n1))*centre
    veins = np.exp(-((np.sin(3*theta-7*r+4.0*n2)-0.82)/0.16)**2)*centre
    dark = np.array([0.04, 0.22, 0.09])
    mid = np.array([0.16, 0.62, 0.24])
    bright = np.array([0.62, 1.00, 0.52])
    body = dark+(mid-dark)*(0.35+0.65*n2)[..., None]
    body += (bright-mid)*(arms**3*0.55)[..., None]
    body += np.array([0.30, 0.45, 0.25])*(veins*0.45)[..., None]
    body += np.array([0.25, 0.35, 0.18])*np.exp(-r*r/0.10)[..., None]
    body *= (1.0-0.45*smoothstep(0.72, 1.0, r))[..., None]
    rng = np.random.default_rng(9983)
    for _ in range(34):
        angle, distance = rng.random()*2*np.pi, 0.88*np.sqrt(rng.random())
        cx, cy = distance*np.cos(angle), distance*np.sin(angle)
        radius = (4+rng.random()*11)/size*2
        d = np.sqrt((x-cx)**2+(y-cy)**2)/radius
        body *= (1.0-0.25*np.clip(1-d, 0, 1))[..., None]
        body += np.array([0.45, 0.70, 0.40])*(np.exp(-((d-1.0)/0.18)**2)*0.6)[..., None]
        spot = np.sqrt((x-cx+0.35*radius)**2+(y-cy-0.35*radius)**2)/radius
        body += (np.exp(-(spot/0.22)**2)*0.8)[..., None]
    return Image.fromarray((np.clip(body, 0, 1)*255+0.5).astype(np.uint8), 'RGB')


# Additive layer that tiles: wisps of light, bubble rings and sparkles on black, tinted by the material.
def glint_texture(size=256):
    wisps = periodic_noise(size, 9984, 9.0)
    fine = periodic_noise(size, 9985, 26.0)
    value = smoothstep(0.62, 0.86, wisps)*0.55+smoothstep(0.70, 0.92, fine)*0.35
    index = np.arange(size)
    rng = np.random.default_rng(9986)
    for _ in range(34):
        cx, cy = rng.random()*size, rng.random()*size
        radius = 2.5+rng.random()*7.5
        dx = np.minimum(np.abs(index-cx), size-np.abs(index-cx))[None, :]
        dy = np.minimum(np.abs(index-cy), size-np.abs(index-cy))[:, None]
        d = np.sqrt(dx*dx+dy*dy)/radius
        value += np.exp(-((d-1.0)/0.20)**2)*0.75
        sx = np.minimum(np.abs(index-(cx-0.35*radius)%size), size-np.abs(index-(cx-0.35*radius)%size))[None, :]
        sy = np.minimum(np.abs(index-(cy-0.35*radius)%size), size-np.abs(index-(cy-0.35*radius)%size))[:, None]
        value += np.exp(-(sx*sx+sy*sy)/(0.09*radius*radius))
    grey = (np.clip(value, 0, 1)*255+0.5).astype(np.uint8)
    return Image.fromarray(np.stack([grey]*3, -1), 'RGB')


def textures():
    swirl_texture().save(repo/'materials/textures/GhostCauldronEctoplasm.png', optimize=True)
    glint_texture().save(repo/'materials/textures/GhostCauldronEctoGlint.png', optimize=True)


# ---- binary OGRE mesh (MeshSerializer_v1.100, little endian) ----

def chunk(data, at):
    kind, size = struct.unpack_from('<HI', data, at)
    return kind, size


# Split the file into header, mesh chunk children and the chunks after the mesh chunk.
def split_mesh(data):
    head_end = data.index(b'\n', 2)+1
    kind, size = chunk(data, head_end)
    assert kind == 0x3000
    flag = data[head_end+6:head_end+7]
    children, at = [], head_end+7
    while at < head_end+size:
        kind, length = chunk(data, at)
        children.append(bytearray(data[at:at+length]))
        at += length
    return data[:head_end], flag, children, data[head_end+size:]


def join_mesh(head, flag, children, tail):
    body = b''.join(bytes(child) for child in children)
    return head+struct.pack('<HI', 0x3000, 6+1+len(body))+flag+body+tail


# Submesh chunk fields: material, shared flag, index list, raw child chunks (operation type, ...).
def read_submesh(child):
    name_end = child.index(b'\n', 6)
    material = bytes(child[6:name_end])
    shared, count, wide = struct.unpack_from('<?IB', child, name_end+1)
    assert shared, 'cauldron and fill submeshes use the shared vertex buffer'
    start = name_end+1+6
    indices = list(struct.unpack_from(('<%dI' if wide else '<%dH') % count, child, start))
    rest = bytes(child[start+count*(4 if wide else 2):])
    return material, wide, indices, rest


def write_submesh(material, wide, indices, rest):
    body = material+b'\n'+struct.pack('<?IB', True, len(indices), wide)
    body += struct.pack(('<%dI' if wide else '<%dH') % len(indices), *indices)+rest
    return bytearray(struct.pack('<HI', 0x4000, 6+len(body))+body)


# Offsets of positions and of the first texture coordinate set in the shared geometry chunk.
def geometry_layout(geometry):
    count = struct.unpack_from('<I', geometry, 6)[0]
    elements, buffers, at = [], {}, 10
    while at < len(geometry):
        kind, size = chunk(geometry, at)
        if kind == 0x5100:
            inner = at+6
            while inner < at+size:
                _, inner_size = chunk(geometry, inner)
                elements.append(struct.unpack_from('<5H', geometry, inner+6))
                inner += inner_size
        elif kind == 0x5200:
            binding, stride = struct.unpack_from('<HH', geometry, at+6)
            buffers[binding] = (stride, at+16)
        at += size
    def place(semantic, kind):
        source, element_type, _, offset, _ = next(e for e in elements if e[2] == semantic and e[4] == 0)
        assert element_type == kind, (semantic, element_type)
        stride, start = buffers[source]
        return lambda index: start+index*stride+offset
    return count, place(1, 2), place(7, 1)


def planar_uvs(geometry, vertices, project):
    _, position, uv = geometry_layout(geometry)
    for index in vertices:
        x, y, z = struct.unpack_from('<3f', geometry, position(index))
        struct.pack_into('<2f', geometry, uv(index), *project(x, y, z))


def cauldron():
    path = repo/'models/GhostCauldron.mesh'
    head, flag, children, tail = split_mesh(path.read_bytes())
    geometry = next(child for child in children if chunk(child, 0)[0] == 0x5000)
    _, position, _ = geometry_layout(geometry)
    names = [read_submesh(child)[0] if chunk(child, 0)[0] == 0x4000 else None for child in children]
    assert MATERIAL not in names, 'mesh step already applied'
    slot = names.index(b'GhostEctoplasm')
    _, wide, indices, rest = read_submesh(children[slot])
    seat, mouth = [], []
    for corner in range(0, len(indices), 3):
        triangle = indices[corner:corner+3]
        low = all(struct.unpack_from('<3f', geometry, position(index))[2] < SEAT_Z for index in triangle)
        (mouth if low else seat).extend(triangle)
    assert seat and mouth and not set(seat) & set(mouth)
    planar_uvs(geometry, set(mouth), lambda x, y, z: (0.5+x/UV_SPAN, 0.5-y/UV_SPAN))
    children[slot] = write_submesh(b'GhostEctoplasm', wide, seat, rest)
    children.insert(slot+1, write_submesh(MATERIAL, wide, mouth, rest))
    path.write_bytes(join_mesh(head, flag, children, tail))


def fill():
    path = repo/'models/GhostCauldronFill.mesh'
    head, flag, children, tail = split_mesh(path.read_bytes())
    geometry = next(child for child in children if chunk(child, 0)[0] == 0x5000)
    slot = next(i for i, child in enumerate(children) if chunk(child, 0)[0] == 0x4000)
    material, wide, indices, rest = read_submesh(children[slot])
    assert material == b'GhostEctoplasm', 'mesh step already applied'
    planar_uvs(geometry, set(indices), lambda x, y, z: (0.5+x/UV_SPAN, 0.5-(z-FILL_MID_Z)/UV_SPAN))
    children[slot] = write_submesh(MATERIAL, wide, indices, rest)
    path.write_bytes(join_mesh(head, flag, children, tail))


if __name__ == '__main__':
    steps = sys.argv[1:] or ['textures', 'meshes']
    if 'textures' in steps:
        textures()
    if 'meshes' in steps:
        cauldron()
        fill()
