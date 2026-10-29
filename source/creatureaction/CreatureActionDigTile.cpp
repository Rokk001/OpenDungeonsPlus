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

#include "creatureaction/CreatureActionDigTile.h"

#include "creatureaction/CreatureActionGrabEntity.h"

#include "creatureeffect/CreatureEffectDigTile.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/Tile.h"
#include "entities/TreasuryObject.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "gamemap/LevelScript.h"
#include "gamemap/Pathfinding.h"
#include "network/CosmeticEvent.h"
#include "rooms/Room.h"
#include "utils/ConfigManager.h"
#include "utils/Helper.h"
#include "utils/MakeUnique.h"
#include "utils/LogManager.h"

CreatureActionDigTile::CreatureActionDigTile(Creature& creature, Tile& tileDig, Tile& tilePos) :
    CreatureAction(creature),
    mTileDig(tileDig),
    mTilePos(tilePos)
{
    mCreature.parkedBit = false;
    mTileDig.addWorkerDigging(mCreature, mTilePos);     
}

CreatureActionDigTile::~CreatureActionDigTile()
{
    mTileDig.removeWorkerDigging(mCreature, mTilePos);
    OD_LOG_DIG("Removing Creature Dig Effect");    
    if(mCreature.mDiggingEffect)
    {
        mCreature.removeCreatureEffect(mCreature.mDiggingEffect);
        mCreature.mDiggingEffect = nullptr;
    }
    mCreature.parkedBit = false;
}

std::function<bool()> CreatureActionDigTile::action()
{
    return std::bind(&CreatureActionDigTile::handleDigTile,
        std::ref(mCreature), std::ref(mTileDig), std::ref(mTilePos));
}

//! \brief Gives the gold of one dig step to the worker, the seat statistics and the level script. The worker carries the
//! whole part, the fraction stays in its remainder; the statistics and the script get the whole part as well.
//! \param creature The mining worker.
//! \param tileDig The mined tile.
//! \param gold The gold of this step, may have a fraction.
static void payMinedGold(Creature& creature, Tile& tileDig, double gold)
{
    int32_t wholeGold = creature.addGoldCarriedFraction(gold);
    creature.getSeat()->addGoldMined(wholeGold);
    creature.getGameMap()->getLevelScript().observeGoldMined(creature.getSeat()->getId(),
        tileDig.getX(), tileDig.getY(), wholeGold);
}

