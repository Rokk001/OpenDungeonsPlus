"""Check type-neutral marking of unexplored tiles and the fog-surface mark. Text check, no game start."""
from pathlib import Path
import math

repo = Path(__file__).resolve().parents[2]


# Read a source contract without starting the game or a compiler.
def read(path):
    return (repo / path).read_text(encoding='utf-8')


game_mode = read('source/modes/GameMode.cpp')
assert 'Unexplored. Click or drag to mark for digging.' in game_mode
assert '!tile->getEverVisible() || tile->getHasFogOfWar() || tile->isDiggable' in game_mode

player = read('source/game/Player.cpp')
assert 'if(unexplored || getSeat()->isTileDiggableForClient(tile))' in player
assert 'if(!unexplored && !tile->isDiggable(getSeat()))' in player
seat = read('source/game/Seat.cpp')
assert 'mPlayer->markTilesForDigging(false, std::vector<Tile*>(1, tile), false)' in seat

render = read('source/render/RenderManager.cpp')
# Ordinary earth replaces the separate marked fog manager; require exact shared geometry and marks.
import runpy
earth_contract = runpy.run_path(str(repo / 'source/tests/check_fog_earth_geometry.py'), run_name='__fog_contract__')
assert 'mInstanceManagerMarkedFog' not in render and 'mInstanceManagerDirt' not in render
assert 'colourizeEntity(tileMeshEnt, seatColor, isMarked, vision)' in render
# The cloud above a marked unknown tile is hidden so it cannot cover the mark; unmarking shows it again.
fog_block = render[render.index('// Only previously discovered enemy territory'):]
fog_block = fog_block[:fog_block.index('// We rescale and set the orientation')]
# Set cloud visibility after creation as well, including marked discovered enemy tiles.
assert fog_block.index('createInstancedEntity("Fog")') < fog_block.index('tile.getFogOfWarCloud()->setVisible(!isMarked)')
assert 'if(tile.getFogOfWarCloud() != nullptr)' in fog_block
tile = read('source/entities/Tile.cpp')
assert 'DIG_MARK_COLOUR(0.65f, 0.45f, 1.0f, 0.5f)' in tile
# Blend the same opaque earth texture through the existing half-alpha overlay, on identical vertices.
assert '*markPass = *technique->getPass(0);' in render
assert 'markPass->setDepthWriteEnabled(false)' in render
preview = render[render.index('void RenderManager::rrDrawTilePreview('):render.index('bool RenderManager::getKeeperHandPosition')]
rectangle = preview[preview.index('if(singleRectangle)'):preview.index('    return;\n    }')]
assert 'if(construction || digging)' in rectangle and 'OT_TRIANGLE_LIST' in rectangle
assert 'minX - PREVIEW_BORDER_INNER_HALF' in rectangle and 'maxX + PREVIEW_BORDER_INNER_HALF' in rectangle
assert 'minX - PREVIEW_TILE_HALF' in rectangle and 'maxX + PREVIEW_TILE_HALF' in rectangle
# The named values keep the half tile width 0.5 and the inner frame edge 0.44.
assert 'static const float PREVIEW_TILE_HALF = 0.5f;' in render
assert 'static const float PREVIEW_BORDER_INNER_HALF = 0.44f;' in render

# Mario replaced the height-1.33211 flat cuboid with the exact ordinary earth surface.
# Read real mesh positions instead; retain every original translated-neighbour assertion below.
# The strict companion additionally checks all full-earth variants against each other.
assert 'createMarkedFogMesh' not in render
assert '"FogOfWarDirt.mesh"' not in render and '"FogOfWarMarked.mesh"' not in render
vertices = earth_contract['positions'](repo / 'models/Dirt_fl_1111.mesh')
height = max(p[2] for p in vertices)
corners = list({tuple(round(value, 4) for value in p) for p in vertices
                if abs(abs(p[0]) - 0.5) < 0.0001 and abs(abs(p[1]) - 0.5) < 0.0001
                and abs(p[2] - height) < 0.0001})
