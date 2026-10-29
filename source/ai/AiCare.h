#ifndef AICARE_H
#define AICARE_H

class KeeperAI;

namespace CARE
{
//! \brief Moves idle fighters to available training places, strongest first unless the row mistakes the order.
void idleToHall(KeeperAI& ai);
//! \brief Moves capped trainees to the arena and fighters without work to the casino or temple.
void levelWatch(KeeperAI& ai);
//! \brief Takes upset creatures to the available mood room their class likes most.
void moodRelief(KeeperAI& ai);
}

#endif // AICARE_H
