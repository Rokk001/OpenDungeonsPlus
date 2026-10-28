"""Strict source contracts for identical known/unknown earth geometry; no compilation or game start."""
from pathlib import Path
import re
import struct
import math

ROOT = Path(__file__).resolve().parents[2]


# Read actual OGRE position buffers without a converter, compiler or renderer.
def positions(path):
    data = path.read_bytes()
    result = []

    # Walk only documented mesh/geometry containers, never scan inside raw vertex buffers.
    def chunks(start, end):
        while start < end:
            kind, size = struct.unpack_from('<HI', data, start)
            # Legacy mesh serializers overstate container lengths; payloads remain bounded by the file.
            assert size >= 6
            yield kind, start + 6, min(start + size, end)
            start += size

    # Decode a declared float3 position stream from each shared or local geometry.
    def geometry(start, end):
        count, = struct.unpack_from('<I', data, start)
        position = None
        buffers = {}
        for kind, body, stop in chunks(start + 4, end):
            if kind == 0x5100:
                for entry, elem, _ in chunks(body, stop):
                    assert entry == 0x5110
                    source, value_type, semantic, offset, _ = struct.unpack_from('<5H', data, elem)
                    if semantic == 1:
                        assert value_type == 2
                        position = source, offset
            elif kind == 0x5200:
                binding, stride = struct.unpack_from('<HH', data, body)
                vertex_chunks = list(chunks(body + 4, stop))
                assert len(vertex_chunks) == 1 and vertex_chunks[0][0] == 0x5210
                raw = vertex_chunks[0][1]
                assert vertex_chunks[0][2] - raw == count * stride
                buffers[binding] = raw, stride
        assert position is not None
        raw, stride = buffers[position[0]]
        result.extend(struct.unpack_from('<3f', data, raw + index * stride + position[1])
                      for index in range(count))

    for kind, body, end in chunks(data.index(b'\n') + 1, len(data)):
        assert kind == 0x3000
        for child, start, stop in chunks(body + 1, end):
            if child == 0x5000:
                geometry(start, stop)
            elif child == 0x4000:
                cursor = data.index(b'\n', start) + 1
                shared, count, wide = struct.unpack_from('<?I?', data, cursor)
                cursor += 6 + count * (4 if wide else 2)
                for sub, local, limit in chunks(cursor, stop):
                    if sub == 0x5000:
                        assert not shared
                        geometry(local, limit)
    assert result
    return result