assert len(corners) == 4
assert {p[0] for p in corners} == {-0.5, 0.5}
assert {p[1] for p in corners} == {-0.5, 0.5}
assert {p[2] for p in corners} == {round(height, 4)}
for width, height in [(1, 1), (4, 1), (4, 4), (3, 7)]:
    # Every cell shares the same straight edge and top plane with its neighbours, without a gap/overlap.
    for x in range(width):
        for y in range(height):
            top = {(x + p[0], y + p[1], p[2]) for p in corners if p[2] > 0}
            if x + 1 < width:
                next_top = {(x + 1 + p[0], y + p[1], p[2]) for p in corners if p[2] > 0}
                assert len(top & next_top) == 2
            if y + 1 < height:
                next_top = {(x + p[0], y + 1 + p[1], p[2]) for p in corners if p[2] > 0}
                assert len(top & next_top) == 2
    thickness = 0.5 - 0.44
    assert math.isclose(thickness, 0.06)
    # One outer frame, with the same width as the existing single-tile frame, no internal tile lines.
    ring_area = width * height - (width - 2 * thickness) * (height - 2 * thickness)
    assert ring_area > 0
assert 'for(Tile* tile' not in rectangle[rectangle.index('if(construction || digging)'):]
# Relief now stays identical when marked; the overlay copies the same vertex pass instead of
# flattening a separate instanced surface. Shared world UVs continue across tile boundaries.
vertex = read('shaders/DirtTile.vert')
assert 'tileBorderFade(pos.xy)' in vertex and 'P = deform(P)' in vertex
assert 'worldTileUV(P)' in vertex and 'out_UV0 = mix(uv_0, worldUV, uvWeight)' in vertex
assert 'if(final_color.a > 0.0)' not in vertex
assert '*markPass = *technique->getPass(0);' in render
assert 'markPass->setVertexProgram' not in render
# No separate manager remains to create or leak an obsolete marked-fog mesh.
assert 'mInstanceManagerMarkedFog' not in render
# Releasing clears the temporary frame before the persistent marking is requested.
release = game_mode[game_mode.index('void GameMode::handlePlayerActionSelectTile()'):]
release = release[:release.index('void GameMode::resetSkillTree()')]
assert release.index('unselectAllTiles();') < release.index('ClientNotificationType::askMarkTiles')
assert 'markPass->setSceneBlending(Ogre::SBT_TRANSPARENT_ALPHA)' in render
assert 'Ogre::ColourValue markColor(Tile::DIG_MARK_COLOUR)' in render
# Every fog tile is markable everywhere, on the client as well as on the server, and the mark is shown.
set_mark = tile[tile.index('void Tile::setMarkedForDigging('):]
set_mark = set_mark[:set_mark.index('bool Tile::getMarkedForDigging')]
# The client never flags its players as human, so the client branch must not depend on getIsHuman().
assert 'setIsHuman' not in read('source/network/ODClient.cpp'), 'client sets human flags: re-check the client branch'
server_branch = set_mark[set_mark.index('if(getGameMap()->isServerGameMap())'):set_mark.index('else')]
client_branch = set_mark[set_mark.index('else'):set_mark.index('if (ss && !unexplored')]
assert 'unexplored = !getGameMap()->everVisitedFlagPool[getX()][getY()][pp->getSeat()->getId()];' in server_branch
assert 'getIsHuman' not in server_branch
assert 'getIsHuman' not in client_branch, 'client fog marks must not depend on the human flag the client never has'
assert '!getEverVisible() || getHasFogOfWar()' in client_branch
assert 'if (ss && !unexplored && !isDiggable(pp->getSeat()))' in set_mark
# No adjacency, distance or neighbour restriction in the client selection or the server acceptance.
for name, text in (('client selection', release[:release.index('unselectAllTiles();')]),
                   ('server mark', player[player.index('void Player::markTilesForDigging('):player.index('void Player::upkeepPlayer(')])):
    for forbidden in ('getNeighbor', 'isAdjacent', 'adjacent', 'Adjacent', 'getAllNeighbors'):
        assert forbidden not in text, name + ' restricts marking by ' + forbidden
# Every unknown mark uses the identical known-earth pass, independent of ever-visible or vision.
assert 'colourizeEntity(tileMeshEnt, seatColor, isMarked, vision)' in render
assert '*markPass = *technique->getPass(0);' in render
print('check_unexplored_marks ok: thick outer frame, shared earth marks, neutral tooltip and transparent marking')
