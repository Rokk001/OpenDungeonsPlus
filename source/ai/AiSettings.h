/*!
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

#ifndef AISETTINGS_H
#define AISETTINGS_H

#include <array>

//! \brief How the war planner of a keeper AI level estimates the mana of an enemy keeper.
//! own: its own current mana times the noise of the sighting; observed: from the game time and the enemy casts it saw.
enum class EnemyManaEstimateMode { own, observed };

//! \brief The values of one keeper AI level (one column of the [KeeperAILevels] section of ai.cfg).
//! Filled by ConfigManager::getAiLevel(KeeperAIType).
struct AiSettings
{
    double rho, pi, scanPeriod, clickShare, mistakeMultiplier, estimateNoise, tacticTemperature,
           attackAdvantage, focusFire, retreatThreshold, tunnelDetour;
    //! \brief Design priors of the tactics in the order allin, single, split, raid, counter.
    std::array<double, 5> tacticPriors;
    EnemyManaEstimateMode enemyManaEstimate;
};

#endif // AISETTINGS_H
