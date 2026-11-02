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

#include "ai/AIFactory.h"

#include "ai/KeeperAI.h"
#include "ai/KeeperAIType.h"
#include "utils/LogManager.h"

namespace AIFactory
{
//! \brief Creates the keeper AI of the given level for a player.
//! \param gameMap The map the AI plays on.
//! \param player The player the AI controls.
//! \param type The AI level.
//! \return The new AI, or nullptr (with an error in the log) for any other AI type.
BaseAI* createAI(GameMap& gameMap, Player& player, KeeperAIType type)
{
    // All five levels use the configured mind; the controller reads the selected level.
    switch(type)
    {
        case KeeperAIType::easy:
        case KeeperAIType::medium:
        case KeeperAIType::normal:
        case KeeperAIType::hard:
        case KeeperAIType::hell:
            return new KeeperAI(gameMap, player, type);
        default:
            break;
    }
    OD_LOG_ERR("Asked wrong AI type=" + KeeperAITypes::toString(type));
    return nullptr;
}
} // namespace AIFactory
