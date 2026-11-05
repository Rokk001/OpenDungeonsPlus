"""Static check: loading a save with training hall weapon racks does not place the racks on their tiles too early.

A gameplay save keeps the weapon racks of a training hall ("TrainingRack WeaponShield2 x y z angle" on a room tile
line). RoomTrainingHall::importTileDataFromStream restored such a rack with Building::addBuildingObject, which calls
setPosition -> addEntityToPositionTile -> GameMap::getHeightFromTile. While the map loads, the tile set and its
height map (mTileSet, mHighMap) are not set yet: GameMap::createAllEntities sets them after the whole map is read and
then puts every loaded rendered entity on its tile. So loading the save 2026-11-05_073240-SK-Brackenford.level
crashed right after "Adding rendered object RenderedMovableEntity_TrainingHall_5_[7,30]_1,MeshName=WeaponShield2".
The rack must only be registered while loading. It does not start a game and compiles nothing."""
from pathlib import Path
import re
import sys

repo = Path(__file__).resolve().parents[2]


def function(text, start):
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def strip_comments(text):
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    return re.sub(r'//[^\n]*', '', text)


def source(path):
    return strip_comments((repo / path).read_text(encoding='utf-8'))


failures = []


def check(condition, message):
    if not condition:
        failures.append(message)


game_map = source('source/gamemap/GameMap.cpp')
building = source('source/entities/Building.cpp')
movable = source('source/entities/MovableGameEntity.cpp')
entity = source('source/entities/GameEntity.cpp')
hall = source('source/rooms/RoomTrainingHall.cpp')

# The premise: the height of a tile needs the tile set, which is known only once all entities are created
create = function(game_map, game_map.index('void GameMap::createAllEntities()'))
check(re.search(r'mHighMap\s*=', create) is not None and re.search(r'mTileSet\s*=', create) is not None,
      'GameMap::createAllEntities sets the tile set and its height map')
check(re.search(r'for\s*\(\s*RenderedMovableEntity\s*\*\s*\w+\s*:\s*mRenderedMovableEntities\s*\)\s*\{?\s*'
                r'\w+->setPosition\(', create) is not None,
      'GameMap::createAllEntities puts every loaded rendered entity on its tile')
height = function(game_map, game_map.index('float GameMap::getHeightFromTile('))
check('mHighMap->' in height, 'GameMap::getHeightFromTile reads the height map')
check('getHeightFromTile(' in function(entity, entity.index('void GameEntity::addEntityToPositionTile(')),
      'GameEntity::addEntityToPositionTile asks the height of the tile')
check('addEntityToPositionTile(' in function(movable, movable.index('void MovableGameEntity::setPosition(')),
      'MovableGameEntity::setPosition puts the entity on its tile')
check('setPosition(' in function(building, building.index('void Building::addBuildingObject(')),
      'Building::addBuildingObject places the object on its tile')

# The fix: the rack read from a save is registered only; createAllEntities places it
body = function(hall, hall.index('bool RoomTrainingHall::importTileDataFromStream('))
check('new BuildingObject(' in body, 'RoomTrainingHall::importTileDataFromStream restores the saved rack')
check('addBuildingObject(' not in body and 'replaceBuildingObject(' not in body,
      'RoomTrainingHall::importTileDataFromStream does not place the rack on its tile with addBuildingObject')
check(re.search(r'->\s*setPosition\(|\bsetPosition\(', body) is None,
      'RoomTrainingHall::importTileDataFromStream does not call setPosition while the map loads')
check(re.search(r'mBuildingObjects\s*\[\s*tile\s*\]\s*=\s*rack\s*;', body) is not None,
      'RoomTrainingHall::importTileDataFromStream keeps the rack as the building object of its tile')
check(re.search(r'rack\s*->\s*addToGameMap\(\s*\)', body) is not None,
      'RoomTrainingHall::importTileDataFromStream adds the rack to the game map')

if failures:
    for failure in failures:
        print('FAIL: ' + failure)
    sys.exit(1)
print('check_training_rack_load: OK')