# Check the real authored earth top edges for every tileset mask and quarter-turn variant.
def earth_edges(tileset, offset=0.0):
    earth = tileset.split('[dirtFull]', 1)[1].split('[/dirtFull]', 1)[0]
    mask = None
    profiles = {}
    full_corners = []
    height = max(p[2] for p in positions(ROOT / 'models/Dirt_fl_0000.mesh'))
    for line in earth.splitlines():
        fields = line.split()
        if not fields:
            continue
        if re.fullmatch('[01]{4}', fields[0]):
            mask = int(fields.pop(0), 2)
        if not fields or not fields[0].endswith('.mesh'):
            continue
        name, material, rx, ry, rz = fields
        assert mask is not None and material == 'DirtWall' and float(rx) == float(ry) == 0
        angle = math.radians(float(rz))
        vertices = [(x * math.cos(angle) - y * math.sin(angle),
                     x * math.sin(angle) + y * math.cos(angle), z + offset)
                    for x, y, z in positions(ROOT / 'models' / name)]
        for bit, axis, side in [(0, 1, -0.5), (1, 0, 0.5), (2, 1, 0.5), (3, 0, -0.5)]:
            if not mask & (1 << bit):
                continue
            edge = [p for p in vertices if abs(p[axis] - side) < 0.0001 and p[2] > height - 0.001]
            assert len(edge) >= 2, (mask, name, bit, 'missing shared top edge')
            assert max(abs(p[2] - height) for p in edge) < 0.0001, (mask, name, bit, 'height mismatch')
            assert min(p[1-axis] for p in edge) >= -0.5001
            assert max(p[1-axis] for p in edge) <= 0.5001
            assert max(p[1-axis] for p in edge) > min(p[1-axis] for p in edge)
            profiles.setdefault(mask, []).append((axis, side, edge))
        if mask == 15:
            corners = {tuple(round(value, 4) for value in p) for p in vertices
                       if abs(abs(p[0]) - 0.5) < 0.0001 and abs(abs(p[1]) - 0.5) < 0.0001
                       and abs(p[2] - height) < 0.0001}
            assert len(corners) == 4, (name, 'missing shared top corner')
            full_corners.append(corners)
    assert full_corners and set(profiles) == set(range(1, 16))
    # The same top supports meet at each translated tile boundary for all previous rectangle sizes.
    for width, depth in [(1, 1), (4, 1), (4, 4), (3, 7)]:
        for x in range(width):
            for y in range(depth):
                for corners in full_corners:
                    top = {(x + p[0], y + p[1], p[2]) for p in corners}
                    for neighbour in full_corners:
                        if x + 1 < width:
                            next_top = {(x + 1 + p[0], y + p[1], p[2]) for p in neighbour}
                            assert len(top & next_top) == 2
                        if y + 1 < depth:
                            next_top = {(x + p[0], y + 1 + p[1], p[2]) for p in neighbour}
                            assert len(top & next_top) == 2
    return sum(len(edges) for edges in profiles.values())


# Remove comments and insignificant whitespace before comparing complete selection expressions.
def compact(source):
    return re.sub(r"\s+", "", re.sub(r"//[^\n]*|/\*.*?\*/", "", source, flags=re.S))


# Extract a complete C++ function body, respecting nested braces.
def function(source, signature):
    start = source.index(signature)
    first = source.index("{", start)
    depth = 1
    end = first + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[first + 1:end - 1]


