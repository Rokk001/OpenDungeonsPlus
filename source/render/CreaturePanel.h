/*
 *  Copyright (C) 2026 OpenDungeons Team
 *  SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef CREATUREPANEL_H
#define CREATUREPANEL_H

#include "game/CreaturePanelData.h"
#include <CEGUI/Event.h>
#include <CEGUI/Size.h>
#include <set>
#include <vector>

class GameMap;
class Gui;
namespace CEGUI { class Window; }

class CreaturePanel
{
public:
    CreaturePanel(GameMap& gameMap, Gui& gui, CEGUI::Window* parent);
    ~CreaturePanel();
    void setData(const CreaturePanelData& data);
    void update();

private:
    //! \brief One column of the panel, showing a single creature type.
    struct Slot
    {
        //! \brief Container of the column
        CEGUI::Window* window;
        //! \brief Portrait image of the creature type
        CEGUI::Window* portrait;
        //! \brief Count labels below each other, one per criterion of the selected view
        std::array<CEGUI::Window*, 4> counts;
        //! \brief Creature class name currently shown in this column
        std::string type;
    };

    void addSlot();
    void selectView(size_t view);
    void scroll(int direction);
    void pickUp(const std::string& type, CreaturePanelCriterion criterion, bool workersOnly, int levelOrder = 0);
    void focus(const std::string& type);

    GameMap& mGameMap;
    Gui& mGui;
    CEGUI::Window* mWindow;
    CEGUI::Window* mStrip;
    std::array<CEGUI::Window*, 4> mWorkerCounts;
    std::array<CEGUI::Window*, 4> mViewButtons;
    CEGUI::Window* mPrevious;
    CEGUI::Window* mNext;
    std::vector<Slot> mSlots;
    std::vector<CEGUI::Event::Connection> mConnections;
    CreaturePanelData mData;
    std::set<std::string> mPendingPickups;
    CEGUI::Sizef mLastSize;
    size_t mView = 0;
    size_t mFirstType = 0;
    size_t mVisibleSlots = 0;
    size_t mTypeCount = 0;
    bool mHasData = false;
    bool mDirty = true;
};

#endif
