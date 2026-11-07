"""Check without compiling that the mana still, ghost press and soul forge are created on the client with a visible size.

Owner check build 36 showed only the cauldron: the server added the three apparatuses, but they never entered their tile,
so no seat with vision sent them to the client. This check follows the whole way from the room to the client renderer and
reads the shipped meshes and skeletons to prove the size, the height and the three state clips."""
from pathlib import Path
from collections import defaultdict
import re
import struct

repo = Path(__file__).resolve().parents[2]
APPARATUS_MESHES = ("ManaStill", "GhostPress", "SoulForge")
STATES = ("Working", "Idle", "Locked")


# Read a tracked source using the repository root rather than the caller's directory.
def read(path):
    return (repo / path).read_text(encoding="utf-8")


# Return a complete brace-delimited body that starts at the signature.
def body(text, signature):
    start = text.index(signature)
    opening = text.index("{", start)
    depth, end = 1, opening + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


# Read a newline-terminated OGRE string.
def ogre_string(data, position):
    end = data.index(b"\n", position)
    return data[position:end].decode("utf-8"), end + 1


# Read bounds, submesh materials and vertices, vertex positions and bone assignments of a binary OGRE mesh.
def read_mesh(name):
    data = (repo / "models" / (name + ".mesh")).read_bytes()
    assert struct.unpack_from("<H", data)[0] == 0x1000, name
    version, position = ogre_string(data, 2)
    assert version.startswith("[MeshSerializer_v1"), (name, version)
    kind, length = struct.unpack_from("<HI", data, position)
    assert kind == 0x3000, (name, hex(kind))
    mesh = {"bounds": None, "skeleton": None, "submeshes": [], "positions": None, "assignments": defaultdict(list)}
    cursor = position + 7
    while cursor < position + length:
        kind, size = struct.unpack_from("<HI", data, cursor)
        assert size >= 6, (name, cursor)
        if kind == 0x4000:
            material, inner = ogre_string(data, cursor + 6)
            count, wide = struct.unpack_from("<IB", data, inner + 1)
            indices = struct.unpack_from(("<%dI" if wide else "<%dH") % count, data, inner + 6)
            mesh["submeshes"].append((material, set(indices)))
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
            stride, start = buffers[source]
            mesh["positions"] = [struct.unpack_from("<3f", data, start + index * stride + offset) for index in range(vertices)]
        elif kind == 0x6000:
            mesh["skeleton"], _ = ogre_string(data, cursor + 6)
        elif kind == 0x7000:
            vertex, bone, weight = struct.unpack_from("<IHf", data, cursor + 6)
            mesh["assignments"][vertex].append((bone, weight))
        elif kind == 0x9000:
            mesh["bounds"] = struct.unpack_from("<7f", data, cursor + 6)
        cursor += size
    return mesh


# Read bones, parents and the first key scale of every track of every clip of a binary OGRE skeleton.
def read_skeleton(name):
    data = (repo / "models" / name).read_bytes()
    _, position = ogre_string(data, 2)
    bones, parents, clips = {}, {}, {}
    while position < len(data):
        kind, size = struct.unpack_from("<HI", data, position)
        if kind == 0x2000:
            # OGRE leaves the bone name out of the chunk length
            bone, inner = ogre_string(data, position + 6)
            handle = struct.unpack_from("<H", data, inner)[0]
            end = position + size + (inner - (position + 6))
            scale = struct.unpack_from("<3f", data, inner + 30) if end - (inner + 30) >= 12 else (1.0, 1.0, 1.0)
            bones[handle] = (bone, scale)
            position = end
            continue
        if kind == 0x3000:
            child, parent = struct.unpack_from("<HH", data, position + 6)
            parents[child] = parent
        elif kind == 0x4000:
            clip, inner = ogre_string(data, position + 6)
            inner += 4
            tracks = {}
            while inner < position + size:
                child, child_size = struct.unpack_from("<HI", data, inner)
                if child == 0x4100:
                    bone = struct.unpack_from("<H", data, inner + 6)[0]
                    key, scales = inner + 8, []
                    while key < inner + child_size:
                        key_kind, key_size = struct.unpack_from("<HI", data, key)
                        if key_kind == 0x4110:
                            scales.append(struct.unpack_from("<3f", data, key + 38) if key_size >= 50 else (1.0, 1.0, 1.0))
                        key += key_size
                    tracks[bone] = scales
                inner += child_size
            clips[clip] = tracks
        position += size
    return bones, parents, clips


