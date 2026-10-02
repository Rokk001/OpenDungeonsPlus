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

#ifndef MENUMODECAMPAIGN_H
#define MENUMODECAMPAIGN_H

#include "AbstractApplicationMode.h"

#include <string>
#include <vector>

//! \brief The campaign menu: a map where each level is a territory. Levels that
//! can be started highlight under the mouse and start on a click. The briefing
//! of the territory under the mouse and the debriefing of the level that was
//! played last are shown beside the map.
class MenuModeCampaign: public AbstractApplicationMode
{
public:
    MenuModeCampaign(ModeManager*);

    //! \brief Called when the mode is activated
    //! Used to call the corresponding Gui Sheet.
    void activate() final override;

    //! \brief Reads the campaign definition and the saved progress from disk.
    //! Returns false if there is no campaign definition.
    static bool loadCampaign();

private:
    //! \brief Debriefing text of the level that was played last (empty if none)
    std::string mResultText;
    //! Windows of the territory blocks currently on the map
    std::vector<CEGUI::Window*> mTerritoryWindows;
    //! Level index under the mouse, or the number of levels if none
    size_t mHoveredLevel;

    void fillMap();
    void clearMap();
    void updateTerritoryColour(CEGUI::Window* block);
    void showDescription(size_t index);
    void startLevel(size_t index);

    bool territoryEntered(const CEGUI::EventArgs& e);
    bool territoryLeft(const CEGUI::EventArgs& e);
    bool territoryClicked(const CEGUI::EventArgs& e);
    bool difficultyButtonPressed(const CEGUI::EventArgs&);
    void updateDifficultyButton();
    bool backButtonPressed(const CEGUI::EventArgs&);
};

#endif // MENUMODECAMPAIGN_H
