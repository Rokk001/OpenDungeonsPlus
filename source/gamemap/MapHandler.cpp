/*
 *  Copyright (C) 2011-2016  OpenDungeons Team
 *
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "gamemap/MapHandler.h"

#include "gamemap/LevelScript.h"

#include "creaturemood/CreatureMoodManager.h"
#include "eventsystem/CreatureMoved.h"
#include "game/CreatureRelationships.h"
#include "gamemap/GameMap.h"
#include "game/Seat.h"
#include "goals/Goal.h"
#include "goals/GoalLoading.h"
#include "entities/ChickenEntity.h"
#include "entities/GhostEntity.h"
#include "entities/GhostBoxEntity.h"
#include "entities/CraftedTrap.h"
#include "entities/DirtPileEntity.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/EntityLoading.h"
#include "entities/GameEntity.h"
#include "entities/GameEntityType.h"
#include "entities/GiftBoxEntity.h"
#include "entities/MapLight.h"
#include "entities/MissileObject.h"
#include "entities/SkillEntity.h"
#include "entities/Tile.h"
#include "entities/TileLava.h"
#include "entities/TreasuryObject.h"
#include "entities/Weapon.h"
#include "modes/GameEditorModeConsole.h"
#include "rooms/Room.h"
#include "rooms/RoomManager.h"
#include "spells/Spell.h"
#include "traps/Trap.h"
#include "traps/TrapManager.h"
#include "utils/ConfigManager.h"
#include "utils/Helper.h"
#include "utils/LogManager.h"
#include "utils/ResourceManager.h"

#include "ODApplication.h"

#include <algorithm>
#include <iostream>
#include <sstream>
#include <vector>
#include <fstream>
#include <string>

namespace MapHandler {

//! \brief Loads campaign progress for both save browsing and direct saved-game server starts.
bool loadCampaignProgress()
{
    ResourceManager& resources = ResourceManager::getSingleton();
    Campaign& campaign = Campaign::getSingleton();
    std::ifstream definition((resources.getGameDataPath() + "levels/campaign/Campaign.cfg").c_str());
    if(!definition.is_open() || !campaign.importDefinition(definition))
    {
        campaign.stopCampaign();
        return false;
    }
    const std::string progressPath = resources.getUserDataPath() + "campaign.progress";
    campaign.setProgressPath(progressPath);
    std::ifstream progress(progressPath.c_str());
    if(progress.is_open())
        campaign.importProgress(progress);
    else
    {
        std::istringstream empty;
        campaign.importProgress(empty);
    }
    return true;
}

namespace {
//! \brief The reason of the last failed level load, shown in the menu.
std::string lastLoadError;

//! \brief Remembers a load failure and writes its exact cause to the log.
void setLoadError(const std::string& message)
{
    lastLoadError = message;
    OD_LOG_ERR("Level load failed: " + message);
}

//! \brief Largest side of a map that a level or a saved game may declare.
const int MAX_MAP_SIDE = 4096;

//! \brief Reads a whole number out of a text; false if the text is empty or has anything else than the number.
bool parseWholeNumber(const std::string& text, int& value)
{
    std::istringstream stream(text);
    stream >> value;
    if(stream.fail())
        return false;

    stream >> std::ws;
    return stream.eof();
}

//! \brief Checks that a tile line has what Tile::loadFromLine reads: x and y inside of the map, a known type and,
//! except for water, lava and mana wells, the fullness. On failure the reason is returned in the text.
bool isValidTileLine(const std::string& line, int mapSizeX, int mapSizeY, std::string& reason)
{
    std::vector<std::string> elems = Helper::split(line, '\t');
    int x = 0;
    int y = 0;
    int type = 0;
    if(elems.size() < 3 || !parseWholeNumber(elems[0], x) || !parseWholeNumber(elems[1], y) ||
       !parseWholeNumber(elems[2], type))
    {
        reason = "a tile line needs x, y and the type separated by tabs";
        return false;
    }

    if(x < 0 || y < 0 || x >= mapSizeX || y >= mapSizeY)
    {
        reason = "the tile is outside of the map";
        return false;
    }

    if(type < 0 || type >= static_cast<int>(TileType::countTileType))
    {
        reason = "the tile type is unknown";
        return false;
    }

    const TileType tileType = static_cast<TileType>(type);
    const bool ignoresFullness = (tileType == TileType::water) || (tileType == TileType::lava) ||
        (tileType == TileType::manaWell);
    if(!ignoresFullness && elems.size() < 4)
    {
        reason = "the tile line has no fullness";
        return false;
    }

    return true;
}
} // namespace

//! \brief Tells whether a file version header can be loaded, ignoring the build number of the writing version.
bool isSupportedVersionHeader(const std::string& header)
{
    if(header == ODApplication::VERSIONSTRING)
        return true;
    const char* releases[] = {"OpenDungeons_Version:0.7.1", "OpenDungeons_Version:0.7.2", "OpenDungeons_Version:0.7.3",
                              "OpenDungeons_Version:0.7.4"};
    for(const char* release : releases)
    {
        const std::string base(release);
        if(header == base)
            return true;
        // A build number follows as ".<digits>"
        if(header.size() > base.size() + 1 && header.compare(0, base.size(), base) == 0 && header[base.size()] == '.'
           && header.find_first_not_of("0123456789", base.size() + 1) == std::string::npos)
            return true;
    }
    return false;
}

//! \brief Returns the exact reason why the last level load failed.
const std::string& getLastLoadError()
{
    return lastLoadError;
}

//! \brief Loads map state and reports the failing section, retaining optional legacy sections.
bool readGameMapFromFile(const std::string& fileName, GameMap& gameMap)
{
    lastLoadError.clear();
    std::stringstream levelFile;
    if(!Helper::readFile(fileName, levelFile,true))
    {
        setLoadError("Could not read the file " + fileName);
        return false;
    }
    
    std::string nextParam;
    int mapSizeX;
    int mapSizeY;
    int numberOfSeats;
    
    getXandYandSeatsNumber(levelFile,mapSizeX,mapSizeY,numberOfSeats);  
    // A missing, negative or absurd map size must end in a message, never in a huge or negative allocation
    if((mapSizeX <= 0) || (mapSizeY <= 0) || (mapSizeX > MAX_MAP_SIDE) || (mapSizeY > MAX_MAP_SIDE))
    {
        setLoadError("The map size after [Tiles] is missing or not between 1 and " + Helper::toString(MAX_MAP_SIDE)
            + " (x=" + Helper::toString(mapSizeX) + ", y=" + Helper::toString(mapSizeY) + "), file=" + fileName);
        return false;
    }
    const int scannedMapSizeX = mapSizeX;
    const int scannedMapSizeY = mapSizeY;
    levelFile.clear();               // Clear any eof or fail flags
    levelFile.seekg(0, std::ios::beg);  // Move read position to beginning
    gameMap.initializeEverVisitedFlagTilesPools(mapSizeX,mapSizeY,numberOfSeats + 1);  // mind that the mId = 0 is always reserved and is not a valid Seat number, instead mId = 0 is for rogue ( enemy to all ) creatures
    // Read in the version number from the level file

    // std::vector CreatureMoved::alreadyVisited also depends on map Size : 
    CreatureMoved::alreadyVisited.assign(mapSizeX*mapSizeY, false);
    GameEditorModeConsole::scriptRegister.clear();
    /// int CreatureMoved::GAME_MAP_WIDTH also depends on map Size:
    CreatureMoved::GAME_MAP_WIDTH = mapSizeX;
    
    levelFile >> nextParam;
    if (!isSupportedVersionHeader(nextParam))
    {
        setLoadError("Unsupported file version '" + nextParam + "' (this game is " + ODApplication::VERSION
            + "), file=" + fileName);
        return false;
    }

    levelFile >> nextParam;
    if (nextParam != "[Info]")
    {
        setLoadError("Expected [Info] after the version but found '" + nextParam + "', file=" + fileName);
        return false;
    }

    // By default, we use the default tileSet
    gameMap.setTileSetName("");

    // Files without a Relationships line (levels, saves of older versions) get the relationships
    // option switched on with an empty table. The server overrides this for levels and the editor.
    gameMap.setRelationshipsEnabled(true);

    // Read in the seats from the level file
    while (true)
    {
        if(!levelFile.good())
        {
            setLoadError("Unexpected end or invalid stream in [Info], file=" + fileName);
            return false;
        }
        // Information can contain spaces. We need to use std::getline to get content
        std::getline(levelFile, nextParam);
        std::string param;
        if (nextParam == "[/Info]")
        {
            break;
        }

        param = "Name\t";
        if (nextParam.compare(0, param.size(), param) == 0)
        {
            gameMap.setLevelName(nextParam.substr(param.size()));
            continue;
        }

        param = "Description\t";
        if (nextParam.compare(0, param.size(), param) == 0)
        {
            gameMap.setLevelDescription(nextParam.substr(param.size()));
            continue;
        }

        param = "Music\t";
        if (nextParam.compare(0, param.size(), param) == 0)
        {
            std::string musicFile = nextParam.substr(param.size());
            gameMap.setLevelMusicFile(musicFile);
            OD_LOG_INF("Level Music: " + musicFile);
            continue;
        }

        param = "FightMusic\t";
        if (nextParam.compare(0, param.size(), param) == 0)
        {
            std::string musicFile = nextParam.substr(param.size());
            gameMap.setLevelFightMusicFile(nextParam.substr(param.size()));
            OD_LOG_INF("Level Fight Music: " + musicFile);
            continue;
        }

        param = "TileSet\t";
        if (nextParam.compare(0, param.size(), param) == 0)
        {
            std::string tileSet = nextParam.substr(param.size());
            gameMap.setTileSetName(tileSet);
            OD_LOG_INF("TileSet: " + tileSet);
            continue;
        }

        param = "TurnNumber\t";
        if (nextParam.compare(0, param.size(), param) == 0)
        {
            int64_t turnNumber = Helper::toInt(nextParam.substr(param.size()));
            gameMap.setSavedTurnNumber(turnNumber);
            OD_LOG_INF("Saved at turn: " + Helper::toString(turnNumber));
            continue;
        }

        param = "Sandbox\t";
        if (nextParam.compare(0, param.size(), param) == 0)
        {
            gameMap.setSandbox(nextParam.substr(param.size()) == "1");
            continue;
        }

        param = "Relationships\t";
        if (nextParam.compare(0, param.size(), param) == 0)
        {
            gameMap.setRelationshipsEnabled(nextParam.substr(param.size()) != "Off");
            continue;
        }
        if(gameMap.getSandboxMode().importInfoLine(nextParam))
            continue;
    }

    levelFile >> nextParam;
    
    if (nextParam != "[Seats]")
    {
        setLoadError("Expected [Seats] but found '" + nextParam + "', file=" + fileName);
        return false;
    }

    // Read in the seats from the level file
    while (true)
    {
        if(!levelFile.good())
        {
            setLoadError("Unexpected end or invalid stream in [Seats], file=" + fileName);
            return false;
        }

        levelFile >> nextParam;
        if (nextParam == "[/Seats]")
            break;

        if (nextParam != "[Seat]")
        {
            setLoadError(std::string("Expected a Seat tag but got " + nextParam) + ", file=" + fileName);
            return false;
        }

        Seat* tempSeat = new Seat(&gameMap);
        if(!tempSeat->importSeatFromStream(levelFile))
        {
            setLoadError("Invalid Seat data for seat id=" + Helper::toString(tempSeat->getId()) + ", file=" + fileName);
            delete tempSeat;
            return false;
        }

        if(!gameMap.addSeat(tempSeat))
        {
            OD_LOG_WRN("Couldn't add seat id="
                + Helper::toString(tempSeat->getId()));
            delete tempSeat;
        }
    }

    // Read in the goals that are shared by all players, the first player to complete all these goals is the winner.
    levelFile >> nextParam;
    if (nextParam != "[Goals]")
    {
        setLoadError("Expected [Goals] but found '" + nextParam + "', file=" + fileName);
        return false;
    }

    while(true)
    {
        if(!levelFile.good())
        {
            setLoadError("Unexpected end or invalid stream in [Goals], file=" + fileName);
            return false;
        }

        levelFile >> nextParam;
        if (nextParam == "[/Goals]")
            break;

        std::unique_ptr<Goal> tempGoal = Goals::loadGoalFromStream(nextParam, levelFile);

        if (tempGoal.get() != nullptr)
            gameMap.addGoalForAllSeats(std::move(tempGoal));
    }

    levelFile >> nextParam;
    if (nextParam != "[Tiles]")
    {
        setLoadError("Expected [Tiles] but found '" + nextParam + "', file=" + fileName);
        return false;
    }

    // Load the map size on next two lines

    if(!(levelFile >> mapSizeX >> mapSizeY) || (mapSizeX != scannedMapSizeX) || (mapSizeY != scannedMapSizeY))
    {
        setLoadError("The map size after [Tiles] could not be read, file=" + fileName);
        return false;
    }

    if (!gameMap.createNewMap(mapSizeX, mapSizeY))
    {
        setLoadError("Could not create map " + Helper::toString(mapSizeX) + "x" + Helper::toString(mapSizeY) + ", file=" + fileName);
        return false;
    }




    
    // Read in the map tiles from disk
    gameMap.disableFloodFill();
    gameMap.setProperPositions();
    while (true)
    {
        if(!levelFile.good())
        {
            setLoadError(std::string("unexpected EOF reached") + ", file=" + fileName);
            return false;
        }

        levelFile >> nextParam;
        if (nextParam == "[/Tiles]")
            break;

        // Get all the params together in order to prepare for the new parsing function
        std::string entire_line = nextParam;
        std::getline(levelFile, nextParam);
        entire_line += nextParam;

        std::string tileProblem;
        if(!isValidTileLine(entire_line, mapSizeX, mapSizeY, tileProblem))
        {
            setLoadError("Invalid tile line '" + entire_line.substr(0, 60) + "': " + tileProblem + ", file=" + fileName);
            return false;
        }

        TileType tt = Tile::getTileTypeFromLine(entire_line);

        Tile* tile;
        if(tt == TileType::lava)
            tile = new TileLava(&gameMap);

        else
            tile =  new Tile(&gameMap, true);

 
        
 
        Tile::loadFromLine(entire_line, tile);

        gameMap.addTile(tile);
    }

    gameMap.setAllFullnessAndNeighbors();

    // Read in the rooms
    levelFile >> nextParam;
    if (nextParam != "[Rooms]")
    {
        setLoadError(std::string("Invalid Rooms start format:" + nextParam) + ", file=" + fileName);
        return false;
    }

    while(true)
    {
        if(!levelFile.good())
        {
            setLoadError(std::string("unexpected EOF reached") + ", file=" + fileName);
            return false;
        }

        levelFile >> nextParam;
        if (nextParam == "[/Rooms]")
            break;

        if (gameMap.isServerGameMap() && (nextParam != "[Room]"))
        {
            setLoadError(std::string("Expected [Room] but got:" + nextParam) + ", file=" + fileName);
            return false;
        }

        if(!gameMap.isServerGameMap())
            continue;

        Room* tempRoom = RoomManager::getRoomFromStream(&gameMap, levelFile);
        if(tempRoom == nullptr)
        {
            setLoadError(std::string("unexpected null room") + ", file=" + fileName);
            return false;
        }

        tempRoom->addToGameMap();

        levelFile >> nextParam;
        if (nextParam != "[/Room]")
        {
            setLoadError(std::string("Expected [/Room] but got:" + nextParam) + ", file=" + fileName);
            return false;
        }
    }

    // Read in the traps
    levelFile >> nextParam;
    if (nextParam != "[Traps]")
    {
        setLoadError(std::string("Invalid Traps start format:" + nextParam) + ", file=" + fileName);
        return false;
    }

    while(true)
    {
        if(!levelFile.good())
        {
            setLoadError(std::string("unexpected EOF reached") + ", file=" + fileName);
            return false;
        }

        levelFile >> nextParam;
        if (nextParam == "[/Traps]")
            break;

        if (nextParam != "[Trap]")
        {
            setLoadError(std::string("Expected [Trap] but got:" + nextParam) + ", file=" + fileName);
            return false;
        }

        Trap* tempTrap = TrapManager::getTrapFromStream(&gameMap, levelFile);
        if(tempTrap == nullptr)
        {
            setLoadError(std::string("unexpected null trap") + ", file=" + fileName);
            return false;
        }

        tempTrap->addToGameMap();

        levelFile >> nextParam;
        if (nextParam != "[/Trap]")
        {
            setLoadError(std::string("Expected [/Trap] but got:" + nextParam) + ", file=" + fileName);
            return false;
        }
    }
    
    // Computer the tiles visuals
    for(int ii = 0; ii < mapSizeX; ++ii)
        for(int jj = 0; jj < mapSizeY; ++jj)
        {
            Tile* visualTile = gameMap.getTile(ii,jj);
            if(visualTile != nullptr)
                visualTile->computeTileVisual();
        }

    
    // Read in the lights
    levelFile >> nextParam;
    if (nextParam != "[Lights]")
    {
        setLoadError(std::string("Invalid Lights start format:" + nextParam) + ", file=" + fileName);
        return false;
    }

    while(true)
    {
        if(!levelFile.good())
        {
            setLoadError("Unexpected end or invalid stream in [Lights], file=" + fileName);
            return false;
        }

        levelFile >> nextParam;
        if (nextParam == "[/Lights]")
            break;

        std::string entire_line = nextParam;
        std::getline(levelFile, nextParam);
        entire_line += nextParam;

        std::stringstream ss(entire_line);
        MapLight* tempLight = MapLight::getMapLightFromStream(&gameMap, ss);
        if(tempLight == nullptr)
        {
            setLoadError(std::string("unexpected null map light") + ", file=" + fileName);
            return false;
        }
        tempLight->setName(gameMap.nextUniqueNameMapLight());
        tempLight->addToGameMap();
    }

    levelFile >> nextParam;
    if (nextParam == "[CreatureDefinitions]")
    {
        while(levelFile.good())
        {
            levelFile >> nextParam;
            if (nextParam == "[/CreatureDefinitions]")
                break;

            if (nextParam == "[/Creature]")
                continue;

            // Seek the [Creature] tag
            if (nextParam != "[Creature]")
            {
                setLoadError(std::string("Invalid Creature start format:" + nextParam) + ", file=" + fileName);
                return false;
            }

            levelFile >> nextParam;
            if (nextParam == "Name")
            {
                levelFile >> nextParam;
                CreatureDefinition* def = gameMap.getClassDescriptionForTuning(nextParam);
                if (def == nullptr)
                {
                    setLoadError(std::string("Invalid Creature definition format for " + nextParam) + ", file=" + fileName);
                    return false;
                }
                if(!CreatureDefinition::update(def, levelFile, ConfigManager::getSingleton().getCreatureDefinitions()))
                {
                    setLoadError("Invalid CreatureDefinitions data for " + nextParam + ", file=" + fileName);
                    return false;
                }
            }
        }

        levelFile >> nextParam;
    }

    if (nextParam == "[EquipmentDefinitions]")
    {
        while(levelFile.good())
        {
            levelFile >> nextParam;
            if (nextParam == "[/EquipmentDefinitions]")
                break;

            if (nextParam == "[/Equipment]")
                continue;

            if (nextParam != "[Equipment]")
            {
                setLoadError(std::string("Invalid Weapon start format:" + nextParam) + ", file=" + fileName);
                return false;
            }

            levelFile >> nextParam;
            if (nextParam == "Name")
            {
                levelFile >> nextParam;
                Weapon* def = gameMap.getWeaponForTuning(nextParam);
                if (def == nullptr)
                {
                    setLoadError(std::string("Invalid Weapon definition format for " + nextParam) + ", file=" + fileName);
                    return false;
                }
                if(!Weapon::update(def, levelFile))
                {
                    setLoadError("Invalid EquipmentDefinitions data for " + nextParam + ", file=" + fileName);
                    return false;
                }
            }
        }

        levelFile >> nextParam;
    }

    // Read in the actual creatures themselves
    if (nextParam != "[Creatures]")
    {
        setLoadError(std::string("Invalid Creatures start format:" + nextParam) + ", file=" + fileName);
        return false;
    }

    uint32_t nbCreatures = 0;
    while(true)
    {
        if(!levelFile.good())
        {
            setLoadError("Unexpected end or invalid stream in [Creatures], file=" + fileName);
            return false;
        }

        levelFile >> nextParam;
        if (nextParam == "[/Creatures]")
            break;

        std::string entire_line = nextParam;
        std::getline(levelFile, nextParam);
        entire_line += nextParam;

        std::stringstream ss(entire_line);
        Creature* tempCreature = Creature::getCreatureFromStream(&gameMap, ss);
        if(tempCreature == nullptr)
        {
            setLoadError("Creature number " + Helper::toString(nbCreatures + 1)
                + " of the level could not be read (see the warning above for the reason), line=" + entire_line.substr(0, 120)
                + ", file=" + fileName);
            return false;
        }

        tempCreature->addToGameMap();
        ++nbCreatures;
    }
    OD_LOG_INF("Loaded " + Helper::toString(nbCreatures) + " creatures in level");

    if(!readGameEntity(gameMap, "Spells", GameEntityType::spell, levelFile))
    {
        setLoadError(std::string("Invalid Spells section") + ", file=" + fileName);
        return false;
    }

    if(!readGameEntity(gameMap, "CraftedTraps", GameEntityType::craftedTrap, levelFile))
    {
        setLoadError(std::string("Invalid CraftedTraps section") + ", file=" + fileName);
        return false;
    }

    if(!readGameEntity(gameMap, "SkillEntity", GameEntityType::skillEntity, levelFile))
    {
        setLoadError(std::string("Invalid SkillEntity section") + ", file=" + fileName);
        return false;
    }

    if(!readGameEntity(gameMap, "GiftBoxEntity", GameEntityType::giftBoxEntity, levelFile))
    {
        setLoadError(std::string("Invalid GiftBoxEntity section") + ", file=" + fileName);
        return false;
    }

    // Item bags are optional in older maps and saves.
    const std::streampos itemBagPosition = levelFile.tellg();
    levelFile >> nextParam;
    levelFile.seekg(itemBagPosition);
    if(nextParam == "[ItemBags]" && !readGameEntity(gameMap, "ItemBags", GameEntityType::itemBagEntity, levelFile))
    {
        setLoadError("Invalid ItemBags section, file=" + fileName);
        return false;
    }
    // Ghosts are absent from legacy maps; leave the next section untouched.
    const std::streampos ghostPosition = levelFile.tellg();
    if(levelFile >> nextParam)
    {
        levelFile.seekg(ghostPosition);
        if(nextParam == "[Ghosts]" && !readGameEntity(gameMap, "Ghosts", GameEntityType::ghostEntity, levelFile))
        {
            setLoadError("Invalid Ghosts section, file=" + fileName);
            return false;
        }
    }
    else
    {
        levelFile.clear();
        levelFile.seekg(ghostPosition);
    }
    // Closed capture boxes follow ghosts; legacy maps have neither section.
    const std::streampos boxPosition = levelFile.tellg();
    if(levelFile >> nextParam)
    {
        levelFile.seekg(boxPosition);
        if(nextParam == "[GhostBoxes]" && !readGameEntity(gameMap, "GhostBoxes", GameEntityType::ghostBoxEntity, levelFile))
        {
            setLoadError("Invalid GhostBoxes section, file=" + fileName);
            return false;
        }
    }
    else
    {
        levelFile.clear();
        levelFile.seekg(boxPosition);
    }
    if(!readDirtSections(gameMap, levelFile))
    {
        setLoadError(std::string("Invalid Dirt or DirtPiles section") + ", file=" + fileName);
        return false;
    }

    if(!readGameEntity(gameMap, "Missiles", GameEntityType::missileObject, levelFile))
    {
        setLoadError(std::string("Invalid Missiles section") + ", file=" + fileName);
        return false;
    }

    if(!readGameEntity(gameMap, "TreasuryObject", GameEntityType::treasuryObject, levelFile))
    {
        setLoadError(std::string("Invalid TreasuryObject section") + ", file=" + fileName);
        return false;
    }

    if(!readGameEntity(gameMap, "Chickens", GameEntityType::chickenEntity, levelFile))
    {
        setLoadError(std::string("Invalid Chickens section") + ", file=" + fileName);
        return false;
    }
    
    levelFile >> nextParam;

    if(nextParam == "[HerbBundles]")
    {
        while(true)
        {
            levelFile >> nextParam;
            if(!levelFile.good())
            {
                setLoadError("Unexpected end or invalid stream in [HerbBundles], file=" + fileName);
                return false;
            }
            if(nextParam == "[/HerbBundles]")
                break;
            std::string remainder;
            std::getline(levelFile, remainder);
            std::stringstream bundleLine(nextParam + remainder);
            GameEntity* bundle = Entities::getGameEntityFromStream(&gameMap, GameEntityType::herbBundleEntity, bundleLine);
            if(bundle == nullptr)
            {
                setLoadError("Invalid HerbBundles entry=" + nextParam + remainder + ", file=" + fileName);
                return false;
            }
            bundle->addToGameMap();
        }
        levelFile >> nextParam;
    }
    if(nextParam == "[Scripts]")
    {
        while(true)
        {
            if(!levelFile.good())
            {
                setLoadError("Unexpected end or invalid stream in [Scripts], file=" + fileName);
                return false;
            }

            levelFile >> nextParam;
            if (nextParam == "[/Scripts]")
                break;

            std::string entire_line = nextParam;
            std::getline(levelFile, nextParam);
            entire_line += nextParam;

            std::stringstream ss(entire_line);
            std::stringstream script_body;
            std::string actionName;
            std::string scriptName;
            std::vector<int> auxVector;
            int auxI;
            ss >> actionName;
            ss >> scriptName;
            if(!Helper::readFile( ResourceManager::getSingleton().getGameScriptsPath() +  scriptName,script_body,false))            
                OD_LOG_ERR("COULD NOT READ THE FILE " + scriptName);
            while(ss>>auxI)
            {
                auxVector.push_back(auxI);
            }
           
            GameEditorModeConsole::scriptRegister[actionName].insert(make_pair(auxVector, script_body.str())); // std::make_pair(auxF,  script_body.str()));

        }

        levelFile >> nextParam;
    }

    // Optional level triggers and their state. Older levels do not have this section.
    if(nextParam == "[Triggers]")
    {
        if(!gameMap.getLevelScript().importFromStream(levelFile))
        {
            setLoadError(std::string("Invalid Triggers section") + ", file=" + fileName);
            return false;
        }

        if(!(levelFile >> nextParam))
            nextParam.clear();
    }

    // Optional creature relationships of a saved game. Only written when the option is on.
    if(nextParam == "[Relationships]")
    {
        // When the option is off the section is read and dropped
        CreatureRelationships dropped;
        CreatureRelationships* relationships = gameMap.getCreatureRelationships();
        if(relationships == nullptr)
            relationships = &dropped;

        // A resumed saved game continues at its saved turn; the map itself is still at turn -1 while loading
        int64_t relationshipTurn = (gameMap.getSavedTurnNumber() > 0) ? gameMap.getSavedTurnNumber() : gameMap.getTurnNumber();
        if(!relationships->readFromStream(levelFile, relationshipTurn))
        {
            setLoadError(std::string("Invalid Relationships section") + ", file=" + fileName);
            return false;
        }

        if(!(levelFile >> nextParam))
            nextParam.clear();
    }

    // Optional relationship state of the creatures (grief, rage, brawl). Only written when the option is on
    // and there is something to save; read and dropped when the option is off.
    if(nextParam == "[RelationshipState]")
    {
        std::vector<RelationshipCreatureState> states;
        if(!readRelationshipCreatureStates(levelFile, states))
        {
            setLoadError(std::string("Invalid RelationshipState section") + ", file=" + fileName);
            return false;
        }

        // The creature definitions are not set up yet while the level is read: the states are applied by
        // GameMap::createAllEntities, so that every saved relationship of an existing creature is kept.
        gameMap.setPendingRelationshipStates(states);
    }


        
    return true;
}

//! \brief Section tag that opens the dirt of the tiles in a level or saved game.
static const std::string DIRT_SECTION_OPEN = "[Dirt]";
//! \brief Section tag that closes the dirt of the tiles.
static const std::string DIRT_SECTION_CLOSE = "[/Dirt]";
//! \brief Section tag that opens the piles and blood stains.
static const std::string DIRT_PILES_SECTION_OPEN = "[DirtPiles]";
//! \brief Section tag that closes the piles and blood stains.
static const std::string DIRT_PILES_SECTION_CLOSE = "[/DirtPiles]";

//! \brief Reads the lines "x y dirt" of an opened [Dirt] section up to its end tag.
static bool readDirtTileLines(GameMap& gameMap, std::stringstream& levelFile)
{
    std::string token;
    while(levelFile >> token)
    {
        if(token == DIRT_SECTION_CLOSE)
            return true;

        int x = Helper::toInt(token);
        int y = 0;
        double dirt = 0.0;
        if(!(levelFile >> y >> dirt))
            return false;

        Tile* tile = gameMap.getTile(x, y);
        if(tile == nullptr)
        {
            OD_LOG_WRN("Dirt for an unknown tile x=" + Helper::toString(x) + ", y=" + Helper::toString(y));
            continue;
        }

        tile->setDirt(dirt);
    }

    return false;
}

//! \brief Reads the lines of an opened [DirtPiles] section up to its end tag.
static bool readDirtPileLines(GameMap& gameMap, std::stringstream& levelFile)
{
    std::string token;
    while(levelFile >> token)
    {
        if(token == DIRT_PILES_SECTION_CLOSE)
            return true;

        std::string line = token;
        std::string rest;
        std::getline(levelFile, rest);
        line += rest;

        std::stringstream lineStream(line);
        if(!DirtPileEntity::importFromSaveStream(&gameMap, lineStream))
        {
            OD_LOG_WRN("Invalid dirt pile line=" + line);
            return false;
        }
    }

    return false;
}

bool readDirtSections(GameMap& gameMap, std::stringstream& levelFile)
{
    // Both sections are optional and come in this order. A tag that is not ours is put back for the next reader.
    std::string tag;
    std::streampos before = levelFile.tellg();
    if(levelFile >> tag)
    {
        if(tag == DIRT_SECTION_OPEN)
        {
            if(!readDirtTileLines(gameMap, levelFile))
                return false;

            before = levelFile.tellg();
            if(!(levelFile >> tag))
                tag.clear();
        }

        if(tag == DIRT_PILES_SECTION_OPEN)
        {
            if(!readDirtPileLines(gameMap, levelFile))
                return false;

            return true;
        }
    }

    // Not a dirt section: go back to the start of the tag that was read
    levelFile.clear();
    levelFile.seekg(before);
    return true;
}

//! \brief Loads an entity section and converts legacy research books into their owner's points.
bool readGameEntity(GameMap& gameMap, const std::string& item, GameEntityType type, std::stringstream& levelFile)
{
    std::string nextParam;
    levelFile >> nextParam;
    if (nextParam != "[" + item + "]")
        return false;

    uint32_t nbEntity = 0;
    while(true)
    {
        if(!levelFile.good())
            return false;

        levelFile >> nextParam;
        if (nextParam == "[/" + item + "]")
            break;

        std::string entire_line = nextParam;
        std::getline(levelFile, nextParam);
        entire_line += nextParam;

        std::stringstream ss(entire_line);
        GameEntity* entity = Entities::getGameEntityFromStream(&gameMap, type, ss);
        if(entity == nullptr)
        {
            OD_LOG_ERR("unexpected null entity type=" + Helper::toString(static_cast<uint32_t>(type)) + " in " + item
                + ", line=" + entire_line.substr(0, 120));
            return false;
        }

        if(type == GameEntityType::skillEntity)
        {
            SkillEntity* legacyBook = static_cast<SkillEntity*>(entity);
            if(legacyBook->getSeat() == nullptr)
            {
                OD_LOG_ERR("Legacy research book has no valid owner");
                delete legacyBook;
                return false;
            }
            legacyBook->getSeat()->addSkillPoints(legacyBook->getSkillPoints());
            delete legacyBook;
        }
        else
            entity->addToGameMap();
        ++nbEntity;
    }
    OD_LOG_INF("Loaded " + Helper::toString(nbEntity) + " " + item + " in level");

    return true;
}

//! \brief Writes the [Dirt] section (one line x y dirt for every tile with dirt) and the [DirtPiles] section (one line
//! for every pile or blood stain). A section without entries is left out.
static void writeDirtSections(std::ostream& levelFile, GameMap& gameMap)
{
    std::stringstream dirtLines;
    for(int xx = 0; xx < gameMap.getMapSizeX(); ++xx)
    {
        for(int yy = 0; yy < gameMap.getMapSizeY(); ++yy)
        {
            Tile* tile = gameMap.getTile(xx, yy);
            if((tile != nullptr) && (tile->getDirt() > 0.0))
                dirtLines << xx << "\t" << yy << "\t" << tile->getDirt() << "\n";
        }
    }
    if(dirtLines.tellp() > 0)
    {
        levelFile << "\n" << DIRT_SECTION_OPEN << "\n";
        levelFile << "# x y dirt" << "\n";
        levelFile << dirtLines.str();
        levelFile << DIRT_SECTION_CLOSE << std::endl;
    }

    std::stringstream pileLines;
    const std::vector<RenderedMovableEntity*>& rendereds = gameMap.getRenderedMovableEntities();
    for(RenderedMovableEntity* rendered : rendereds)
    {
        if(rendered->getObjectType() != GameEntityType::dirtPileEntity)
            continue;

        static_cast<DirtPileEntity*>(rendered)->exportToSaveStream(pileLines);
        pileLines << "\n";
    }
    if(pileLines.tellp() > 0)
    {
        levelFile << "\n" << DIRT_PILES_SECTION_OPEN << "\n";
        levelFile << "# kind creatureClass x y dirtLeft ageTurns" << "\n";
        levelFile << pileLines.str();
        levelFile << DIRT_PILES_SECTION_CLOSE << std::endl;
    }
}

//! \brief Saves the map with item bags after gift boxes and the existing remaining sections.
//! \brief Campaign games also record their running context, separately from user progress.
bool writeGameMapToFile(const std::string& fileName, GameMap& gameMap)
{
    std::ofstream levelFile(fileName.c_str(), std::ifstream::out);

    // This is better than checking for .bad(), as it checks every error flags.
    if (!levelFile.good()) {
        OD_LOG_WRN("Couldn't open file for writing: " + fileName);
        return false;
    }

    // Write the identifier string and the version number
    levelFile << ODApplication::VERSIONSTRING
            << "  # The version of OpenDungeons which created this file (for compatibility reasons).\n";

    // Write map info
    levelFile << "\n[Info]\n";
    levelFile << "Name\t" << (gameMap.getLevelName().empty() ? "No name" : gameMap.getLevelName()) << std::endl;
    if (!gameMap.getLevelDescription().empty())
        levelFile << "Description\t" << gameMap.getLevelDescription() << std::endl;
    if (!gameMap.getLevelMusicFile().empty())
        levelFile << "Music\t" << gameMap.getLevelMusicFile() << std::endl;
    if (!gameMap.getLevelFightMusicFile().empty())
        levelFile << "FightMusic\t" << gameMap.getLevelFightMusicFile() << std::endl;
    if(!gameMap.getTileSetName().empty())
        levelFile << "TileSet\t" << gameMap.getTileSetName() << std::endl;
    if(gameMap.isSandbox())
    {
        levelFile << "Sandbox\t1" << std::endl;
        gameMap.getSandboxMode().exportInfo(levelFile);
    }

    // Only saved games record the option, levels written by the editor do not
    bool isGameSave = gameMap.isServerGameMap() && !gameMap.isInEditorMode();
    if(isGameSave)
    {
        Campaign::getSingleton().getSaveState().exportInfo(levelFile);
        levelFile << "Relationships\t" << (gameMap.isRelationshipsEnabled() ? "On" : "Off") << std::endl;
        // A saved game goes on from its current turn when it is loaded again. Levels written
        // by the editor have to start from the beginning, so they carry no turn.
        levelFile << "TurnNumber\t" << gameMap.getTurnNumber() << std::endl;
    }

    levelFile << "[/Info]" << std::endl;

    // Write out the seats to the file
    levelFile << "\n[Seats]\n";
    const std::vector<Seat*> seats = gameMap.getSeats();
    for (Seat* seat : seats)
    {
        // We don't save rogue seat
        if(seat->isRogueSeat())
            continue;

        levelFile << "[Seat]" << std::endl;
        seat->exportSeatToStream(levelFile);
        levelFile << "[/Seat]" << std::endl;
    }
    levelFile << "[/Seats]" << std::endl;

    // Write out the goals shared by all players to the file.
    levelFile << "\n[Goals]\n";
    levelFile << "# " << Goal::getFormat() << "\n";
    for (const std::unique_ptr<Goal>& goal : gameMap.getGoalsForAllSeats())
    {
        levelFile << *goal.get();
    }
    levelFile << "[/Goals]" << std::endl;

    levelFile << "\n[Tiles]\n";
    int mapSizeX = gameMap.getMapSizeX();
    int mapSizeY = gameMap.getMapSizeY();
    levelFile << "# Map Size" << std::endl;
    levelFile << mapSizeX << " # MapSizeX" << std::endl;
    levelFile << mapSizeY << " # MapSizeY" << std::endl;

    // Write out the tiles to the file
    levelFile << "# " << Tile::getFormat() << "\n";

    for(int ii = 0; ii < mapSizeX; ++ii)
    {
        for(int jj = 0; jj < mapSizeY; ++jj)
        {
            Tile* tile = gameMap.getTile(ii, jj);
            if (tile == nullptr)
                continue;

            // Don't save standard tiles as they're auto filled in at load time.
            if (!tile->isClaimed() && tile->getType() == TileType::dirt && tile->getFullness() >= 100.0)
                continue;

            Tile::exportToStream(tile, levelFile);
            levelFile << std::endl;
        }
    }
    levelFile << "[/Tiles]" << std::endl;

    std::vector<Room*> rooms = gameMap.getRooms();
    std::sort(rooms.begin(), rooms.end(), Room::sortForMapSave);

    // Write out the rooms to the file
    levelFile << "\n[Rooms]\n";
    levelFile << "# " << Room::getRoomStreamFormat() << "\n";
    for (Room* room : rooms)
    {
        // Rooms with 0 tiles are removed during upkeep. In editor mode, we don't use upkeep so there might be some rooms with
        // 0 tiles (if a room has been erased for example). For this reason, we don't save rooms with 0 tiles
        if((gameMap.isInEditorMode()) && (room->numCoveredTiles() <= 0))
            continue;

        levelFile << "[Room]" << std::endl;
        GameEntity::exportToStream(room, levelFile);
        levelFile << "[/Room]" << std::endl;
    }
    levelFile << "[/Rooms]" << std::endl;

    std::vector<Trap*> traps = gameMap.getTraps();
    // Gameplay saves retain the order used to schedule workshop production.
    if(gameMap.isInEditorMode())
        std::sort(traps.begin(), traps.end(), Trap::sortForMapSave);

    // Write out the traps to the file
    levelFile << "\n[Traps]\n";
    levelFile << "# " << Trap::getTrapStreamFormat() << "\n";
    for (Trap* trap : traps)
    {
        // In editor mode, we don't use upkeep so there might be some traps with
        // 0 tiles (if a trap has been erased for example). For this reason, we don't save traps with 0 tiles
        if(gameMap.isInEditorMode() && trap->numCoveredTiles() <= 0)
            continue;

        levelFile << "[Trap]" << std::endl;
        GameEntity::exportToStream(trap, levelFile);
        levelFile << "[/Trap]" << std::endl;
    }
    levelFile << "[/Traps]" << std::endl;

    // Write out the lights to the file.
    levelFile << "\n[Lights]\n";
    levelFile << "# " << MapLight::getMapLightStreamFormat() << "\n";
    for (MapLight* mapLight : gameMap.getMapLights())
    {
        GameEntity::exportToStream(mapLight, levelFile);
        levelFile << std::endl;
    }
    levelFile << "[/Lights]" << std::endl;

    levelFile << std::endl << "[CreatureDefinitions]" << std::endl;
    gameMap.saveLevelClassDescriptions(levelFile);
    levelFile << "[/CreatureDefinitions]" << std::endl;

    levelFile << std::endl << "[EquipmentDefinitions]" << std::endl;
    gameMap.saveLevelEquipments(levelFile);
    levelFile << "[/EquipmentDefinitions]" << std::endl;

    // Write out the individual creatures to the file
    levelFile << "\n[Creatures]\n";
    levelFile << "# " << Creature::getCreatureStreamFormat() << "\n";
    for (Creature* creature : gameMap.getCreatures())
    {
        GameEntity::exportToStream(creature, levelFile);
        levelFile << std::endl;
    }
    levelFile << "[/Creatures]" << std::endl;

    // Write out the RenderedMovableEntities that need to
    const std::vector<RenderedMovableEntity*>& rendereds = gameMap.getRenderedMovableEntities();
    levelFile << "\n[Spells]\n";
    levelFile << "# " << Spell::getSpellStreamFormat() << "\n";
    for (Spell* spell : gameMap.getSpells())
    {
        GameEntity::exportToStream(spell, levelFile);
        levelFile << std::endl;
    }
    levelFile << "[/Spells]" << std::endl;

    levelFile << "\n[CraftedTraps]\n";
    levelFile << "# " << CraftedTrap::getCraftedTrapStreamFormat() << "\n";
    for (RenderedMovableEntity* rendered : rendereds)
    {
        if(rendered->getObjectType() != GameEntityType::craftedTrap)
            continue;

        GameEntity::exportToStream(rendered, levelFile);
        levelFile << std::endl;
    }
    levelFile << "[/CraftedTraps]" << std::endl;

    levelFile << "\n[SkillEntity]\n";
    levelFile << "# " << SkillEntity::getSkillEntityStreamFormat() << "\n";
    for (RenderedMovableEntity* rendered : rendereds)
    {
        if(rendered->getObjectType() != GameEntityType::skillEntity)
            continue;

        GameEntity::exportToStream(rendered, levelFile);
        levelFile << std::endl;
    }
    levelFile << "[/SkillEntity]" << std::endl;

    levelFile << "\n[GiftBoxEntity]\n";
    levelFile << "# " << GiftBoxEntity::getGiftBoxEntityStreamFormat() << "\n";
    for (RenderedMovableEntity* rendered : rendereds)
    {
        if(rendered->getObjectType() != GameEntityType::giftBoxEntity)
            continue;

        GameEntity::exportToStream(rendered, levelFile);
        levelFile << std::endl;
    }
    levelFile << "[/GiftBoxEntity]" << std::endl;

    levelFile << "\n[ItemBags]\n";
    levelFile << "# SeatId Name MeshName PosX PosY PosZ opacity rotationAngle ItemInstanceLine\n";
    for(RenderedMovableEntity* rendered : rendereds)
    {
        if(rendered->getObjectType() != GameEntityType::itemBagEntity)
            continue;
        GameEntity::exportToStream(rendered, levelFile);
        levelFile << '\n';
    }
    levelFile << "[/ItemBags]\n";
    levelFile << "\n[Ghosts]\n";
    levelFile << "# SeatId Name ClassName CreatureName PosX PosY Level LifeLeft State AssignedHunter\n";
    for(RenderedMovableEntity* rendered : rendereds)
    {
        if(rendered->getObjectType() != GameEntityType::ghostEntity)
            continue;
        GameEntity::exportToStream(rendered, levelFile);
        levelFile << '\n';
    }
    levelFile << "[/Ghosts]\n";
    levelFile << "\n[GhostBoxes]\n";
    levelFile << "# Name PosX PosY OpenTurns NbGhosts (GhostName)*\n";
    for(RenderedMovableEntity* rendered : rendereds)
    {
        if(rendered->getObjectType() != GameEntityType::ghostBoxEntity)
            continue;
        GameEntity::exportToStream(rendered, levelFile);
        levelFile << '\n';
    }
    levelFile << "[/GhostBoxes]\n";
    writeDirtSections(levelFile, gameMap);

    levelFile << "\n[Missiles]\n";
    levelFile << "# " << MissileObject::getMissileObjectStreamFormat() << "\n";
    for (RenderedMovableEntity* rendered : rendereds)
    {
        if(rendered->getObjectType() != GameEntityType::missileObject)
            continue;

        GameEntity::exportToStream(rendered, levelFile);
        levelFile << std::endl;
    }
    levelFile << "[/Missiles]" << std::endl;

    levelFile << "\n[TreasuryObject]\n";
    levelFile << "# " << TreasuryObject::getTreasuryObjectStreamFormat() << "\n";
    for (RenderedMovableEntity* rendered : rendereds)
    {
        if(rendered->getObjectType() != GameEntityType::treasuryObject)
            continue;

        GameEntity::exportToStream(rendered, levelFile);
        levelFile << std::endl;
    }
    levelFile << "[/TreasuryObject]" << std::endl;

    levelFile << "\n[Chickens]\n";
    levelFile << "# " << ChickenEntity::getChickenEntityStreamFormat() << "\n";
    for (RenderedMovableEntity* rendered : rendereds)
    {
        if(rendered->getObjectType() != GameEntityType::chickenEntity)
            continue;

        GameEntity::exportToStream(rendered, levelFile);
        levelFile << std::endl;
    }
    levelFile << "[/Chickens]" << std::endl;
    levelFile << "\n[HerbBundles]\n";
    for(RenderedMovableEntity* rendered : rendereds)
        if(rendered->getObjectType() == GameEntityType::herbBundleEntity)
        {
            GameEntity::exportToStream(rendered, levelFile);
            levelFile << "\n";
        }
    levelFile << "[/HerbBundles]\n";

    if(!gameMap.getLevelScript().isEmpty())
    {
        levelFile << "\n";
        // The turn counter starts at 0 again when the game is loaded, so a time limit is
        // written as the time that is left
        LevelScript script = gameMap.getLevelScript();
        int64_t elapsedSeconds = static_cast<int64_t>(static_cast<double>(std::max<int64_t>(0, gameMap.getTurnNumber()))
            / ODApplication::turnsPerSecond);
        script.rebaseTimeLimit(elapsedSeconds);
        script.exportToStream(levelFile);
    }

    if(isGameSave && gameMap.isRelationshipsEnabled())
    {
        levelFile << "\n[Relationships]\n";
        gameMap.getCreatureRelationships()->writeToStream(levelFile, gameMap.getTurnNumber());
        levelFile << "[/Relationships]" << std::endl;

        std::vector<RelationshipCreatureState> states;
        const std::vector<Creature*>& creatures = gameMap.getCreatures();
        for(size_t i = 0; i < creatures.size(); ++i)
        {
            RelationshipCreatureState state;
            if(creatures[i]->getRelationshipState(state))
                states.push_back(state);
        }

        if(!states.empty())
        {
            levelFile << "\n[RelationshipState]\n";
            writeRelationshipCreatureStates(levelFile, states);
            levelFile << "[/RelationshipState]" << std::endl;
        }
    }

    if (!levelFile.good()) {
        OD_LOG_WRN("Unexpected failure on file: " + fileName);
        return false;
    }

    levelFile.close();
    return true;
}

//! \brief Lists supported level formats independently of the executable build suffix.
//! \brief Exposes optional campaign save metadata without changing campaign activity.
bool getMapInfo(const std::string& fileName, LevelInfo& levelInfo)
{
    levelInfo = LevelInfo();
    // Prepare an invalid level reference
    std::stringstream levelFile;
    if(!Helper::readFile(fileName, levelFile,true))
        return false;

    std::string nextParam;
    // Read in the version number from the level file
    levelFile >> nextParam;
    if (!isSupportedVersionHeader(nextParam))
        return false;

    levelFile >> nextParam;
    if (nextParam != "[Info]")
        return false;

    std::stringstream mapInfo;

    // Read in the seats from the level file
    while (true)
    {
        if(!levelFile.good())
            return false;
        // Information can contain spaces. We need to use std::getline to get content
        std::getline(levelFile, nextParam);
        std::string param;
        if (nextParam == "[/Info]")
        {
            break;
        }

        if(levelInfo.mCampaignSave.importInfoLine(nextParam))
            continue;

        param = "Name\t";
        if (nextParam.compare(0, param.size(), param) == 0)
        {
            levelInfo.mLevelName = nextParam.substr(param.size());
            mapInfo << levelInfo.mLevelName << std::endl << std::endl;
            continue;
        }

        param = "Description\t";
        if (nextParam.compare(0, param.size(), param) == 0)
        {
            mapInfo << nextParam.substr(param.size()) << std::endl << std::endl;
            continue;
        }

        if (nextParam == "Sandbox\t1")
        {
            levelInfo.mIsSandbox = true;
            continue;
        }

        param = "SandboxRealm\t";
        if (nextParam.compare(0, param.size(), param) == 0)
        {
            levelInfo.mSandboxRealm = nextParam.substr(param.size());
            continue;
        }

        param = "SandboxNext\t";
        if (nextParam.compare(0, param.size(), param) == 0)
        {
            levelInfo.mSandboxNext = nextParam.substr(param.size());
            continue;
        }

    }

    levelFile >> nextParam;
    if (nextParam != "[Seats]")
    {
        levelInfo.mLevelDescription = mapInfo.str();
        return true;
    }

    // Read in the seats from the level file
    int playerSeatNumber = 0;
    int AISeatNumber = 0;
    int seatConfigurable = 0;
    while (true)
    {
        if(!levelFile.good())
            return false;

        levelFile >> nextParam;
        if (nextParam == "[/Seats]")
            break;

        if (nextParam != "[Seat]")
            return false;

        while(true)
        {
            std::string line;
            std::getline(levelFile, line);
            std::stringstream ss(line);
            ss >> nextParam;
            if(nextParam == "[/Seat]")
                break;

            if(nextParam != "player")
                continue;

            // We get the player type
            ss >> nextParam;
            if (nextParam == Seat::PLAYER_TYPE_HUMAN)
                ++playerSeatNumber;
            else if (nextParam == Seat::PLAYER_TYPE_CHOICE)
                ++seatConfigurable;
            else if (nextParam == Seat::PLAYER_TYPE_AI)
                ++AISeatNumber;
        }
    }

    if (playerSeatNumber > 0 || AISeatNumber > 0)
    {
        std::string str;

        if (playerSeatNumber > 0)
            str += "Player slot(s): " + Helper::toString(playerSeatNumber);
        if (AISeatNumber > 0)
        {
            if(!str.empty())
                str += " / ";

            str += "AI: " + Helper::toString(AISeatNumber);
        }
        if (seatConfigurable > 0)
        {
            if(!str.empty())
                str += " / ";

            str += "Configurable: " + Helper::toString(seatConfigurable);
        }

        mapInfo << str << std::endl << std::endl;
    }

    // Read in the goals that are shared by all players, the first player to complete all these goals is the winner.
    levelFile >> nextParam;
    if (nextParam != "[Goals]")
    {
        levelInfo.mLevelDescription = mapInfo.str();
        return true;
    }

    while(true)
    {
        if(!levelFile.good())
            return false;

        levelFile >> nextParam;
        if (nextParam == "[/Goals]")
            break;
    }

    levelFile >> nextParam;
    if (nextParam != "[Tiles]")
    {
        levelInfo.mLevelDescription = mapInfo.str();
        return true;
    }

    // Load the map size on next two lines
    int mapSizeX = 0;
    int mapSizeY = 0;
    levelFile >> mapSizeX;
    levelFile >> mapSizeY;

    mapInfo << "Size: " << mapSizeX << "x" << mapSizeY << std::endl << std::endl;

    levelInfo.mLevelDescription = mapInfo.str();
    return true;
}

//! \brief Finds the map size of the last [Tiles] section and counts the seats; a size that is no number stays -1.
void getXandYandSeatsNumber(std::stringstream& ss,int& xx, int& yy, int& numberOfSeats)
{
    numberOfSeats = 0;
    xx = -1;
    yy = -1;
    std::string nextParam;
    while(true)
    {
        if(!ss.good())
            break;
        ss >> nextParam;
        if (nextParam == "[Seat]")
            numberOfSeats++;    
        else if (nextParam == "[Tiles]")
        {
        
            // A size that is not a number must stay invalid, the caller refuses it
            if(!(ss >> xx))
                xx = -1;
            if(!(ss >> yy))
                yy = -1;
        
        }
    }
    OD_ASSERT_TRUE_MSG( xx > 0 && yy > 0 , "Couldn't find mapSizeX and mapSizeY" );
}

} // Namespace MapHandler
