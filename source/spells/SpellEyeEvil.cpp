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

#include "spells/SpellEyeEvil.h"

#include "entities/Creature.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "modes/InputCommand.h"
#include "modes/InputManager.h"
#include "network/ODClient.h"
#include "network/ODPacket.h"
#include <istream>
#include <ostream>
#include "spells/SpellManager.h"
#include "utils/ConfigManager.h"
#include "game/SkillManager.h"
#include "game/SkillType.h"
#include "utils/Helper.h"
#include "utils/LogManager.h"

const std::string SpellEyeEvilName = "eyeEvil";
const std::string SpellEyeEvilNameDisplay = "Eye of Evil";
const std::string SpellEyeEvilCooldownKey = "EyeEvilCooldown";
const SpellType SpellEyeEvil::mSpellType = SpellType::eyeEvil;

namespace
{
class SpellEyeEvilFactory : public SpellFactory
{
    SpellType getSpellType() const override
    { return SpellEyeEvil::mSpellType; }

    const std::string& getName() const override
    { return SpellEyeEvilName; }

    const std::string& getCooldownKey() const override
    { return SpellEyeEvilCooldownKey; }

    const std::string& getNameReadable() const override
    { return SpellEyeEvilNameDisplay; }

    virtual void checkSpellCast(GameMap* gameMap, const InputManager& inputManager, InputCommand& inputCommand) const override
    { SpellEyeEvil::checkSpellCast(gameMap, inputManager, inputCommand); }

    virtual bool castSpell(GameMap* gameMap, Player* player, ODPacket& packet) const override
    { return SpellEyeEvil::castSpell(gameMap, player, packet); }

    Spell* getSpellFromStream(GameMap* gameMap, std::istream &is) const override
    { return SpellEyeEvil::getSpellFromStream(gameMap, is); }

    Spell* getSpellFromPacket(GameMap* gameMap, ODPacket &is) const override
    { return SpellEyeEvil::getSpellFromPacket(gameMap, is); }
};

// Register the factory
static SpellRegister reg(new SpellEyeEvilFactory);
}

SpellEyeEvil::SpellEyeEvil(GameMap* gameMap) :
    Spell(gameMap, SpellManager::getSpellNameFromSpellType(getSpellType()), "FlyingSkull", 0.0,
        ConfigManager::getSingleton().getSpellConfigInt32("EyeEvilNbTurns")),
    mFreeMode(false), mFreeRadius(0), mFreeTurns(0)
{
    mPrevAnimationState = "Triggered";
    mPrevAnimationStateLoop = true;
}

SpellEyeEvil::~SpellEyeEvil()
{
}

//! \brief Reveals the persisted base radius for a free eye, or the researched ordinary spell radius.
void SpellEyeEvil::computeVisibleTiles()
{
    uint32_t radius = mFreeMode ? mFreeRadius : static_cast<uint32_t>(std::round(SkillManager::getResearchValue(getSeat(), SkillType::spellEyeEvil,
        ConfigManager::getSingleton().getSpellConfigDouble("EyeEvilRadiusTiles"), ResearchEffect::Radius)));
    Tile* posTile = getPositionTile();
    if(posTile == nullptr)
    {
        OD_LOG_ERR("name=" + getName() + ", position=" + Helper::toString(getPosition()));
        return;
    }

    std::vector<Tile*> tiles = getGameMap()->circularRegion(posTile->getX(), posTile->getY(), radius);
    for(Tile* tile : tiles)
        tile->notifyVision(getSeat());
}

//! \brief Keeps the free-reveal save counter synchronized with the ordinary spell lifetime.
void SpellEyeEvil::doUpkeep()
{
    Spell::doUpkeep();
    if(mFreeMode && mFreeTurns > 0)
        --mFreeTurns;
}

//! \brief Spawns a free reveal with the base radius and no research or mana transaction.
SpellEyeEvil* SpellEyeEvil::spawnFree(GameMap* map, Seat* seat, Tile* tile, int32_t turns)
{
    if(map == nullptr || seat == nullptr || tile == nullptr)
        return nullptr;
    SpellEyeEvil* eye = new SpellEyeEvil(map);
    eye->mFreeMode = true;
    eye->mFreeRadius = ConfigManager::getSingleton().getSpellConfigUInt32("EyeEvilRadiusTiles");
    eye->mFreeTurns = turns;
    eye->setDuration(turns);
    eye->setSeat(seat);
    eye->addToGameMap();
    eye->createMesh();
    eye->setPosition(Ogre::Vector3(static_cast<Ogre::Real>(tile->getX()),
        static_cast<Ogre::Real>(tile->getY()), 3.0f));
    return eye;
}

//! \brief Saves the optional free mode and exact remaining lifetime.
void SpellEyeEvil::exportToStream(std::ostream& stream) const
{
    Spell::exportToStream(stream);
    if(mFreeMode)
        stream << " [FreeEye] " << mFreeRadius << ' ' << mFreeTurns << " [/FreeEye]";
}

