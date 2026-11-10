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

#include "social/PostLog.h"

#include <CEGUI/Event.h>
#include <CEGUI/EventArgs.h>

#include <stdint.h>
#include <string>
#include <vector>

class GameMap;

namespace CEGUI
{
class Image;
class Scrollbar;
class Window;
}

//! \brief The Dungeonbook (gui/WindowSocial.layout). Its start page lists the creatures of the local player and its
//! allies on the left (portrait, name, level and mood, filtered by All, Workers, Fighters or Unhappy) and the feed of
//! all their posts (see social/PostLog.h) on the right. A click on a creature opens its own pages: its feed, its social
//! profile, its values and its inventory, switched by the navigation bar at the bottom. The head of these pages has a
//! back arrow to the start page and arrows to the previous and next creature of the list. The window connects its own
//! controls; the game mode connects the close button, the HUD button and the key. It only redraws while it is visible
//! and only when the post log or the roster changed, or every few seconds for the ages of the posts.
class SocialWindow
{
public:
    SocialWindow(CEGUI::Window* rootWindow, GameMap& gameMap);
    ~SocialWindow();

    //! \brief Shows the window on top of the other ones and draws the shown page.
    void show();
    //! \brief Same, with the inventory page of the given creature (all creatures are listed then).
    void showCreature(const std::string& creatureName);
    void hide();
    bool isVisible() const;

    //! \brief Called every frame by the game mode, only does something while the window is visible.
    void update(float elapsed);

    bool onCloseClicked(const CEGUI::EventArgs& e);

    //! \brief Marks the tab button as the active one (gold, in brackets); the button stays enabled.
    static void setTabState(CEGUI::Window* tab, const std::string& label, bool active);

    //! \brief "Latest: <text> (2 min ago)" for the newest post of the creature, empty if it has none.
    static std::string describeLatestPost(const std::string& creatureName, int64_t turnNow);

    //! \brief The text of a post, used by the post log to keep neighbouring posts different.
    static std::string renderPostTextForLog(const social::Post& post);

private:
    enum class CreatureFilter
    {
        All,
        Workers,
        Fighters,
        Unhappy
    };

    //! The pages of the book: the start page and the four pages of one creature
    enum class Page
    {
        Home,
        Feed,
        Profile,
        Values,
        Inventory
    };

    //! \brief The filter dropdown returns to the overview.
    bool onFilterClicked(const CEGUI::EventArgs& e);
    //! \brief A creature of the list (user string "Row"): opens its inventory page.
    bool onListRowClicked(const CEGUI::EventArgs& e);
    //! \brief A button of the navigation bar (user string "Page").
    bool onNavClicked(const CEGUI::EventArgs& e);
    //! \brief The back arrow: returns to the start page and clears the selection.
    bool onBackClicked(const CEGUI::EventArgs& e);
    //! \brief The arrows around the name: the previous or next creature of the list, on the same page.
    bool onPreviousClicked(const CEGUI::EventArgs& e);
    bool onNextClicked(const CEGUI::EventArgs& e);
    //! \brief A friend or foe name in the profile: shows the inventory of that creature.
    bool onLinkClicked(const CEGUI::EventArgs& e);
    //! \brief The scrollbars of the list and of the feeds move the shown rows.
    bool onListScrolled(const CEGUI::EventArgs& e);
    bool onFeedScrolled(const CEGUI::EventArgs& e);
    //! \brief The mouse wheel over the list or over a feed moves its scrollbar.
    bool onListWheel(const CEGUI::EventArgs& e);
    bool onFeedWheel(const CEGUI::EventArgs& e);

    //! \brief Subscribes to an event of a window of the book; the connection is released with the book.
    void connect(CEGUI::Window* window, const CEGUI::String& event, const CEGUI::Event::Subscriber& subscriber);
    //! \brief Builds the roster (server roster or locally known creatures) and the filtered, sorted list.
    void rebuildCreatureList();
    //! \brief Shows the creatures of the list from the scroll position on, the selected one highlighted.
    void refreshListRows();
    //! \brief Fills the feed of the shown page: all posts on the start page, the posts of the creature on its feed.
    void rebuildFeed();
    //! \brief Shows a page, updates the navigation bar and the head and fills the page.
    void showPage(Page page);
    //! \brief Selects the creature (resetting the filter if it hides the creature) and shows the given page.
    void selectCreature(const std::string& creatureName, Page page);
    //! \brief Selects the previous (-1) or next (+1) creature of the list, wrapping around.
    void stepCreature(int direction);
    //! \brief Fills the shown page of the selected creature.
    void refreshPage();
    void refreshHeader(const social::DungeonbookEntry& entry);
    void refreshProfile(const social::DungeonbookEntry& entry);
    void refreshValues(const social::DungeonbookEntry& entry);
    void refreshInventory(const social::DungeonbookEntry& entry);
    //! \brief The roster entry of the creature, null if it is not in the roster.
    const social::DungeonbookEntry* findEntry(const std::string& creatureName) const;
    //! \brief The composed picture of the creature (round or square), else its round tinted portrait; null if neither exists.
    const CEGUI::Image* findPortrait(const std::string& creatureName, const std::string& className, bool worker,
        bool circular) const;
    //! \brief The game picture of a post (room or thing it is about), else the portrait of its creature.
    const CEGUI::Image* findPostPicture(const social::Post& post) const;
    //! \brief Mood word and symbol of the creature for the list and the profile.
    void describeMood(const social::DungeonbookEntry& entry, std::string& text, std::string& icon) const;

    GameMap& mGameMap;
    CEGUI::Window* mWindow;
    //! Which creatures the list shows
    CreatureFilter mFilter;
    //! The shown page
    Page mPage;
    //! True while rows and scrollbars are filled, their scroll events are ignored then
    bool mUpdatingRows;
    //! Name of the selected creature, empty if none is selected
    std::string mSelectedCreature;
    //! All creatures of the roster, as received from the server or collected from the known creatures
    std::vector<social::DungeonbookEntry> mEntries;
    //! Names of the creatures the filtered list shows, in list order
    std::vector<std::string> mListedCreatures;
    //! The shared social profile page inside the profile page, created when it is needed the first time
    CEGUI::Window* mProfilePage;
    //! Subscriptions of the controls of the book and of the friend and foe names of the profile page
    std::vector<CEGUI::Event::Connection> mLinkConnections;
    //! Roster version of the post log the list was built for
    uint32_t mShownRosterVersion;
    //! Post version of the post log the feed was built for
    uint32_t mShownPostVersion;
    //! Seconds since update() last checked for changes
    float mSinceRefreshCheck;
    //! Seconds since the feed was last rebuilt
    float mSinceFeedRebuild;
    //! Post version of the post log the creature page was built for
    uint32_t mShownProfilePostVersion;
    //! Seconds since the creature page was last refreshed
    float mSinceProfileRefresh;
};

#endif // SOCIALWINDOW_H
