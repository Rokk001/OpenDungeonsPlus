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

#ifndef SOCIALWINDOW_H
#define SOCIALWINDOW_H

#include <CEGUI/EventArgs.h>

#include <stdint.h>
#include <string>
#include <vector>

class GameMap;

namespace CEGUI
{
class Window;
}

//! \brief The Dungeonbook: a window with the list of the creatures of the local player and the
//! feed of their posts (see social/PostLog.h). The window itself comes from
//! gui/WindowSocial.layout, the event handlers are connected by the game mode. The window only
//! redraws while it is visible and only when the post log or the roster changed.
class SocialWindow
{
public:
    SocialWindow(CEGUI::Window* rootWindow, GameMap& gameMap);

    //! \brief Shows the window on top of the other ones and draws list and feed.
    void show();
    //! \brief Same, with the given creature selected in the list (all creatures are listed then).
    void showCreature(const std::string& creatureName);
    void hide();
    bool isVisible() const;

    //! \brief Called every frame by the game mode, only does something while the window is visible.
    void update(float elapsed);

    bool onCloseClicked(const CEGUI::EventArgs& e);
    bool onFilterClicked(const CEGUI::EventArgs& e);
    bool onFeedModeClicked(const CEGUI::EventArgs& e);
    bool onSelectionChanged(const CEGUI::EventArgs& e);
    bool onOpenProfileClicked(const CEGUI::EventArgs& e);

    //! \brief "Latest: <text> (2 min ago)" for the newest post of the creature, empty if it has none.
    static std::string describeLatestPost(const std::string& creatureName, int64_t turnNow);

private:
    enum class CreatureFilter
    {
        All,
        Workers,
        Fighters,
        Unhappy
    };

    void rebuildCreatureList();
    void rebuildFeed();
    void updateButtons();

    GameMap& mGameMap;
    CEGUI::Window* mWindow;
    CreatureFilter mFilter;
    bool mSelectedOnly;
    //! True while the list is rebuilt, selection events are ignored then
    bool mRebuildingList;
    std::string mSelectedCreature;
    //! Creature names of the list items, indexed by the item id
    std::vector<std::string> mListedCreatures;
    uint32_t mShownRosterVersion;
    uint32_t mShownPostVersion;
    float mSinceRefreshCheck;
    float mSinceFeedRebuild;
};

#endif // SOCIALWINDOW_H