# Require every client tile and one shared, type-neutral mesh/material/height/marking pipeline.
def verify(sources):
    create_all = function(sources["map"], "void GameMap::createAllEntities(")
    assert compact("""for (int jj = 0; jj < getMapSizeY(); ++jj) {
        for (int ii = 0; ii < getMapSizeX(); ++ii) {
            getTile(ii,jj)->createMesh(mNodeType);
        }
    }""") in compact(create_all)
    create_tile = function(sources["tile"], "void Tile::createMeshLocal(")
    assert 'rrCreateTile(*this, *getGameMap(), *getGameMap()->getLocalPlayer(),nt)' in create_tile
    create_render = function(sources["render"], "void RenderManager::rrCreateTile(")
    assert 'rrRefreshTile(tile, dtc, localPlayer,nt);' in create_render
    mesh = function(sources["map"], "const TileSetValue& GameMap::getMeshForTile(")
    assert compact(mesh) == compact("""
        const TileVisual visual = !isServerGameMap() && !tile->getEverVisible() ?
            TileVisual::dirtFull : tile->getTileVisual();
        int index = computeTileSetIndex(tile);
        int upper_bound = mTileSet->getTileValues(visual).at(index).size() - 1;
        std::uniform_int_distribution<int> distribution(0 , upper_bound);
        int random_number = distribution(generator);
        return mTileSet->getTileValues(visual).at(index).at(random_number);
    """), "unknown geometry, rotation and material must come from precisely the ordinary earth tileset"
    links = function(sources["links"], "bool TileSet::areLinked(")
    assert compact(links) == compact("""
        uint32_t intTile1Visual = static_cast<uint32_t>(!tile1->getIsOnServerMap() && !tile1->getEverVisible() ? TileVisual::dirtFull : tile1->getTileVisual());
        uint32_t intTile2Visual = static_cast<uint32_t>(!tile2->getIsOnServerMap() && !tile2->getEverVisible() ? TileVisual::dirtFull : tile2->getTileVisual());
        uint32_t linkValue = 1 << intTile2Visual;
        linkValue &= mTileLinks[intTile1Visual];
        if(linkValue == 0) return false;
        return true;
    """), "both neighbours must join as ordinary earth without changing server geometry"
    render = sources["render"]
    refresh = function(render, "void RenderManager::rrRefreshTile(")
    assert '"DirtInstanced"' not in render
    assert '"FogOfWarDirt.mesh"' not in render and '"FogOfWarMarked.mesh"' not in render
    assert 'createMarkedFogMesh' not in render
    assert refresh.count('createEntity(tileMeshName, meshPtr)') == 1
    assert 'const TileSetValue& tileSetValue = draggableTileContainer.getMeshForTile(&tile);' in refresh
    assert 'meshName = tileSetValue.getMeshName();' in refresh
    creation = refresh[refresh.index('if((tileMeshEnt == nullptr) && !meshName.empty() )'):refresh.index('// Only previously discovered')]
    assert compact(creation) == compact("""
        if((tileMeshEnt == nullptr) && !meshName.empty() ) {
            if(tileMeshNode == nullptr)
                tileMeshNode = tile.getEntityNode()->createChildSceneNode(tileMeshNodeName);
            tileMeshEnt = mSceneManager->createEntity(tileMeshName, meshPtr);
            tileMeshNode->attachObject(tileMeshEnt);
            tile.setHasFogOfWar(false);
        }
    """), "known and unknown terrain must instantiate exactly the same mesh at exactly the same transform"
    assert 'setScale(' not in refresh and 'tileMeshNode->setPosition(' not in refresh
    assert 'tileMeshNode->resetOrientation();' in refresh
    for axis in 'XYZ':
        assert f'tileSetValue.getRotation{axis}()' in refresh
    appearance = refresh[refresh.index('if(tileMeshEnt != nullptr)'):refresh.index('if (tile.getTileVisual() == TileVisual::waterGround')]
    assert compact(appearance) == compact("""
        if(tileMeshEnt != nullptr) {
            tileMeshEnt->setCastShadows(false);
            if(tile.getTileVisual() == TileVisual::claimedGround)
                tileMeshEnt->setLightMask(~ROOM_LIGHT_MASK);
            else tileMeshEnt->setLightMask(ALL_LIGHTS_MASK);
            if(!tileSetValue.getMaterialName().empty())
                tileMeshEnt->setMaterialName(tileSetValue.getMaterialName());
            if(tileSetValue.getMaterialName() == GOLD_WALL_MATERIAL)
                tileMeshEnt->setMaterialName(goldWallMaterialName(tile.getGoldDensity(), nt == NodeType::MDTC_NODE));
            Seat* seatColor = nullptr;
            if(tile.getEverVisible() && tile.shouldColorTileMesh()) seatColor = tile.getSeat();
            colourizeEntity(tileMeshEnt, seatColor, isMarked, vision);
        }
    """), "unknown earth must have precisely the ordinary earth material, lighting and mark pass"
    overlay = function(render, 'std::string RenderManager::colourizeMaterial(')
    mark = overlay[overlay.index('if(markedForDigging)'):]
    assert '*markPass = *technique->getPass(0);' in mark
    assert 'markPass->setVertexProgram' not in mark
    assert 'Ogre::ColourValue markColor(Tile::DIG_MARK_COLOUR)' in mark
    assert 'markPass->setSceneBlending(Ogre::SBT_TRANSPARENT_ALPHA)' in mark
    assert 'markPass->setDepthWriteEnabled(false)' in mark
    preview = function(render, 'void RenderManager::rrDrawTilePreview(')
    assert 'if(tile->getEverVisible() && !tile->getHasFogOfWar())' not in preview
    assert 'if(!tile->getHasFogOfWar())' in preview
    assert preview.count('if((!tile->getEverVisible() || tile->isFullTile()) && !getWallPreviewHeight(') == 2
    assert preview.count('getWorldBoundingBox(true).getMaximum().z + WALL_BORDER_LIFT') == 1
    assert 'getWorldBoundingBox(true).getMaximum().z + WALL_BORDER_LIFT' in function(render, 'static bool getWallPreviewHeight(')
    picking = function(sources['picker'], 'bool ODFrameListener::findTilePositionFromMouse(')
    assert 'if(!tile->getEverVisible() || tile->isFullTile())' in picking
    assert 'wall->getWorldBoundingBox(true).getMaximum().z' in picking
    # All 16 adjacency masks use ordinary earth materials and meshes, hence identical vertex heights.
    earth = sources['tileset'].split('[dirtFull]', 1)[1].split('[/dirtFull]', 1)[0]
    assert all(mask in earth for mask in (f'{i:04b}' for i in range(16)))
    entries = re.findall(r'(Dirt_[^\s]+\.mesh)\s+(\w+)\s+([0-9.-]+)\s+([0-9.-]+)\s+([0-9.-]+)', earth)
    assert entries and all(material == 'DirtWall' and float(rx) == 0 and float(ry) == 0 for _, material, rx, ry, _ in entries)
    assert all((ROOT / 'models' / name).exists() for name, *_ in entries)


