#ifndef CREATUREACTIONINFIRMARYREST_H
#define CREATUREACTIONINFIRMARYREST_H
#include "creatureaction/CreatureAction.h"
class RoomInfirmary;
//! \brief Keeps an admitted patient lying until discharge or interruption.
class CreatureActionInfirmaryRest : public CreatureAction
{
public:
    //! \brief Starts resting on the admitted cot.
    CreatureActionInfirmaryRest(Creature& creature, RoomInfirmary& room);
    //! \brief Frees the cot whenever another action interrupts treatment.
    ~CreatureActionInfirmaryRest() override;
    //! \brief Returns the patient rest action type.
    CreatureActionType getType() const override { return CreatureActionType::infirmaryRest; }
    //! \brief Returns the next patient upkeep step.
    std::function<bool()> action() override; // allowed-lambda: signature required by CreatureAction
    //! \brief Runs one turn of the patient's treatment.
    bool handleRest();
private:
    RoomInfirmary& mRoom;
};
#endif