# Follow the client creation of the apparatus objects from the room to the renderer.
def client_creation():
    room = read("source/rooms/RoomGhostRoom.cpp")
    create = body(room, "void RoomGhostRoom::createApparatusObjects(")
    # Every apparatus of the room gets its own building object with its own mesh on its floor stand tile
    for fragment in ("const std::string& mesh=getApparatusMesh(static_cast<GhostProduct>(index));",
            "new BuildingObject(getGameMap(),*this,mesh,tile,", "object->setFurnitureScale(Ogre::Vector2(1.0f,1.0f));",
            "apparatus.object=object;"):
        assert fragment in create, fragment
    assert re.search(r"static const std::string meshes\[APPARATUS_COUNT\]=\{\"ManaStill\",\"GhostPress\",\"SoulForge\"\};",
        body(room, "const std::string& RoomGhostRoom::getApparatusMesh(")), "the three apparatus meshes"
    # The positioned constructor only stores the position; it does not put the object into its tile
    constructor = body(read("source/entities/BuildingObject.cpp"), "BuildingObject::BuildingObject(GameMap* gameMap, Building& building, const std::string& meshName, Tile* targetTile,")
    assert "mPosition = Ogre::Vector3(x, y, z);" in constructor and "setPosition(" not in constructor, "constructor stores only"
    # addToGameMap registers the object in the lists of the map, not in a tile
    added = body(read("source/entities/RenderedMovableEntity.cpp"), "void RenderedMovableEntity::addToGameMap(")
    assert "addEntityToPositionTile" not in added and "setPosition(" not in added, "addToGameMap does not enter the tile"
    # setPosition enters the tile; the tile sends its entities to the seats that see it; they are created on the client
    moved = body(read("source/entities/MovableGameEntity.cpp"), "void MovableGameEntity::setPosition(")
    assert "addEntityToPositionTile(gameMap);" in moved, "setPosition enters the tile"
    tile = body(read("source/entities/Tile.cpp"), "void Tile::notifyEntitiesSeatsWithVision(")
    assert "for(GameEntity* entity : mEntitiesInTile)" in tile and "entity->notifySeatsWithVision(mSeatsWithVision , nt);" in tile
    notify = body(read("source/entities/GameEntity.cpp"), "void GameEntity::notifySeatsWithVision(")
    assert "fireAddEntity(seat, false ,nt);" in notify, "a seat that gains vision gets the entity"
    fire = body(read("source/entities/RenderedMovableEntity.cpp"), "void RenderedMovableEntity::fireAddEntity(")
    assert "ServerNotificationType::addEntity" in fire and "exportToPacket(serverNotification->mPacket, seat);" in fire
    # So every positioned object of the ghost room must be put into its tile, the apparatuses above all (the cause of build 36)
    for signature in re.findall(r"^\S[^\n;]*RoomGhostRoom::\w+\([^\n;]*$", room, re.M):
        function = body(room, signature)
        for variable in re.findall(r"BuildingObject\* (\w+)=(?:new BuildingObject|notifyActiveSpotCreated)\(", function):
            if variable + "->addToGameMap(" not in function:
                continue
            assert variable + "->setPosition(" in function, (signature.strip(), variable, "never enters its tile, so no client sees it")
    assert re.search(r"object->addToGameMap\(map\);object->setPosition\(object->getPosition\(\),map\);object->createMesh\(\);", create), \
        "the apparatus enters its floor stand tile"
    # The apparatus stands on its floor stand in the middle of its own tile (decision 793), not pushed to a wall
    assert "static_cast<float>(tile->getX()),static_cast<float>(tile->getY()),0.0f,static_cast<float>(rotation),false);" in create
    assert "forward=" not in create and "std::sin(angle)" not in create, "no offset towards a wall"
    # The client draws the packet: furniture scale and animation state travel with the object
    building = read("source/entities/BuildingObject.cpp")
    assert "os << mFurnitureScale.x << mFurnitureScale.y;" in body(building, "void BuildingObject::exportToPacket(")
    assert "os << mPrevAnimationState;" in body(read("source/entities/MovableGameEntity.cpp"), "void MovableGameEntity::exportToPacket(")
    render = body(read("source/render/RenderManager.cpp"), "void RenderManager::rrCreateRenderedMovableEntity(")
    assert "node->setPosition(renderedMovableEntity->getPosition());" in render
    assert "node->setScale(scale.x, scale.y, 1.0f);" in render, "renderer applies the placed furniture scale"
    # The room shows the state of G4 on each apparatus
    work = body(room, "void RoomGhostRoom::workApparatuses(")
    assert "const std::string state=!unlocked?\"Locked\":apparatus.working?\"Working\":\"Idle\";" in work
    assert "apparatus.object->setAnimationState(state,true);" in work
    print("client creation of the apparatuses: ok")


