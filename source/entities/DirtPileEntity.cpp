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

#include "entities/DirtPileEntity.h"

#include "entities/GameEntityType.h"
#include "entities/Tile.h"
#include "gamemap/GameMap.h"
#include "network/ODPacket.h"
#include "utils/ConfigManager.h"
#include "utils/LogManager.h"

#include <istream>
#include <ostream>

const std::string DirtPileEntity::PILE_MESH_PREFIX = "Pile_";
const std::string DirtPileEntity::BLOOD_MESH_NAME = "BloodStain";
const double DirtPileEntity::DIRT_LEFT_START = 100.0;

//! \brief Text of the kind "pile" in the saved dirt piles.
static const std::string KIND_PILE_TEXT = "pile";
//! \brief Text of the kind "blood" in the saved dirt piles.
static const std::string KIND_BLOOD_TEXT = "blood";
//! \brief Written in the saved dirt piles instead of an empty creature class.
static const std::string NO_CLASS_TEXT = "none";
//! \brief Base name of the unique name of a pile.
static const std::string PILE_BASE_NAME = "DirtPile_";
//! \brief Base name of the unique name of a blood stain.
static const std::string BLOOD_BASE_NAME = "BloodStain_";

DirtPileEntity::DirtPileEntity(GameMap* gameMap, DirtPileKind kind, const std::string& creatureClass) :
    RenderedMovableEntity(gameMap, (kind == DirtPileKind::pile) ? PILE_BASE_NAME : BLOOD_BASE_NAME,
        getMeshNameFor(kind, creatureClass), 0.0f, false),
    mKind(kind),
    mCreatureClass(creatureClass),
    mDirtLeft(DIRT_LEFT_START),
    mAgeTurns(0.0)
{
}

DirtPileEntity::DirtPileEntity(GameMap* gameMap) :
    RenderedMovableEntity(gameMap),
    mKind(DirtPileKind::pile),
    mCreatureClass(""),
    mDirtLeft(DIRT_LEFT_START),
    mAgeTurns(0.0)
{
}

GameEntityType DirtPileEntity::getObjectType() const
{
    return GameEntityType::dirtPileEntity;
}

std::string DirtPileEntity::getMeshNameFor(DirtPileKind kind, const std::string& creatureClass)
{
    if(kind == DirtPileKind::blood)
        return BLOOD_MESH_NAME;

    return PILE_MESH_PREFIX + creatureClass;
}

void DirtPileEntity::doUpkeep()
{
    if(!getIsOnMap())
        return;

    if(mDirtLeft <= 0.0)
    {
        removeFromGameMap();
        deleteYourself();
        return;
    }

    if(mKind != DirtPileKind::blood)
        return;

    // Blood dries into normal tile dirt: the stain goes, the dirt of its tile stays
    mAgeTurns += 1.0;
    if(mAgeTurns >= ConfigManager::getSingleton().getDirtConfigDouble("BloodDryTurns"))
    {
        removeFromGameMap();
        deleteYourself();
    }
}

DirtPileEntity* DirtPileEntity::getEntityOnTile(const Tile* tile, DirtPileKind kind)
{
    if(tile == nullptr)
        return nullptr;

    const std::vector<GameEntity*>& entities = tile->getEntitiesInTile();
    for(std::vector<GameEntity*>::const_iterator it = entities.begin(); it != entities.end(); ++it)
    {
        GameEntity* entity = *it;
        if((entity == nullptr) || (entity->getObjectType() != GameEntityType::dirtPileEntity))
            continue;

        DirtPileEntity* dirtPile = static_cast<DirtPileEntity*>(entity);
        if(dirtPile->mKind == kind)
            return dirtPile;
    }

    return nullptr;
}

