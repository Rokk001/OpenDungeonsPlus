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

//! \brief The campaign menu: list of the campaign levels with briefing, and
//! the debriefing of the level that was played last.
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
    //! \brief Level index the debriefing text belongs to
    size_t mResultLevel;

    void fillLevelList();
    void selectLevel(size_t index);

    bool launchSelectedButtonPressed(const CEGUI::EventArgs&);
    bool difficultyButtonPressed(const CEGUI::EventArgs&);
    void updateDifficultyButton();
    bool backButtonPressed(const CEGUI::EventArgs&);
    bool updateDescription(const CEGUI::EventArgs& e = {});
};

#endif // MENUMODECAMPAIGN_H
