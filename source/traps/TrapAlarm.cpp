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

#include "traps/TrapAlarm.h"

#include "entities/Tile.h"
#include "entities/TrapEntity.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "spells/Spell.h"
#include "spells/SpellCallToWar.h"
#include "spells/SpellType.h"
#include "traps/TrapManager.h"
#include "utils/ConfigManager.h"
#include "utils/LogManager.h"

const std::string TrapAlarmName = "Alarm";
const std::string TrapAlarmNameDisplay = "Alarm trap";
const TrapType TrapAlarm::mTrapType = TrapType::alarm;

namespace
{
class TrapAlarmFactory : public TrapFactory
{
    TrapType getTrapType() const override
    { return TrapAlarm::mTrapType; }

    const std::string& getName() const override
    { return TrapAlarmName; }

    const std::string& getNameReadable() const override
    { return TrapAlarmNameDisplay; }

    int getCostPerTile() const override
    { return ConfigManager::getSingleton().getTrapConfigInt32("AlarmCostPerTile"); }

    const std::string& getMeshName() const override
    {
        static const std::string meshName = "Spiketrap";
        return meshName;
    }

    void checkBuildTrap(GameMap* gameMap, const InputManager& inputManager, InputCommand& inputCommand) const override
    {
        checkBuildTrapDefault(gameMap, TrapType::alarm, inputManager, inputCommand);
    }

    bool buildTrap(GameMap* gameMap, Player* player, ODPacket& packet) const override
    {
        std::vector<Tile*> tiles;
        if(!getTrapTilesDefault(tiles, gameMap, player, packet))
            return false;

        int32_t pricePerTarget = TrapManager::costPerTile(TrapType::alarm);
        int32_t price = static_cast<int32_t>(tiles.size()) * pricePerTarget;
        if(!gameMap->withdrawFromTreasuries(price, player->getSeat()))
            return false;

        TrapAlarm* trap = new TrapAlarm(gameMap);
        return buildTrapDefault(gameMap, trap, player->getSeat(), tiles);
    }

    void checkBuildTrapEditor(GameMap* gameMap, const InputManager& inputManager, InputCommand& inputCommand) const override
    {
        checkBuildTrapDefaultEditor(gameMap, TrapType::alarm, inputManager, inputCommand);
    }

    bool buildTrapEditor(GameMap* gameMap, ODPacket& packet) const override
    {
        TrapAlarm* trap = new TrapAlarm(gameMap);
        return buildTrapDefaultEditor(gameMap, trap, packet);
    }

    Trap* getTrapFromStream(GameMap* gameMap, std::istream& is) const override
    {
        TrapAlarm* trap = new TrapAlarm(gameMap);
        if(!Trap::importTrapFromStream(*trap, is))
        {
            OD_LOG_ERR("Error while building a trap from the stream");
        }
        return trap;
    }

    bool buildTrapOnTiles(GameMap* gameMap, Player* player, const std::vector<Tile*>& tiles, bool noFee = false) const override
    {        
        return buildTrapOnTiles(gameMap, player->getSeat(), tiles, noFee);
    }
    
    bool buildTrapOnTiles(GameMap* gameMap, Seat* seatPtr, const std::vector<Tile*>& tiles, bool noFee=false) const 
    {
        int32_t pricePerTarget = TrapManager::costPerTile(TrapType::alarm);
        int32_t price = static_cast<int32_t>(tiles.size()) * pricePerTarget;
        if(!noFee)
            if(!gameMap->withdrawFromTreasuries(price, seatPtr))
                return false;

        TrapAlarm* trap = new TrapAlarm(gameMap);
        return buildTrapDefault(gameMap, trap, seatPtr, tiles);
    }
};

// Register the factory
static TrapRegister reg(new TrapAlarmFactory);
}

TrapAlarm::TrapAlarm(GameMap* gameMap) :
    Trap(gameMap)
{
    mReloadTime = ConfigManager::getSingleton().getTrapConfigUInt32("AlarmReloadTurns");
    mNbShootsBeforeDeactivation = ConfigManager::getSingleton().getTrapConfigUInt32("AlarmNbShootsBeforeDeactivation");
    setMeshName("");
}

bool TrapAlarm::shoot(Tile* tile)
{
    std::vector<Tile*> visibleTiles;
    visibleTiles.push_back(tile);
    std::vector<GameEntity*> enemyCreatures = getGameMap()->getVisibleCreatures(visibleTiles, getSeat(), true);
    if(enemyCreatures.empty() && !mForcedTrigger)
        return false;

    // The alarm calls the owner's fighters with a call to war banner on the trap tile.
    // If the owner already has a banner there, we do not add another one.
    std::vector<Spell*> callToWars = getGameMap()->getSpellsBySeatAndType(getSeat(), SpellType::callToWar);
    for(Spell* callToWar : callToWars)
    {
        if(callToWar->getPositionTile() == tile)
            return false;
    }

    SpellCallToWar* spell = new SpellCallToWar(getGameMap());
    spell->setSeat(getSeat());
    spell->addToGameMap();
    Ogre::Vector3 spawnPosition(static_cast<Ogre::Real>(tile->getX()),
                                static_cast<Ogre::Real>(tile->getY()),
                                static_cast<Ogre::Real>(0.0));
    spell->createMesh();
    spell->setPosition(spawnPosition);
    return true;
}

TrapEntity* TrapAlarm::getTrapEntity(Tile* tile)
{
    return new TrapEntity(getGameMap(), *this, reg.getTrapFactory()->getMeshName(), tile, 0.0, true, isActivated(tile) ? 1.0f : 0.7f);
}
