#include "rooms/RoomInfirmary.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "ODApplication.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "game/SkillManager.h"
#include "game/SkillType.h"
#include "gamemap/GameMap.h"
#include "utils/ConfigManager.h"
#include <algorithm>

//! \brief Tests the selected payer without changing a purse or treasury.
bool RoomInfirmary::canPayAdmission(const Creature& creature, bool manual) const
{
    const double admission = ConfigManager::getSingleton().getRoomConfigDouble("InfirmaryAdmissionWageShare") *
        creature.getDefinition()->getFee(creature.getLevel());
    const Player* player = getSeat()->getPlayer();
    if(manual || getSeat()->getInfirmaryPayer() == 0 || (player != nullptr && !player->getIsHuman()))
    {
        double available = 0.0;
        for(const Room* room : getGameMap()->getRooms())
            if(room->getSeat() == getSeat())
                available += room->getTotalGoldStored();
        return available >= admission;
    }
    return creature.getGoldCarried() >= admission;
}

//! \brief Charges one admission and applies its temporary mood only after payment succeeds.
bool RoomInfirmary::payAdmission(Creature& creature, bool manual, double& amount, int& payer)
{
    const Player* player = getSeat()->getPlayer();
    payer = (manual || (player != nullptr && !player->getIsHuman())) ? 0 : getSeat()->getInfirmaryPayer();
    amount = ConfigManager::getSingleton().getRoomConfigDouble("InfirmaryAdmissionWageShare") *
        creature.getDefinition()->getFee(creature.getLevel());
    if(!canPayAdmission(creature, manual))
        return false;
    if(payer == 0)
    {
        if(!getGameMap()->withdrawFromTreasuries(amount, getSeat()))
            return false;
    }
    else
    {
        creature.addGoldCarried(-amount);
        getGameMap()->addGoldToSeat(amount, getSeat()->getId());
    }
    creature.setInfirmaryAdmissionMood(payer == 1);
    return true;
}

//! \brief Heals one paid turn, retaining fractional mana and collecting one shortage notice per room.
bool RoomInfirmary::healPatient(Creature& creature)
{
    const int64_t turn = getGameMap()->getTurnNumber();
    if(turn != mHealingTurn)
    {
        if(!mHealingTurnFailed)
            mManaShortageNotified = false;
        mHealingTurn = turn;
        mHealingTurnFailed = false;
    }
    if(!getSeat()->getInfirmaryHealOn())
    {
        mHealingTurnFailed = true;
        return false;
    }
    const double maximum = creature.getMaxHp();
    const double seconds = SkillManager::getResearchValue(getSeat(), SkillType::roomInfirmary,
        ConfigManager::getSingleton().getRoomConfigDouble("InfirmaryFullHealSeconds"), ResearchEffect::HealTime);
    const double gain = std::min(maximum - creature.getHP(),
        maximum / (seconds * ODApplication::turnsPerSecond));
    if(gain <= 0.0)
        return false;
    const double mana = ConfigManager::getSingleton().getRoomConfigDouble("InfirmaryManaPerWage") *
        creature.getDefinition()->getFee(creature.getLevel()) * gain / maximum;
    if(!getSeat()->takeMana(mana))
    {
        mHealingTurnFailed = true;
        if(!mManaShortageNotified)
        {
            mManaShortageNotified = true;
            if(getSeat()->getPlayer() != nullptr)
                getSeat()->getPlayer()->notifyInfirmaryEvent();
        }
        return false;
    }
    creature.setHP(creature.getHP() + gain);
    const uint32_t glowTurns = ConfigManager::getSingleton().getRoomConfigUInt32("InfirmaryHealGlowTurns");
    if(turn % glowTurns == 0)
        creature.addParticleEffect("InfirmaryHealGlow", glowTurns);
    return true;
}

//! \brief Returns the shared discharge health percentage for this keeper.
int RoomInfirmary::getDischargeThreshold() const
{
    return getSeat()->getInfirmaryThreshold();
}