//! \brief Performs digging with unchanged timing and reports actual gold, stroke tile and the next step interval.
bool CreatureActionDigTile::handleDigTile(Creature& creature, Tile& tileDig, Tile& tilePos)
{
    Tile* myTile = creature.getPositionTile();
    if(myTile == nullptr)
    {
        OD_LOG_ERR("creature=" + creature.getName() + ", pos=" + Helper::toString(creature.getPosition()));
        creature.popAction();
        return false;
    }

    // Check if the tile should still be dug (it may have been dug by another worker)
    if(!tileDig.getMarkedForDigging(creature.getSeat()->getPlayer()) ||
       !tileDig.isDiggable(creature.getSeat()))
    {
        creature.popAction();
        return true;
    }


    if(tileDig.getWorkerDiggingSlot(creature, tilePos) < 0)
    {
        creature.popAction();
        return true;
    }
    const Ogre::Vector2 desired = tileDig.getWorkerDiggingPosition(creature);
    const Ogre::Vector2 current(creature.getPosition().x, creature.getPosition().y);
    if(!creature.parkedBit || current.squaredDistance(desired) > 0.0025f)
    {
        if(!creature.parkToWallTile(&tileDig, &tilePos))
        {
            creature.popAction();
            return false;
        }
        return true;
    }
    // Dig out the tile by decreasing the tile's fullness.
    Ogre::Vector3 walkDirection(tileDig.getX() - tilePos.getX(), tileDig.getY() - tilePos.getY(), 0);
    walkDirection.normalise();
    if(creature.mDiggingEffect == nullptr)
    {
        OD_LOG_DIG("Adding Creature Dig Effect");
        creature.mDiggingEffect = new CreatureEffectDigTile(-1, 1.0, "Examples/Smoke");
        creature.addCreatureEffect(creature.mDiggingEffect);
    }
    creature.setAnimationState(EntityAnimation::dig_anim, true, walkDirection);    
    // One critical roll per dig step: a critical step removes CritDamageMultiplier times the fullness of a dirt or wall
    // tile and pays that many times the step gold on a gold or gem wall (on a gold wall at most what is left)
    const bool critical = creature.rollCritical();
    const double criticalFactor = critical ? ConfigManager::getSingleton().getCritDamageMultiplier() : 1.0;
    // The dig% passives speed up the digging and raise the gold of a step; the experience below does not use them
    const double digFactor = creature.getDigFactor();
    // Gold walls are mined by gold per step (not by the dig rate of the worker), every other tile is dug as before
    double amountDug = 0.0;
    if(tileDig.getType() == TileType::gold)
        amountDug = tileDig.digOutGold(digFactor * criticalFactor);
    else
        amountDug = tileDig.digOut(creature.getDigRate() * digFactor * criticalFactor);
    if(amountDug > 0.0)
    {
        if(tileDig.getType() == TileType::gold)
        {
            CosmeticEvent stroke(CosmeticEventType::digStroke);
            stroke.mSubject = creature.getName();
            stroke.mValue = static_cast<int32_t>(tileDig.getType());
            stroke.mPosition = Ogre::Vector3(static_cast<Ogre::Real>(tileDig.getX()),
                static_cast<Ogre::Real>(tileDig.getY()), 0.0f);
            creature.fireCosmeticEvent(stroke, false);
        }

        if(critical)
        {
            creature.fireCriticalOnStructure("dig", Ogre::Vector3(static_cast<Ogre::Real>(tileDig.getX()),
                static_cast<Ogre::Real>(tileDig.getY()), 0.0f));
        }
        creature.receiveExp(1.5 * creature.getDigRate() / 20.0);

        // If the tile is a gold tile accumulate gold for this creature.
        switch(tileDig.getType())
        {
            case TileType::gold:
            {
                // The gold of this step is the amount the tile paid (density, skirmish setting and last step included)
                payMinedGold(creature, tileDig, amountDug);
                if(tileDig.getFullness() <= 0.0)
                    ++creature.getSeat()->getStatistics().mGoldTilesMined;

                // Receive experience for digging gold
                creature.receiveExp(creature.getDigRate() / 20.0);
                break;
            }
            case TileType::gem:
            {
                // Gem tiles are endless and pay a fixed gold per step, independent of the worker level
                static const double gemGoldPerDigStep = ConfigManager::getSingleton().getGemGoldPerDigStep();
                payMinedGold(creature, tileDig, gemGoldPerDigStep * digFactor * criticalFactor);
                // Receive experience for digging
                creature.receiveExp(creature.getDigRate() / 20.0);
                break;
            }
            default:
                break;
        }

        // If the tile has been dug out, move into that tile and try to continue digging.
        if (tileDig.getFullness() <= 0.0)
        {
            CosmeticEvent event(CosmeticEventType::digFinished);
            event.mSubject = creature.getName();
            event.mValue = static_cast<int32_t>(tileDig.getType());
            event.mPosition = Ogre::Vector3(static_cast<Ogre::Real>(tileDig.getX()),
                static_cast<Ogre::Real>(tileDig.getY()), 0.0f);
            creature.fireCosmeticEvent(event, false);

            creature.popAction();
            creature.receiveExp(2.5);
            creature.parkedBit = false;
            creature.setDestination(&tileDig);
        }
        //Set sound position and play dig sound.
        creature.fireCreatureSound(CreatureSound::Dig);
    }
    else
    {
        //We tried to dig a tile we are not able to
        //Completely bail out if this happens.
        creature.clearActionQueue();
    }

    // Check to see if we are carrying the maximum amount of gold we can carry, and if so, try to take it to a treasury.
    if (creature.getGoldCarried() >= creature.getGoldCapacity())
    {
        // We create the treasury object and push action to deposit it
        TreasuryObject* obj = new TreasuryObject(creature.getGameMap(), creature.getGoldCarried());
        creature.resetGoldCarried();
        Ogre::Vector3 pos(static_cast<Ogre::Real>(myTile->getX()), static_cast<Ogre::Real>(myTile->getY()), 0.0f);
        obj->addToGameMap();
        obj->createMesh();
        obj->setPosition(pos);

        bool isTreasuryAvailable = false;
        for(Room* room : creature.getGameMap()->getRooms())
        {
            if(room->getSeat() != creature.getSeat())
                continue;

            if(room->getTotalGoldStorage() <= 0)
                continue;

            if(room->getTotalGoldStored() >= room->getTotalGoldStorage())
                continue;

            if(room->numCoveredTiles() <= 0)
                continue;

            Tile* tile = room->getCoveredTile(0);
            if(!creature.getGameMap()->pathExists(&creature, myTile, tile))
                continue;

            isTreasuryAvailable = true;
            break;
        }

        if(isTreasuryAvailable)
        {
            // We do not push CreatureActionType::searchEntityToCarry because we want
            // this worker to be count as digging, not as carrying stuff
            
            creature.pushAction(Utils::make_unique<CreatureActionGrabEntity>(creature, *obj));
            if(creature.mDiggingEffect)
            {
                creature.removeCreatureEffect(creature.mDiggingEffect);
                creature.mDiggingEffect = nullptr;
            }            
            return true;
        }

        if((creature.getSeat()->getPlayer() != nullptr) &&
            creature.getSeat()->getPlayer()->getIsHuman())
        {
            creature.getSeat()->getPlayer()->notifyNoTreasuryAvailable();
        }
        else if(creature.getSeat()->getPlayer() != nullptr)
        {
            creature.getSeat()->getPlayer()->notifyNoTreasuryAvailable();
        }
    }
    if(amountDug > 0.0 && tileDig.getFullness() > 0.0)
        creature.recordWorkerStepRecovery();
    return false;
}