DirtPileEntity* DirtPileEntity::createOnTile(GameMap* gameMap, Tile* tile, DirtPileKind kind, const std::string& creatureClass)
{
    if((gameMap == nullptr) || (tile == nullptr))
        return nullptr;

    DirtPileEntity* dirtPile = getEntityOnTile(tile, kind);
    if(dirtPile == nullptr)
    {
        dirtPile = new DirtPileEntity(gameMap, kind, creatureClass);
        dirtPile->addToGameMap();
        Ogre::Vector3 spawnPosition(static_cast<Ogre::Real>(tile->getX()),
                                    static_cast<Ogre::Real>(tile->getY()), 0.0f);
        dirtPile->createMesh();
        dirtPile->setPosition(spawnPosition);
    }
    else
    {
        // The tile has one already: it is as dirty as a new one again
        dirtPile->mDirtLeft = DIRT_LEFT_START;
    }

    // A pile makes its tile as dirty as can be at once; blood only adds what the fight itself did
    if(kind == DirtPileKind::pile)
        tile->addDirt(Tile::MAX_DIRT);

    return dirtPile;
}

bool DirtPileEntity::cleanBy(double amount)
{
    if(amount > 0.0)
        mDirtLeft -= amount;

    if(mDirtLeft > 0.0)
        return false;

    removeFromGameMap();
    deleteYourself();
    return true;
}

void DirtPileEntity::restoreState(double dirtLeft, double ageTurns)
{
    mDirtLeft = dirtLeft;
    mAgeTurns = ageTurns;
}

std::string DirtPileEntity::kindToString(DirtPileKind kind)
{
    if(kind == DirtPileKind::blood)
        return KIND_BLOOD_TEXT;

    return KIND_PILE_TEXT;
}

bool DirtPileEntity::kindFromString(const std::string& text, DirtPileKind& kind)
{
    if(text == KIND_PILE_TEXT)
    {
        kind = DirtPileKind::pile;
        return true;
    }

    if(text == KIND_BLOOD_TEXT)
    {
        kind = DirtPileKind::blood;
        return true;
    }

    return false;
}

void DirtPileEntity::exportToSaveStream(std::ostream& os) const
{
    int32_t x = 0;
    int32_t y = 0;
    const Tile* tile = getPositionTile();
    if(tile != nullptr)
    {
        x = tile->getX();
        y = tile->getY();
    }

    os << kindToString(mKind) << "\t" << (mCreatureClass.empty() ? NO_CLASS_TEXT : mCreatureClass) << "\t"
       << x << "\t" << y << "\t" << mDirtLeft << "\t" << mAgeTurns;
}

bool DirtPileEntity::importFromSaveStream(GameMap* gameMap, std::istream& is)
{
    std::string kindText;
    std::string creatureClass;
    int32_t x = 0;
    int32_t y = 0;
    double dirtLeft = 0.0;
    double ageTurns = 0.0;
    if(!(is >> kindText >> creatureClass >> x >> y >> dirtLeft >> ageTurns))
        return false;

    DirtPileKind kind = DirtPileKind::pile;
    if(!kindFromString(kindText, kind))
        return false;

    if(creatureClass == NO_CLASS_TEXT)
        creatureClass.clear();

    if(gameMap->getTile(x, y) == nullptr)
        return false;

    DirtPileEntity* dirtPile = new DirtPileEntity(gameMap, kind, creatureClass);
    dirtPile->restoreState(dirtLeft, ageTurns);
    dirtPile->mPosition = Ogre::Vector3(static_cast<Ogre::Real>(x), static_cast<Ogre::Real>(y), 0.0f);
    dirtPile->addToGameMap();
    return true;
}

DirtPileEntity* DirtPileEntity::getDirtPileEntityFromPacket(GameMap* gameMap, ODPacket& is)
{
    DirtPileEntity* dirtPile = new DirtPileEntity(gameMap);
    dirtPile->importFromPacket(is);
    return dirtPile;
}

void DirtPileEntity::exportToPacket(ODPacket& os, const Seat* seat) const
{
    RenderedMovableEntity::exportToPacket(os, seat);
    os << static_cast<int32_t>(mKind);
    os << mCreatureClass;
    os << mDirtLeft;
    os << mAgeTurns;
}

void DirtPileEntity::importFromPacket(ODPacket& is)
{
    RenderedMovableEntity::importFromPacket(is);
    int32_t kind = 0;
    OD_ASSERT_TRUE(is >> kind);
    mKind = (kind == static_cast<int32_t>(DirtPileKind::blood)) ? DirtPileKind::blood : DirtPileKind::pile;
    OD_ASSERT_TRUE(is >> mCreatureClass);
    OD_ASSERT_TRUE(is >> mDirtLeft);
    OD_ASSERT_TRUE(is >> mAgeTurns);
}
