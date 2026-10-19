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

#include "entities/MissileOneHit.h"

#include "entities/Building.h"
#include "entities/Creature.h"
#include "entities/CombatDamage.h"
#include "entities/GameEntityType.h"
#include "gamemap/GameMap.h"
#include "network/ODPacket.h"
#include "utils/LogManager.h"
#include "utils/Random.h"

#include <iostream>

MissileOneHit::MissileOneHit(GameMap* gameMap, Seat* seat, const std::string& senderName, const std::string& meshName,
        const std::string& particleScript, const Ogre::Vector3& direction, double speed, double physicalDamage, double magicalDamage,
        double elementDamage, GameEntity* entityTarget, bool damageAllies, bool koEnemyCreature, bool notifyPlayerIfHit) :
    MissileObject(gameMap, seat, senderName, meshName, direction, speed, entityTarget, damageAllies, koEnemyCreature),
    mHasHit(false),
    mPhysicalDamage(physicalDamage),
    mMagicalDamage(magicalDamage),
    mElementDamage(elementDamage),
    mPhysicalDamageMin(physicalDamage), mPhysicalDamageMax(physicalDamage),
    mMagicalDamageMin(magicalDamage), mMagicalDamageMax(magicalDamage),
    mElementDamageMin(elementDamage), mElementDamageMax(elementDamage),
    mHasCreatureDamageRange(false), mCreatureStrength(1.0),
    mNotifyPlayerIfHit(notifyPlayerIfHit)
{
    if(!particleScript.empty())
    {
        EntityParticleEffect* effect = new EntityParticleEffect(nextParticleSystemsName(), particleScript, -1);
        mEntityParticleEffects.push_back(effect);
    }
}

MissileOneHit::MissileOneHit(GameMap* gameMap) :
    MissileObject(gameMap),
    mHasHit(false),
    mPhysicalDamage(0.0),
    mMagicalDamage(0.0),
    mElementDamage(0.0),
    mPhysicalDamageMin(0.0), mPhysicalDamageMax(0.0),
    mMagicalDamageMin(0.0), mMagicalDamageMax(0.0),
    mElementDamageMin(0.0), mElementDamageMax(0.0),
    mHasCreatureDamageRange(false), mCreatureStrength(1.0),
    mNotifyPlayerIfHit(false)
{
}

bool MissileOneHit::hitCreature(Tile* tile, GameEntity* entity)
{
    hurt(tile, entity);
    if(mNotifyPlayerIfHit)
        entity->notifyFightPlayer(tile);

    return false;
}

void MissileOneHit::hitTargetEntity(Tile* tile, GameEntity* entityTarget)
{
    hurt(tile, entityTarget);
    if(mNotifyPlayerIfHit)
        entityTarget->notifyFightPlayer(tile);
}

//! \brief Captures a creature skill range independently of the unchanged building damage.
void MissileOneHit::setCreatureDamageRange(double phyMin, double phyMax, double magMin, double magMax,
    double eleMin, double eleMax, double strength)
{
    mPhysicalDamageMin = phyMin;
    mPhysicalDamageMax = phyMax;
    mMagicalDamageMin = magMin;
    mMagicalDamageMax = magMax;
    mElementDamageMin = eleMin;
    mElementDamageMax = eleMax;
    mCreatureStrength = strength;
    mHasCreatureDamageRange = true;
}

