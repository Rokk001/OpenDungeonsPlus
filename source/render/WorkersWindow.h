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

#ifndef WORKERSWINDOW_H
#define WORKERSWINDOW_H

#include "game/WorkerJobs.h"

#include <CEGUI/Event.h>
#include <CEGUI/EventArgs.h>
#include <CEGUI/UDim.h>

#include <array>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <vector>

class GameMap;
class Seat;

namespace CEGUI
{
class Window;
}

//! \brief The Workers window of a keeper: the fixed number of workers per job, the mode for free workers, the
//! priority order of the jobs, the carry order and the "gold first" switch, plus the number of free workers and
//! of workers on every job. The window comes from gui/WindowWorkers.layout, the HUD button from gui/ModeGame.layout.
//! The window only shows what the server stored: every change is sent as the complete settings and the stored
//! settings come back with the keeper's regular data.
class WorkersWindow
{
public:
    //! \brief Number of jobs and of tablets in the window.
    static const std::size_t JOB_COUNT = 6;
    //! \brief Number of carry order entries.
    static const std::size_t CARRY_COUNT = 7;

    //! \brief Finds the window and the HUD button in the root window and connects their events.
    WorkersWindow(CEGUI::Window* rootWindow, GameMap& gameMap);
    //! \brief Disconnects the events.
    ~WorkersWindow();

    //! \brief Opens the window on top of the others; does nothing without a keeper seat.
    void show();
    //! \brief Closes the window and forgets the selection and a running drag.
    void hide();
    //! \brief True while the window is open.
    bool isVisible() const;
    //! \brief Opens the closed window, closes the open one (key J and HUD button).
    void toggle();
    //! \brief Called every frame by the game mode: shows the HUD button for a keeper only and redraws the open window
    //! when what it shows has changed.
    void update();
    //! rief True while a tablet or a carry entry is being dragged; the keeper hand then shows its grabbing pose.
    bool isDragging() const { return mDragTablet >= 0 || mDragCarry >= 0; }

    //! \brief The close button and Esc.
    bool onCloseClicked(const CEGUI::EventArgs& e);
    //! \brief The HUD button.
    bool onButtonClicked(const CEGUI::EventArgs& e);
    //! \brief Mode selector: Automatic or Priority list.
    bool onModeClicked(const CEGUI::EventArgs& e);
    //! \brief A tablet is pressed: selects it and starts a drag.
    bool onTabletPressed(const CEGUI::EventArgs& e);
    //! \brief A tablet drag ends: moves the dragged tablet to the tablet under the pointer.
    bool onTabletReleased(const CEGUI::EventArgs& e);
    //! \brief The left button comes up on the window, a tablet or a carry entry: ends the drag that is running. A drag
    //! can end on any of them, depending on which window holds the pointer.
    bool onDragReleased(const CEGUI::EventArgs& e);
    //! \brief Priority arrows.
    bool onPriorityArrowClicked(const CEGUI::EventArgs& e);
    //! \brief "-" and "+" of a tablet.
    bool onFixedClicked(const CEGUI::EventArgs& e);
    //! \brief A carry entry is pressed: selects it and starts a drag.
    bool onCarryPressed(const CEGUI::EventArgs& e);
    //! \brief A carry entry drag ends: moves the dragged entry to the entry under the pointer.
    bool onCarryReleased(const CEGUI::EventArgs& e);
    //! \brief Carry order arrows.
    bool onCarryArrowClicked(const CEGUI::EventArgs& e);
    //! \brief The "Gold first" tick box.
    bool onGoldFirstClicked(const CEGUI::EventArgs& e);

    //! \brief The order in which the tablets are shown: the keeper's priority list in mode Priority list, the
    //! predefined priority of the game (WorkerDefaultPriority) in mode Automatic.
    static std::array<uint32_t, JOB_COUNT> getDisplayOrder(const WorkerJobSettings& settings,
        const WorkerJobSettings& defaults);

    //! \brief Moves the entry at place from to place to; the entries in between move by one place. False and
    //! no change if a place is out of range or both are the same.
    template<std::size_t N>
    static bool moveOrderEntry(std::array<uint32_t, N>& order, std::size_t from, std::size_t to)
    {
        if(from >= N || to >= N || from == to)
            return false;
        const uint32_t value = order[from];
        if(from < to)
        {
            for(std::size_t i = from; i < to; ++i)
                order[i] = order[i + 1];
        }
        else
        {
            for(std::size_t i = from; i > to; --i)
                order[i] = order[i - 1];
        }
        order[to] = value;
        return true;
    }

