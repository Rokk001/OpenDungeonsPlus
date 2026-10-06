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

#ifndef KEEPERWEALTH_H
#define KEEPERWEALTH_H

#include "rooms/TreasurySettings.h"

//! \brief The wealth tier of a keeper, the only thing about its gold that other keepers get to know.
//! The server sends it for the heart and the portal of the keeper to the seats that see the tile of the
//! building (cosmetic event keeperWealth); the amount of gold never leaves the server.
namespace KeeperWealth
{
//! Tier 0: not rich. Tier 1: gold held reaches the share of the treasury capacity and at least the minimum
//! amount (config/treasury.cfg PortalRichShare and PortalRichMinGold). More tiers can be added at the end.
inline int tier(int gold, int goldMax)
{
    if(goldMax <= 0 || gold < TreasurySettings::current().portalRichMinGold)
        return 0;
    return (static_cast<float>(gold) >= TreasurySettings::current().portalRichShare * static_cast<float>(goldMax)) ? 1 : 0;
}

//! Server: turns between two announcements of a building (about 2 s)
static const int announceTurns = 3;
//! Client: seconds an announcement counts; longer than the interval so one lost or late event does not blink
//! the dust, and short enough that the dust stops soon after the building leaves the view of the receiver
static const float announceLifetime = 4.0f;
}

#endif // KEEPERWEALTH_H