//! \brief Restores free reveals while preserving legacy ordinary eye records.
bool SpellEyeEvil::importFromStream(std::istream& stream)
{
    if(!Spell::importFromStream(stream))
        return false;
    const std::streampos position = stream.tellg();
    std::string tag;
    if(stream >> tag)
    {
        if(tag == "[FreeEye]")
        {
            if(!(stream >> mFreeRadius >> mFreeTurns >> tag) || tag != "[/FreeEye]")
                return false;
            mFreeMode = true;
            setDuration(mFreeTurns);
        }
        else
            stream.seekg(position);
    }
    else
    {
        stream.clear();
        stream.seekg(position);
    }
    return true;
}

//! \brief Appends free-reveal presentation and lifetime to the common eye packet.
void SpellEyeEvil::exportToPacket(ODPacket& packet, const Seat* seat) const
{
    Spell::exportToPacket(packet, seat);
    packet << mFreeMode << mFreeRadius << mFreeTurns;
}

//! \brief Reads the symmetric free-reveal fields and restores its exact duration.
void SpellEyeEvil::importFromPacket(ODPacket& packet)
{
    Spell::importFromPacket(packet);
    OD_ASSERT_TRUE(packet >> mFreeMode >> mFreeRadius >> mFreeTurns);
    if(mFreeMode)
        setDuration(mFreeTurns);
}

void SpellEyeEvil::checkSpellCast(GameMap* gameMap, const InputManager& inputManager, InputCommand& inputCommand)
{
    Player* player = gameMap->getLocalPlayer();

    Tile* tile = gameMap->getTile(inputManager.mXPos, inputManager.mYPos);
    if(tile == nullptr)
    {
        inputCommand.displayText(Ogre::ColourValue::Red, "Point at a tile inside the map.");
        return;
    }

    int32_t playerMana = static_cast<int32_t>(player->getSeat()->getMana());
    int32_t price = ConfigManager::getSingleton().getSpellConfigInt32("EyeEvilPrice");
    if(playerMana < price)
    {
        inputCommand.displayText(Ogre::ColourValue::Red, "Not enough mana. " +
            formatCastSpell(SpellType::eyeEvil, price));
        return;
    }
    inputCommand.displayText(Ogre::ColourValue::White, formatCastSpell(SpellType::eyeEvil, price));

    if(inputManager.mCommandState != InputCommandState::validated)
    {
        std::vector<Tile*> tiles;
        tiles.push_back(tile);
        inputCommand.selectTiles(tiles);
        return;
    }

    inputCommand.unselectAllTiles();

    ClientNotification *clientNotification = SpellManager::createSpellClientNotification(SpellType::eyeEvil);
    gameMap->tileToPacket(clientNotification->mPacket, tile);

    ODClient::getSingleton().queueClientNotification(clientNotification);
}

//! \brief Casts the spell; the duration follows the eye of evil research.
bool SpellEyeEvil::castSpell(GameMap* gameMap, Player* player, ODPacket& packet)
{
    Tile* tile = gameMap->tileFromPacket(packet);
    if(tile == nullptr)
        return false;

    int32_t playerMana = static_cast<int32_t>(player->getSeat()->getMana());
    int32_t manaCost = ConfigManager::getSingleton().getSpellConfigInt32("EyeEvilPrice");
    if(playerMana < manaCost)
        return false;

    if(!player->getSeat()->takeMana(manaCost))
        return false;

    SpellEyeEvil* spell = new SpellEyeEvil(gameMap);
    spell->setSeat(player->getSeat());
    spell->setDuration(static_cast<int32_t>(std::round(SkillManager::getResearchValue(
        player->getSeat(), SkillType::spellEyeEvil,
        ConfigManager::getSingleton().getSpellConfigInt32("EyeEvilNbTurns"), ResearchEffect::Duration))));
    spell->addToGameMap();
    fireSpellEffect(*tile, "EyeEvil", "EyeEvilCast");
    Ogre::Vector3 spawnPosition(static_cast<Ogre::Real>(tile->getX()),
                                static_cast<Ogre::Real>(tile->getY()),
                                static_cast<Ogre::Real>(3.0));
    spell->createMesh();
    spell->setPosition(spawnPosition);

    return true;
}

//! \brief Loads only a valid ordinary or free eye record.
Spell* SpellEyeEvil::getSpellFromStream(GameMap* gameMap, std::istream &is)
{
    SpellEyeEvil* spell = new SpellEyeEvil(gameMap);
    if(!spell->importFromStream(is))
    {
        delete spell;
        return nullptr;
    }
    return spell;
}

Spell* SpellEyeEvil::getSpellFromPacket(GameMap* gameMap, ODPacket &is)
{
    SpellEyeEvil* spell = new SpellEyeEvil(gameMap);
    spell->importFromPacket(is);
    return spell;
}
