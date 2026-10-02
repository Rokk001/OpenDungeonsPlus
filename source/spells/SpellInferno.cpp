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

#include "spells/SpellInferno.h"

#include "creatureeffect/CreatureEffectBurn.h"
#include "entities/Creature.h"
#include "entities/GameEntityType.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "modes/InputCommand.h"
#include "modes/InputManager.h"
#include "network/ODClient.h"
#include "spells/SpellType.h"
#include "spells/SpellManager.h"
#include "utils/ConfigManager.h"
#include "utils/Helper.h"
#include "utils/LogManager.h"

const std::string SpellInfernoName = "inferno";
const std::string SpellInfernoNameDisplay = "Inferno";
const std::string SpellInfernoCooldownKey = "InfernoCooldown";
const SpellType SpellInferno::mSpellType = SpellType::inferno;

namespace
{
class SpellInfernoFactory : public SpellFactory
{
    SpellType getSpellType() const override
    { return SpellInferno::mSpellType; }

    const std::string& getName() const override
    { return SpellInfernoName; }

    const std::string& getCooldownKey() const override
    { return SpellInfernoCooldownKey; }

    const std::string& getNameReadable() const override
    { return SpellInfernoNameDisplay; }

    virtual void checkSpellCast(GameMap* gameMap, const InputManager& inputManager, InputCommand& inputCommand) const override
    { SpellInferno::checkSpellCast(gameMap, inputManager, inputCommand); }

    virtual bool castSpell(GameMap* gameMap, Player* player, ODPacket& packet) const override
    { return SpellInferno::castSpell(gameMap, player, packet); }

    Spell* getSpellFromStream(GameMap* gameMap, std::istream &is) const override
    { return SpellInferno::getSpellFromStream(gameMap, is); }

    Spell* getSpellFromPacket(GameMap* gameMap, ODPacket &is) const override
    { return SpellInferno::getSpellFromPacket(gameMap, is); }
};

// Register the factory
static SpellRegister reg(new SpellInfernoFactory);
}

namespace
{
//! \brief Tells whether the given tile is inside the circle of the given radius around (x, y)
bool isTileInRadius(const Tile* tile, int x, int y, int radius)
{
    int dx = tile->getX() - x;
    int dy = tile->getY() - y;
    return (dx * dx + dy * dy) <= (radius * radius);
}

std::vector<Tile*> getTilesInRadius(GameMap* gameMap, int x, int y, int radius)
{
    std::vector<Tile*> tiles;
    for(int xx = x - radius; xx <= x + radius; ++xx)
    {
        for(int yy = y - radius; yy <= y + radius; ++yy)
        {
            Tile* tile = gameMap->getTile(xx, yy);
            if(tile == nullptr)
                continue;

            if(!isTileInRadius(tile, x, y, radius))
                continue;

            tiles.push_back(tile);
        }
    }
    return tiles;
}
}

void SpellInferno::checkSpellCast(GameMap* gameMap, const InputManager& inputManager, InputCommand& inputCommand)
{
    Player* player = gameMap->getLocalPlayer();
    int32_t price = ConfigManager::getSingleton().getSpellConfigInt32("InfernoPrice");
    int radius = static_cast<int>(ConfigManager::getSingleton().getSpellConfigUInt32("InfernoRadiusTiles"));
    int32_t playerMana = static_cast<int32_t>(player->getSeat()->getMana());

    Tile* tileSelected = gameMap->getTile(inputManager.mXPos, inputManager.mYPos);
    if(tileSelected == nullptr)
        return;

    std::vector<Tile*> tiles = getTilesInRadius(gameMap, inputManager.mXPos, inputManager.mYPos, radius);
    inputCommand.selectTiles(tiles);

    std::string txt = formatCastSpell(SpellType::inferno, price);
    if(playerMana < price)
        inputCommand.displayText(Ogre::ColourValue::Red, txt);
    else
        inputCommand.displayText(Ogre::ColourValue::White, txt);

    if(inputManager.mCommandState != InputCommandState::validated)
        return;

    inputCommand.unselectAllTiles();

    ClientNotification *clientNotification = SpellManager::createSpellClientNotification(SpellType::inferno);
    clientNotification->mPacket << inputManager.mXPos << inputManager.mYPos;
    ODClient::getSingleton().queueClientNotification(clientNotification);
}

bool SpellInferno::castSpell(GameMap* gameMap, Player* player, ODPacket& packet)
{
    int x;
    int y;
    OD_ASSERT_TRUE(packet >> x >> y);

    Tile* tileTarget = gameMap->getTile(x, y);
    if(tileTarget == nullptr)
    {
        OD_LOG_ERR("x=" + Helper::toString(x) + ", y=" + Helper::toString(y));
        return false;
    }

    int32_t price = ConfigManager::getSingleton().getSpellConfigInt32("InfernoPrice");
    if(!player->getSeat()->takeMana(price))
        return false;

    int radius = static_cast<int>(ConfigManager::getSingleton().getSpellConfigUInt32("InfernoRadiusTiles"));
    double damagePerTurn = ConfigManager::getSingleton().getSpellConfigDouble("InfernoDamagePerTurn");
    int32_t nbTurns = static_cast<int32_t>(ConfigManager::getSingleton().getSpellConfigUInt32("InfernoNbTurns"));

    // Enemy creatures in the area catch fire. We copy the list to be safe if creatures are removed.
    std::vector<Creature*> creatures = gameMap->getCreatures();
    for(Creature* creature : creatures)
    {
        if(!creature->isAlive())
            continue;

        if(creature->getSeat()->isAlliedSeat(player->getSeat()))
            continue;

        Tile* pos = creature->getPositionTile();
        if((pos == nullptr) || !isTileInRadius(pos, x, y, radius))
            continue;

        // There is no dedicated fire particle effect yet, the explosion one is used as a placeholder
        creature->addCreatureEffect(new CreatureEffectBurn(nbTurns, damagePerTurn, "SpellCreatureExplosion"));
    }

    return true;
}

Spell* SpellInferno::getSpellFromStream(GameMap* gameMap, std::istream &is)
{
    OD_LOG_ERR("SpellInferno cannot be read from stream");
    return nullptr;
}

Spell* SpellInferno::getSpellFromPacket(GameMap* gameMap, ODPacket &is)
{
    OD_LOG_ERR("SpellInferno cannot be read from packet");
    return nullptr;
}
