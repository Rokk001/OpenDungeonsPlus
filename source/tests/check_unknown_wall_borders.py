"""Numerically check shared known/unknown wall edges; no shader compilation or game start."""
from pathlib import Path
from types import SimpleNamespace
import math
import re

ROOT = Path(__file__).resolve().parents[2]


# Read a small GLSL function body without interpreting comments as instructions.
def body(source, name):
    match = re.search(r"(?:float|vec3) " + name + r"\([^)]*\)\s*\{(.*?)\n\}", source, re.S)
    assert match, name
    return re.sub(r"//[^\n]*|/\*.*?\*/", "", match.group(1), flags=re.S)


# Evaluate the scalar arithmetic used by these shader functions, with no builtins.
def evaluate(expression, values):
    return eval(expression.strip(), {"__builtins__": {}}, values)


# Match the cubic interpolation used by the existing GLSL noise and border band.
def smoothstep(low, high, value):
    t = max(0.0, min(1.0, (value - low) / (high - low)))
    return t * t * (3.0 - 2.0 * t)


# Independently calculate the project's deterministic gradient noise at one point.
def perlin(x, y):
    # Each gradient is the same quarter-length vector as randomGradient in GLSL.
    def gradient_dot(ix, iy):
        angle = 29.0 * math.sin(ix * 21.0 + iy * 171 + 89.0) * math.cos(ix * 15.0 * iy * 83.0 + 75.0)
        return (math.cos(angle) * (x - ix) + math.sin(angle) * (y - iy)) / 4.0
    ix, iy = math.floor(x), math.floor(y)
    sx, sy = smoothstep(0, 1, x - ix), smoothstep(0, 1, y - iy)
    bottom = gradient_dot(ix, iy) * (1 - sx) + gradient_dot(ix + 1, iy) * sx
    top = gradient_dot(ix, iy + 1) * (1 - sx) + gradient_dot(ix + 1, iy + 1) * sx
    return (bottom * (1 - sy) + top * sy) / 2.0


# Execute the actual component-wise border expressions from the shared shader source.
def border_fade(point, source):
    code = body(source, "tileBorderFade")
    width = float(re.search(r"#define TILE_BORDER_FADE ([0-9.]+)", source).group(1))
    components = []
    for axis in point:
        values = {"p": axis, "TILE_BORDER_FADE": width, "min": min,
                  "fract": lambda x: x - math.floor(x), "smoothstep": smoothstep}
        for statement in code.split(";"):
            match = re.fullmatch(r"\s*vec2 (\w+) = (.*?)\s*", statement, re.S)
            if match:
                values[match.group(1)] = evaluate(match.group(2), values)
        components.append(values)
    values = {name: SimpleNamespace(x=components[0][name], y=components[1][name])
              for name in components[0] if isinstance(components[0][name], (int, float))}
    expression = re.search(r"return (.*?);", code, re.S).group(1)
    return evaluate(expression, values)


# Interpret the actual deformation statements, including their sequential X/Y updates.
def deform(point, shader, shared):
    pos = SimpleNamespace(x=point[0], y=point[1], z=point[2], xy=point[:2])
    values = {"pos": pos, "tileBorderFade": lambda p: border_fade(p, shared), "perlin": perlin}
    for statement in body(shader, "deform").split(";"):
        statement = statement.strip()
        if not statement or statement == "return pos":
            continue
        local = re.fullmatch(r"float (\w+) = (.*)", statement, re.S)
        update = re.fullmatch(r"pos\.([xy]) \+= (.*)", statement, re.S)
        assert local or update, statement
        if local:
            values[local.group(1)] = evaluate(local.group(2), values)
        else:
            axis = update.group(1)
            setattr(pos, axis, getattr(pos, axis) + evaluate(update.group(2), values))
    return pos.x, pos.y, pos.z


# Check unequal edge tessellations, both coordinate signs, and translated instances.
def check_edges(unknown, known, shared):
    checked = 0
    for cx, cy in [(0, 0), (13, 8), (-7, -4), (-1, 3)]:
        for axis in [0, 1]:
            for side in [-0.5, 0.5]:
                # Neighbours can have extra edge vertices; every support must stay on the same edge.
                for offset in [-0.5, -0.43, -0.17, 0, 0.11, 0.37, 0.5]:
                    point = [cx, cy, 0.82]
                    point[axis] += side
                    point[1 - axis] += offset
                    point = tuple(point)
                    for shader in [unknown, *known]:
                        moved = deform(point, shader, shared)
                        assert max(abs(a - b) for a, b in zip(point, moved)) < 1e-12, (point, moved)
                        checked += 1
    return checked


# Verify the active shared earth deformation and preserve every numerical border assertion.
def main():
    shared = (ROOT / "shaders/PerlinNoise.glsl").read_text()
    # Ordinary earth replaced the independent fog instance/flat mark shader. The exact shared
    # geometry/transform/overlay contract and real mesh edge profiles run before these samples.
    import runpy
    runpy.run_path(str(ROOT / 'source/tests/check_fog_earth_geometry.py'), run_name='__fog_contract__')
    unknown = (ROOT / "shaders/DirtTile.vert").read_text()
    known = [(ROOT / ("shaders/" + name)).read_text() for name in ["DirtTile.vert", "DCW.vert"]]
    assert unknown.index("vec3 P = (worldMatrix * position).xyz") < unknown.index("vec3 PT = deform(P + T)")
    assert 'if(final_color.a > 0.0)' not in unknown
    assert 'P = deform(P)' in unknown
    checked = check_edges(unknown, known, shared)
    interiors = [(0.1, 0.2, 0.8), (4.17, 9.23, 0.7), (-2.21, -3.13, 0.4)]
    for point in interiors:
        assert any(abs(a - b) > 1e-5 for a, b in zip(point, deform(point, unknown, shared)))
        assert deform(point, unknown, shared) == deform(point, known[0], shared)
    # The original missing damping must fail the same numerical edge test.
    mutation = unknown.replace("fade * perlin", "perlin")
    assert mutation != unknown
    try:
        check_edges(mutation, known, shared)
    except AssertionError:
        pass
    else:
        raise AssertionError("undamped mutation passed shared-edge checks")
    print(f"check_unknown_wall_borders ok: {checked} edge samples; interior noise, shared earth/mark geometry, undamped mutation")


if __name__ == "__main__":
    main()