//! \brief Rolls creature damage after defense while keeping building damage deterministic.
void MissileOneHit::hurt(Tile* tile, GameEntity* entity)
{
    double damageDone = 0.0;
    double rawDamage = mPhysicalDamage + mMagicalDamage + mElementDamage;
    if(mHasCreatureDamageRange && entity->getObjectType() == GameEntityType::creature)
    {
        const double damage = CombatDamage::roll(*static_cast<Creature*>(entity),
            mPhysicalDamageMin, mPhysicalDamageMax, mMagicalDamageMin, mMagicalDamageMax,
            mElementDamageMin, mElementDamageMax, &rawDamage) * mCreatureStrength;
        rawDamage *= mCreatureStrength;
        damageDone = entity->takeDamage(this, damage, 0.0, 0.0, 0.0, tile, getKoEnemyCreature());
    }
    else
        damageDone = entity->takeDamage(this, 0.0, mPhysicalDamage, mMagicalDamage, mElementDamage, tile,
            getKoEnemyCreature());
    mHasHit = true;

    // Tell the clients what the shot did (cosmetic only, the damage above is already done)
    if(!mShooterName.empty() && (entity->getObjectType() == GameEntityType::creature))
    {
        Creature* creature = static_cast<Creature*>(entity);
        creature->fireHitResult(mShooterName, damageDone, rawDamage, true);
    }
}

void MissileOneHit::missileStopped()
{
    // A shot at a creature that ended without hurting anything: it hit a wall or the creature was gone from the tile
    if(mHasHit || mShooterName.empty() || mTargetName.empty())
        return;

    Creature* target = getGameMap()->getCreature(mTargetName);
    if((target == nullptr) || !target->isAlive() || !target->getIsOnMap())
        return;

    target->fireHitMissed(mShooterName);
}

MissileOneHit* MissileOneHit::getMissileOneHitFromStream(GameMap* gameMap, std::istream& is)
{
    MissileOneHit* obj = new MissileOneHit(gameMap);
    obj->importFromStream(is);
    return obj;
}

MissileOneHit* MissileOneHit::getMissileOneHitFromPacket(GameMap* gameMap, ODPacket& is)
{
    MissileOneHit* obj = new MissileOneHit(gameMap);
    obj->importFromPacket(is);
    return obj;
}

void MissileOneHit::exportToStream(std::ostream& os) const
{
    MissileObject::exportToStream(os);
    os << mPhysicalDamage << "\t";
    os << mMagicalDamage << "\t";
    os << mElementDamage << "\t";

    uint32_t nbEffects = mEntityParticleEffects.size();
    os << "\t" << nbEffects;
    for(EntityParticleEffect* effect : mEntityParticleEffects)
    {
        os << "\t" << effect->mScript;
    }
    os << "\tCreatureDamageRange\t" << mHasCreatureDamageRange
       << "\t" << mPhysicalDamageMin << "\t" << mPhysicalDamageMax
       << "\t" << mMagicalDamageMin << "\t" << mMagicalDamageMax
       << "\t" << mElementDamageMin << "\t" << mElementDamageMax
       << "\t" << mCreatureStrength;
}

bool MissileOneHit::importFromStream(std::istream& is)
{
    if(!MissileObject::importFromStream(is))
        return false;
    if(!(is >> mPhysicalDamage))
        return false;
    if(!(is >> mMagicalDamage))
        return false;
    if(!(is >> mElementDamage))
        return false;
    uint32_t nbEffects;
    if(!(is >> nbEffects))
        return false;
    while(nbEffects > 0)
    {
        --nbEffects;
        std::string effectScript;
        if(!(is >> effectScript))
            return false;
        EntityParticleEffect* effect = new EntityParticleEffect(nextParticleSystemsName(), effectScript, -1);
        mEntityParticleEffects.push_back(effect);
    }

    // The marker preserves old saves and leaves derived projectile fields unread.
    const std::streampos rangePosition = is.tellg();
    std::string rangeMarker;
    if(!(is >> rangeMarker))
    {
        is.clear();
        return true;
    }
    if(rangeMarker != "CreatureDamageRange")
    {
        is.seekg(rangePosition);
        return static_cast<bool>(is);
    }
    if(!(is >> mHasCreatureDamageRange >> mPhysicalDamageMin >> mPhysicalDamageMax
        >> mMagicalDamageMin >> mMagicalDamageMax >> mElementDamageMin >> mElementDamageMax
        >> mCreatureStrength))
        return false;

    return true;
}