    //! \brief The slot a point belongs to when a dragged entry is dropped, -1 if none. Each rect is
    //! {left, top, right, bottom} of a slot in the order of the slots. A slot owns its column: the point may lie
    //! anywhere between the middles of the gaps to the neighbouring slots and in the height of the row of slots plus a
    //! quarter of it above and below, so a drop does not have to hit the small painted area exactly.
    static int32_t getDropSlot(const std::vector<std::array<float, 4> >& rects, float x, float y);

    //! \brief Roman numeral of a rank (0 is rank I).
    static const char* getRankNumeral(std::size_t rank);
    //! \brief Name of a job in the order of WorkerJob.
    static const char* getJobName(uint32_t job);
    //! \brief Name of a carry entry in the order of WorkerCarryEntry.
    static const char* getCarryName(uint32_t entry);

private:
    //! Slide of a slot from the place its entry came from; the offset shrinks to zero within SLIDE_SECONDS
    struct Slide
    {
        float mOffsetX = 0.0f;
        float mOffsetY = 0.0f;
        std::chrono::steady_clock::time_point mStart;
        bool mActive = false;
    };

    //! \brief The seat of the local keeper, or nullptr without a keeper seat.
    Seat* getSeat() const;
    //! \brief Sends the complete proposed settings to the server.
    void sendSettings(const WorkerJobSettings& settings);
    //! \brief Redraws everything from the stored settings and the regular data.
    void refresh();
    //! \brief Everything the window shows as one list of numbers, to see when a redraw is needed.
    std::vector<uint32_t> getShownState() const;
    //! \brief Index of the slot (tablet or carry entry) the point drops on (see getDropSlot), or -1.
    int32_t findSlotAt(const char* prefix, std::size_t count, float x, float y) const;
    //! \brief Shows an arrow button enabled (painted normally) or greyed out.
    void setArrowEnabled(CEGUI::Window* arrow, bool up, bool enabled);
    //! \brief Ends a running drag of tablet or carry entry at the pointer position of the GUI context.
    void finishDrag();
    //! \brief Forgets running slides and the drag feedback: slots at their places, copies hidden, original places opaque.
    void resetFeedback();
    //! rief Shows the copy of the grabbed picture at the pointer and the original place as drop target, or hides both.
    void updateDragFeedback();
    //! rief Starts the slide of every slot whose entry moved from another place.
    void startSlides(const char* prefix, const std::vector<uint32_t>& before, const std::vector<uint32_t>& after,
        std::vector<Slide>& slides);
    //! rief Moves the sliding slots a step towards their places.
    void updateSlides(const char* prefix, std::vector<Slide>& slides, const std::vector<CEGUI::UVector2>& bases);
    //! \brief Reads the slot index from the window of an event, -1 if there is none.
    static int32_t getSlotId(const CEGUI::EventArgs& e);

    GameMap& mGameMap;
    CEGUI::Window* mWindow;
    CEGUI::Window* mButton;
    std::vector<CEGUI::Event::Connection> mConnections;
    //! The selected job (a WorkerJob value) in mode Priority list, -1 if none
    int32_t mSelectedJob = -1;
    //! The selected carry entry (a WorkerCarryEntry value), -1 if none
    int32_t mSelectedCarry = -1;
    //! The job (a WorkerJob value) of the tablet a drag started on, -1 if none
    int32_t mDragTablet = -1;
    //! The carry entry (a WorkerCarryEntry value) a drag started on, -1 if none
    int32_t mDragCarry = -1;
    //! Positions of the tablets and of the carry entries as the layout gives them
    std::vector<CEGUI::UVector2> mTabletBases;
    std::vector<CEGUI::UVector2> mCarryBases;
    //! Running slides of the tablets and of the carry entries
    std::vector<Slide> mTabletSlides;
    std::vector<Slide> mCarrySlides;
    //! The entries per place as drawn last, empty before the first drawing after opening
    std::vector<uint32_t> mShownTabletOrder;
    std::vector<uint32_t> mShownCarryOrder;
    //! What was drawn last, empty if the window has to be drawn
    std::vector<uint32_t> mShownState;
};

#endif // WORKERSWINDOW_H