sources = {key: (ROOT / path).read_text(encoding='utf-8') for key, path in {
    'map': 'source/gamemap/GameMap.cpp', 'links': 'source/gamemap/TileSet.cpp',
    'render': 'source/render/RenderManager.cpp', 'tile': 'source/entities/Tile.cpp', 'picker': 'source/render/ODFrameListener.cpp',
    'tileset': 'config/tilesets.cfg'}.items()}
verify(sources)
edges = earth_edges(sources['tileset'])
try:
    earth_edges(sources['tileset'], offset=0.1)
except AssertionError:
    pass
else:
    raise AssertionError('raised marked-earth edge mutation accepted')
# Each former visual mismatch and each client/server secrecy regression must fail independently.
mutations = [
    ('map', 'getTile(ii,jj)->createMesh(mNodeType);', 'if(getTile(ii,jj)->getEverVisible()) getTile(ii,jj)->createMesh(mNodeType);'),
    ('map', 'TileVisual::dirtFull : tile->getTileVisual()', 'TileVisual::goldFull : tile->getTileVisual()'),
    ('map', '!isServerGameMap() && ', ''),
    ('links', '!tile1->getIsOnServerMap() && ', ''),
    ('links', '!tile2->getIsOnServerMap() && ', ''),
    ('render', 'meshName = tileSetValue.getMeshName();', 'meshName = "FogOfWarDirt.mesh";'),
    ('render', 'tileMeshEnt->setMaterialName(tileSetValue.getMaterialName());', 'tileMeshEnt->setMaterialName("DirtInstanced");'),
    ('render', 'tileMeshNode->attachObject(tileMeshEnt);', 'tileMeshNode->attachObject(tileMeshEnt); tileMeshNode->setPosition(0, 0, 0.5f);'),
    ('render', '*markPass = *technique->getPass(0);', '*markPass = *technique->getPass(0); markPass->setVertexProgram("other");'),
    ('render', 'if(!tile->getHasFogOfWar())', 'if(tile->getEverVisible() && !tile->getHasFogOfWar())'),
    ('picker', 'if(!tile->getEverVisible() || tile->isFullTile())', 'if(tile->isFullTile())'),
]
for key, old, new in mutations:
    assert old in sources[key], old
    candidate = dict(sources)
    candidate[key] = sources[key].replace(old, new)
    try:
        verify(candidate)
    except AssertionError:
        pass
    else:
        raise AssertionError('regression accepted: ' + old)
print(f'check_fog_earth_geometry ok: {edges} real earth edges, common mesh/material/height/overlay, {len(mutations)+1} rejected mutations')
