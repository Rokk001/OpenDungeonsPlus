#include "creatureaction/CreatureActionInfirmaryRest.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "rooms/RoomInfirmary.h"
#include <utility>

CreatureActionInfirmaryRest::CreatureActionInfirmaryRest(Creature& creature, RoomInfirmary& room) : CreatureAction(creature),mRoom(room)
{
    for(const std::pair<const size_t,RoomInfirmary::PatientInfo>& entry : room.getPatients())
        if(entry.second.creature==&creature)
        {
            const RoomInfirmary::CotInfo& cot=room.getCots().at(entry.first);
            Ogre::Vector3 direction(static_cast<Ogre::Real>(creature.getDefinition()->getBedOrientX()),static_cast<Ogre::Real>(creature.getDefinition()->getBedOrientY()),0.0);
            if(cot.rotation!=0.0) std::swap(direction.x,direction.y);
            creature.setAnimationState(EntityAnimation::sleep_anim,false,direction,false);
            break;
        }
}
CreatureActionInfirmaryRest::~CreatureActionInfirmaryRest()
{ mRoom.releasePatient(mCreature); }
std::function<bool()> CreatureActionInfirmaryRest::action() // allowed-lambda: signature required by CreatureAction
{ return std::bind(&CreatureActionInfirmaryRest::handleRest,this); }
bool CreatureActionInfirmaryRest::handleRest()
{
    if(mRoom.getPatient(mCreature)==nullptr) { mCreature.popAction();return false; }
    mRoom.restPatient(mCreature);
    return false;
}
