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

#include "creaturemood/CreatureMoodHpLoss.h"

#include "creaturemood/CreatureMoodManager.h"
#include "entities/Creature.h"
#include "utils/ConfigManager.h"

#include <algorithm>

static const std::string CreatureMoodHpLossName = "HpLoss";

namespace
{
//! \brief Factory that creates CreatureMoodHpLoss objects from the creature configuration.
class CreatureMoodHpLossFactory : public CreatureMoodFactory
{
    //! \brief Creates a new CreatureMoodHpLoss with default values.
    CreatureMood* createCreatureMood() const override
    { return new CreatureMoodHpLoss; }

    //! \brief Returns the configuration name of this modifier.
    const std::string& getCreatureMoodName() const override
    {
        return CreatureMoodHpLossName;
    }
};

// Register the factory
static CreatureMoodRegister reg(new CreatureMoodHpLossFactory);
}

//! \brief Returns the name under which this modifier is listed in the creature configuration.
const std::string& CreatureMoodHpLoss::getModifierName() const
{
    return CreatureMoodHpLossName;
}

//! \brief Returns 1 while the health of the creature is below LowHealthWalkThresholdPercent of its maximum, otherwise 0.
double CreatureMoodHpLoss::getAmount(const Creature& creature) const
{
    if(creature.getMaxHp() <= 0.0)
        return 0.0;

    const double thresholdPercent = ConfigManager::getSingleton().getLowHealthWalkThresholdPercent();
    return (creature.getHP() / creature.getMaxHp() * 100.0 < thresholdPercent) ? 1.0 : 0.0;
}

//! \brief Returns a copy of this modifier.
CreatureMoodHpLoss* CreatureMoodHpLoss::clone() const
{
    return new CreatureMoodHpLoss(*this);
}