# Prove the visible size, height and look of the three meshes in each state.
def visible_size():
    bounds_source = read("source/gamemap/RoomObjectBounds.h")
    scale_rule = body(bounds_source, "inline FurnitureScale furnitureScale(")
    materials = "".join(path.read_text(encoding="utf-8") for path in (repo / "materials/scripts").glob("*.material"))
    for name in APPARATUS_MESHES:
        # Kept at their authored size by the renderer, as in mockup A
        assert re.search(r'name == "' + name + r'"', scale_rule), (name, "authored size")
        row = re.search(r'\{"' + name + r'",\s*([-.0-9]+)f,\s*([-.0-9]+)f,\s*([-.0-9]+)f,\s*([-.0-9]+)f,\s*([-.0-9]+)f\}', bounds_source)
        assert row, (name, "bounds row")
        min_x, min_y, max_x, max_y, max_z = (float(value) for value in row.groups())
        mesh = read_mesh(name)
        low_x, low_y, low_z, high_x, high_y, high_z, _ = mesh["bounds"]
        for listed, measured in ((min_x, low_x), (min_y, low_y), (max_x, high_x), (max_y, high_y), (max_z, high_z)):
            assert abs(listed - measured) < 1e-4, (name, "bounds row matches the mesh", listed, measured)
        # One tile wide, nearly a tile deep at most, standing on the floor and clearly taller than a worker
        width, depth, height = high_x - low_x, high_y - low_y, high_z - low_z
        assert 0.8 <= width <= 1.0, (name, "width", width)
        assert 0.4 <= depth < 1.0, (name, "depth", depth)
        assert abs(low_z) < 1e-6 and 1.0 <= height <= 1.7, (name, "height", low_z, height)
        positions = mesh["positions"]
        assert positions and len(positions) > 1000, (name, "vertices")
        for axis, low, high in ((0, low_x, high_x), (1, low_y, high_y), (2, low_z, high_z)):
            assert min(point[axis] for point in positions) >= low - 1e-4 and max(point[axis] for point in positions) <= high + 1e-4, (name, axis)
        # Every material exists
        for material, _ in mesh["submeshes"]:
            assert re.search(r"^\s*material\s+" + re.escape(material) + r"\s*$", materials, re.M), (name, material)
        # The skeleton: a root in bind pose carries the body; the clips only hide or show state parts
        assert mesh["skeleton"] == name + ".skeleton", (name, mesh["skeleton"])
        bones, parents, clips = read_skeleton(mesh["skeleton"])
        roots = [handle for handle in bones if handle not in parents]
        assert len(roots) == 1, (name, roots)
        root = roots[0]
        assert all(abs(value - 1.0) < 1e-6 for value in bones[root][1]), (name, "root bind scale")
        assigned = mesh["assignments"]
        assert len(assigned) == len(positions), (name, "every vertex follows a bone")
        dominant = {vertex: max(weights, key=lambda pair: pair[1])[0] for vertex, weights in assigned.items()}
        on_root = sum(1 for bone in dominant.values() if bone == root)
        assert on_root >= 0.3 * len(positions), (name, "the frame is on the root", on_root, len(positions))
        assert set(STATES) <= set(clips), (name, sorted(clips))
        # The frame shown in all three states spans the full footprint and height of the apparatus
        always = [vertex for vertex, bone in dominant.items() if all(shown_in(clips[state], bones, parents, bone) for state in STATES)]
        assert len(always) >= 0.4 * len(positions), (name, "frame shown in every state", len(always), len(positions))
        frame = [positions[vertex] for vertex in always]
        assert max(point[0] for point in frame) - min(point[0] for point in frame) >= 0.8 * width, (name, "frame width")
        # (the locked soul forge has no hammer above the anvil, as in mockup A, so the frame reaches the anvil top)
        assert max(point[2] for point in frame) >= 0.7 * height, (name, "frame height")
        for state in STATES:
            tracks = clips[state]
            # The root (the whole apparatus) is never scaled away
            assert all(all(abs(value - 1.0) < 1e-6 for value in scale) for scale in tracks.get(root, [])), (name, state, "root scaled")
            # Scale of a bone at the first key, multiplied up its parents
            def shown(bone):
                total = 1.0
                while bone is not None:
                    keys = tracks.get(bone)
                    total *= min(keys[0]) if keys else min(bones[bone][1])
                    bone = parents.get(bone)
                return total
            visible = sum(1 for bone in dominant.values() if shown(bone) >= 0.5)
            assert visible >= 0.6 * len(positions), (name, state, "visible share", visible, len(positions))
            # The visible part keeps the full height of the apparatus
            top = max(positions[vertex][2] for vertex, bone in dominant.items() if shown(bone) >= 0.5)
            assert top >= 0.7 * height, (name, state, "visible height", top, height)
        # Each state differs in look: something is shown or hidden between the clips
        looks = {state: tuple(sorted(bone for bone in bones if shown_in(clips[state], bones, parents, bone))) for state in STATES}
        assert len(set(looks.values())) == 3, (name, "three distinct state looks", looks)
    print("visible size, height and state looks of the apparatuses: ok")


