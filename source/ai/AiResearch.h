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

#ifndef AIRESEARCH_H
#define AIRESEARCH_H

#include <vector>

class KeeperAI;
enum class SkillType;

namespace RES
{
//! \brief Retains research observations and the next eligible queue look for one keeper.
struct ResearchState
{
    bool mLoaded = false;
    bool mTunnelOpen = false;
    double mNextLook = 0.0;
    std::vector<SkillType> mQueue;
};

//! \brief Chooses the next legal research entry with the research precedence and one mistake draw.
SkillType chooseResearch(KeeperAI& ai);
//! \brief Refills an empty research queue with the configured entries per look.
void refillQueue(KeeperAI& ai);
//! \brief Registers research looks, queue-empty symptoms and saved research state.
void bind(KeeperAI& ai);
}

#endif // AIRESEARCH_H