# True when the bone is shown (scale at least one half, parents included) at the first key of the clip.
def shown_in(tracks, bones, parents, bone):
    total = 1.0
    while bone is not None:
        keys = tracks.get(bone)
        total *= min(keys[0]) if keys else min(bones[bone][1])
        bone = parents.get(bone)
    return total >= 0.5


# Each kind is shown by its own mesh, left to right as in mockup A.
def mesh_per_kind():
    enum = re.search(r"enum class GhostProduct : uint32_t \{([^}]*)\};", read("source/game/SeatData.h"))
    kinds = {name.strip(): int(value) for name, value in re.findall(r"(\w+)\s*=\s*(\d+)", enum.group(1))}
    room = read("source/rooms/RoomGhostRoom.cpp")
    lookup = body(room, "const std::string& RoomGhostRoom::getApparatusMesh(")
    meshes = re.search(r"meshes\[APPARATUS_COUNT\]=\{([^}]*)\};", lookup).group(1)
    meshes = [mesh.strip().strip('"') for mesh in meshes.split(",")]
    index = re.search(r"return meshes\[(.*)\];", lookup).group(1)
    # Evaluate the index expression of the source for every kind
    def evaluate(expression, kind):
        expression = expression.strip()
        if expression == "static_cast<uint32_t>(kind)":
            return kinds[kind]
        if re.fullmatch(r"\d+", expression):
            return int(expression)
        condition = re.match(r"kind==GhostProduct::(\w+)\?(\d+):(.*)$", expression)
        assert condition, expression
        return int(condition.group(2)) if condition.group(1) == kind else evaluate(condition.group(3), kind)
    expected = {"mana": "ManaStill", "research": "GhostPress", "crystal": "SoulForge"}
    for kind, mesh in expected.items():
        assert meshes[evaluate(index, kind)] == mesh, (kind, meshes[evaluate(index, kind)], mesh)
    layout = body(room, "void RoomGhostRoom::layoutApparatuses(")
    assert "const GhostProduct order[APPARATUS_COUNT]={GhostProduct::mana,GhostProduct::research,GhostProduct::crystal};" in layout
    print("one mesh per apparatus kind: ok")


def main():
    client_creation()
    visible_size()
    mesh_per_kind()
    print("ghost apparatus visible: ok")


if __name__ == "__main__":
    main()
