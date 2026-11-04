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

#include "render/WorkersWindow.h"

#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "network/ODClient.h"
#include "utils/ConfigManager.h"
#include "utils/LogManager.h"

#include <CEGUI/CEGUI.h>
#include <CEGUI/WindowManager.h>
#include <CEGUI/widgets/FrameWindow.h>
#include <CEGUI/widgets/PushButton.h>

#include <algorithm>
#include <string>

namespace
{
//! Names of the jobs in the order of WorkerJob
const char* const JOB_NAMES[WorkersWindow::JOB_COUNT] = {"Dig", "Claim ground", "Claim wall", "Carry", "Clean", "Reload"};
//! Painted pictures of the jobs in the order of WorkerJob
const char* const JOB_IMAGES[WorkersWindow::JOB_COUNT] = {"OpenDungeonsIcons/WorkerJobDig",
    "OpenDungeonsIcons/WorkerJobClaimGround", "OpenDungeonsIcons/WorkerJobClaimWall", "OpenDungeonsIcons/WorkerJobCarry",
    "OpenDungeonsIcons/WorkerJobClean", "OpenDungeonsIcons/WorkerJobReload"};
//! Roman numerals of the ranks
const char* const RANK_NUMERALS[WorkersWindow::JOB_COUNT] = {"I", "II", "III", "IV", "V", "VI"};
//! Names of the carry entries in the order of WorkerCarryEntry
const char* const CARRY_NAMES[WorkersWindow::CARRY_COUNT] = {"Own knocked out", "Enemy knocked out", "Corpses", "Gold",
    "Items", "Gift boxes", "Traps and doors"};
//! Painted pictures of the carry entries in the order of WorkerCarryEntry
const char* const CARRY_IMAGES[WorkersWindow::CARRY_COUNT] = {"OpenDungeonsIcons/WorkerCarryOwn",
    "OpenDungeonsIcons/WorkerCarryEnemy", "OpenDungeonsIcons/WorkerCarryCorpses", "OpenDungeonsIcons/WorkerCarryGold",
    "OpenDungeonsIcons/WorkerCarryItems", "OpenDungeonsIcons/WorkerCarryGift", "OpenDungeonsIcons/WorkerCarryTrapsDoors"};
//! Colour of the lit texts
const char* const COLOUR_LIT = "FFF2C860";
//! Colour of the normal texts
const char* const COLOUR_NORMAL = "FFE8DCC0";
}

//! \brief Finds the window and the HUD button, hides both and connects all events of the window.
WorkersWindow::WorkersWindow(CEGUI::Window* rootWindow, GameMap& gameMap) :
    mGameMap(gameMap),
    mWindow(rootWindow->getChild("WorkersWindow")),
    mButton(rootWindow->getChild("WorkersButton"))
{
    mWindow->hide();
    mButton->hide();

    mConnections.push_back(mWindow->subscribeEvent(CEGUI::FrameWindow::EventCloseClicked,
        CEGUI::Event::Subscriber(&WorkersWindow::onCloseClicked, this)));
    mConnections.push_back(mButton->subscribeEvent(CEGUI::PushButton::EventClicked,
        CEGUI::Event::Subscriber(&WorkersWindow::onButtonClicked, this)));
    mConnections.push_back(mWindow->getChild("ModeAutomatic")->subscribeEvent(CEGUI::PushButton::EventClicked,
        CEGUI::Event::Subscriber(&WorkersWindow::onModeClicked, this)));
    mConnections.push_back(mWindow->getChild("ModePriority")->subscribeEvent(CEGUI::PushButton::EventClicked,
        CEGUI::Event::Subscriber(&WorkersWindow::onModeClicked, this)));
    mConnections.push_back(mWindow->getChild("PriorityUp")->subscribeEvent(CEGUI::PushButton::EventClicked,
        CEGUI::Event::Subscriber(&WorkersWindow::onPriorityArrowClicked, this)));
    mConnections.push_back(mWindow->getChild("PriorityDown")->subscribeEvent(CEGUI::PushButton::EventClicked,
        CEGUI::Event::Subscriber(&WorkersWindow::onPriorityArrowClicked, this)));
    mConnections.push_back(mWindow->getChild("CarryUp")->subscribeEvent(CEGUI::PushButton::EventClicked,
        CEGUI::Event::Subscriber(&WorkersWindow::onCarryArrowClicked, this)));
    mConnections.push_back(mWindow->getChild("CarryDown")->subscribeEvent(CEGUI::PushButton::EventClicked,
        CEGUI::Event::Subscriber(&WorkersWindow::onCarryArrowClicked, this)));
    mConnections.push_back(mWindow->getChild("GoldCheck")->subscribeEvent(CEGUI::PushButton::EventClicked,
        CEGUI::Event::Subscriber(&WorkersWindow::onGoldFirstClicked, this)));

    for(std::size_t i = 0; i < JOB_COUNT; ++i)
    {
        const std::string rank = "Rank" + std::to_string(i);
        CEGUI::Window* tablet = mWindow->getChild(rank);
        tablet->setID(static_cast<unsigned int>(i));
        mWindow->getChild(rank + "/Minus")->setID(static_cast<unsigned int>(i));
        mWindow->getChild(rank + "/Plus")->setID(static_cast<unsigned int>(i));
        mConnections.push_back(tablet->subscribeEvent(CEGUI::Window::EventMouseButtonDown,
            CEGUI::Event::Subscriber(&WorkersWindow::onTabletPressed, this)));
        mConnections.push_back(tablet->subscribeEvent(CEGUI::Window::EventMouseButtonUp,
            CEGUI::Event::Subscriber(&WorkersWindow::onTabletReleased, this)));
        mConnections.push_back(mWindow->getChild(rank + "/Minus")->subscribeEvent(CEGUI::PushButton::EventClicked,
            CEGUI::Event::Subscriber(&WorkersWindow::onFixedClicked, this)));
        mConnections.push_back(mWindow->getChild(rank + "/Plus")->subscribeEvent(CEGUI::PushButton::EventClicked,
            CEGUI::Event::Subscriber(&WorkersWindow::onFixedClicked, this)));
    }
    for(std::size_t i = 0; i < CARRY_COUNT; ++i)
    {
        const std::string entry = "Carry" + std::to_string(i);
        CEGUI::Window* frame = mWindow->getChild(entry);
        frame->setID(static_cast<unsigned int>(i));
        mConnections.push_back(frame->subscribeEvent(CEGUI::Window::EventMouseButtonDown,
            CEGUI::Event::Subscriber(&WorkersWindow::onCarryPressed, this)));
        mConnections.push_back(frame->subscribeEvent(CEGUI::Window::EventMouseButtonUp,
            CEGUI::Event::Subscriber(&WorkersWindow::onCarryReleased, this)));
    }
}

//! \brief Disconnects every event.
WorkersWindow::~WorkersWindow()
{
    for(CEGUI::Event::Connection& connection : mConnections)
        connection->disconnect();
}

//! \brief Names the local keeper's seat, nullptr when the client has no keeper seat.
Seat* WorkersWindow::getSeat() const
{
    Player* player = mGameMap.getLocalPlayer();
    if(player == nullptr)
        return nullptr;
    return player->getSeat();
}

//! \brief Opens the window on top of the others; a client without a keeper seat gets nothing.
void WorkersWindow::show()
{
    if(getSeat() == nullptr)
        return;
    mSelectedJob = -1;
    mSelectedCarry = -1;
    mDragTablet = -1;
    mDragCarry = -1;
    mShownState.clear();
    mWindow->show();
    mWindow->moveToFront();
    refresh();
}

//! \brief Closes the window and forgets selection and drag.
void WorkersWindow::hide()
{
    mSelectedJob = -1;
    mSelectedCarry = -1;
    mDragTablet = -1;
    mDragCarry = -1;
    mWindow->hide();
}

//! \brief True while the window is open.
bool WorkersWindow::isVisible() const
{
    return mWindow->isVisible();
}

//! \brief Key J and the HUD button: opens the closed window and closes the open one.
void WorkersWindow::toggle()
{
    if(isVisible())
        hide();
    else
        show();
}

//! \brief Frame update: the HUD button belongs to a keeper only, the open window follows the stored settings.
void WorkersWindow::update()
{
    const bool keeper = (getSeat() != nullptr);
    if(mButton->isVisible() != keeper)
        mButton->setVisible(keeper);
    if(!keeper)
    {
        if(isVisible())
            hide();
        return;
    }
    if(isVisible())
        refresh();
}

//! \brief Close button and Esc; handled so that Esc closes only this window.
bool WorkersWindow::onCloseClicked(const CEGUI::EventArgs&)
{
    hide();
    return true;
}

//! \brief HUD button.
bool WorkersWindow::onButtonClicked(const CEGUI::EventArgs&)
{
    toggle();
    return true;
}

//! \brief Mode selector: sends the settings with the other mode; the selection of a tablet is cleared.
bool WorkersWindow::onModeClicked(const CEGUI::EventArgs& e)
{
    Seat* seat = getSeat();
    if(seat == nullptr)
        return true;
    const CEGUI::WindowEventArgs& args = static_cast<const CEGUI::WindowEventArgs&>(e);
    WorkerJobSettings next = seat->getWorkerJobSettings();
    const uint32_t mode = (args.window->getName() == "ModePriority") ? static_cast<uint32_t>(WorkerFreeMode::priority) :
        static_cast<uint32_t>(WorkerFreeMode::automatic);
    mSelectedJob = -1;
    if(next.freeMode == mode)
        return true;
    next.freeMode = mode;
    sendSettings(next);
    return true;
}

//! \brief The window id of the window that fired an event, which is the slot index set at construction.
int32_t WorkersWindow::getSlotId(const CEGUI::EventArgs& e)
{
    const CEGUI::WindowEventArgs& args = static_cast<const CEGUI::WindowEventArgs&>(e);
    if(args.window == nullptr)
        return -1;
    return static_cast<int32_t>(args.window->getID());
}

//! \brief Left button on a tablet: selects the job and remembers it for a drag; only in mode Priority list.
bool WorkersWindow::onTabletPressed(const CEGUI::EventArgs& e)
{
    const CEGUI::MouseEventArgs& mouse = static_cast<const CEGUI::MouseEventArgs&>(e);
    Seat* seat = getSeat();
    const int32_t rank = getSlotId(e);
    if(seat == nullptr || mouse.button != CEGUI::LeftButton || rank < 0 || rank >= static_cast<int32_t>(JOB_COUNT))
        return true;
    const WorkerJobSettings& settings = seat->getWorkerJobSettings();
    if(settings.freeMode != static_cast<uint32_t>(WorkerFreeMode::priority))
        return true;
    mSelectedJob = static_cast<int32_t>(settings.priority[static_cast<std::size_t>(rank)]);
    mDragTablet = mSelectedJob;
    return true;
}

//! \brief Left button released after a tablet press: the dragged job takes the place of the tablet under the pointer.
bool WorkersWindow::onTabletReleased(const CEGUI::EventArgs& e)
{
    const CEGUI::MouseEventArgs& mouse = static_cast<const CEGUI::MouseEventArgs&>(e);
    const int32_t dragged = mDragTablet;
    mDragTablet = -1;
    Seat* seat = getSeat();
    if(seat == nullptr || mouse.button != CEGUI::LeftButton || dragged < 0)
        return true;
    WorkerJobSettings next = seat->getWorkerJobSettings();
    if(next.freeMode != static_cast<uint32_t>(WorkerFreeMode::priority))
        return true;
    const int32_t target = findSlotAt("Rank", JOB_COUNT, mouse.position.d_x, mouse.position.d_y);
    if(target < 0)
        return true;
    const std::array<uint32_t, JOB_COUNT>::iterator from = std::find(next.priority.begin(), next.priority.end(),
        static_cast<uint32_t>(dragged));
    if(from == next.priority.end())
        return true;
    if(moveOrderEntry(next.priority, static_cast<std::size_t>(from - next.priority.begin()), static_cast<std::size_t>(target)))
        sendSettings(next);
    return true;
}

//! \brief Up and down arrow of the priority: moves the selected tablet one rank higher or lower.
bool WorkersWindow::onPriorityArrowClicked(const CEGUI::EventArgs& e)
{
    Seat* seat = getSeat();
    if(seat == nullptr || mSelectedJob < 0)
        return true;
    WorkerJobSettings next = seat->getWorkerJobSettings();
    if(next.freeMode != static_cast<uint32_t>(WorkerFreeMode::priority))
        return true;
    const CEGUI::WindowEventArgs& args = static_cast<const CEGUI::WindowEventArgs&>(e);
    const bool up = (args.window->getName() == "PriorityUp");
    const std::array<uint32_t, JOB_COUNT>::iterator from = std::find(next.priority.begin(), next.priority.end(),
        static_cast<uint32_t>(mSelectedJob));
    if(from == next.priority.end())
        return true;
    const std::size_t place = static_cast<std::size_t>(from - next.priority.begin());
    if(up && place == 0)
        return true;
    if(!up && place + 1 >= JOB_COUNT)
        return true;
    if(moveOrderEntry(next.priority, place, up ? place - 1 : place + 1))
        sendSettings(next);
    return true;
}

//! \brief "-" and "+" of a tablet: changes the fixed number of that job by one; "+" needs a free worker.
bool WorkersWindow::onFixedClicked(const CEGUI::EventArgs& e)
{
    Seat* seat = getSeat();
    const int32_t rank = getSlotId(e);
    if(seat == nullptr || rank < 0 || rank >= static_cast<int32_t>(JOB_COUNT))
        return true;
    const CEGUI::WindowEventArgs& args = static_cast<const CEGUI::WindowEventArgs&>(e);
    WorkerJobSettings next = seat->getWorkerJobSettings();
    const std::array<uint32_t, JOB_COUNT> order = getDisplayOrder(next, ConfigManager::getSingleton().getDefaultWorkerJobSettings());
    const uint32_t job = order[static_cast<std::size_t>(rank)];
    if(args.window->getName() == "Plus")
    {
        if(seat->getFreeWorkers() == 0)
            return true;
        ++next.fixed[job];
    }
    else
    {
        if(next.fixed[job] == 0)
            return true;
        --next.fixed[job];
    }
    sendSettings(next);
    return true;
}

//! \brief Left button on a carry entry: selects it and remembers it for a drag.
bool WorkersWindow::onCarryPressed(const CEGUI::EventArgs& e)
{
    const CEGUI::MouseEventArgs& mouse = static_cast<const CEGUI::MouseEventArgs&>(e);
    Seat* seat = getSeat();
    const int32_t place = getSlotId(e);
    if(seat == nullptr || mouse.button != CEGUI::LeftButton || place < 0 || place >= static_cast<int32_t>(CARRY_COUNT))
        return true;
    mSelectedCarry = static_cast<int32_t>(seat->getWorkerJobSettings().carryOrder[static_cast<std::size_t>(place)]);
    mDragCarry = mSelectedCarry;
    return true;
}

//! \brief Left button released after a carry entry press: the dragged entry takes the place under the pointer.
bool WorkersWindow::onCarryReleased(const CEGUI::EventArgs& e)
{
    const CEGUI::MouseEventArgs& mouse = static_cast<const CEGUI::MouseEventArgs&>(e);
    const int32_t dragged = mDragCarry;
    mDragCarry = -1;
    Seat* seat = getSeat();
    if(seat == nullptr || mouse.button != CEGUI::LeftButton || dragged < 0)
        return true;
    const int32_t target = findSlotAt("Carry", CARRY_COUNT, mouse.position.d_x, mouse.position.d_y);
    if(target < 0)
        return true;
    WorkerJobSettings next = seat->getWorkerJobSettings();
    const std::array<uint32_t, CARRY_COUNT>::iterator from = std::find(next.carryOrder.begin(), next.carryOrder.end(),
        static_cast<uint32_t>(dragged));
    if(from == next.carryOrder.end())
        return true;
    if(moveOrderEntry(next.carryOrder, static_cast<std::size_t>(from - next.carryOrder.begin()), static_cast<std::size_t>(target)))
        sendSettings(next);
    return true;
}

//! \brief Up and down arrow of the carry order: moves the selected entry one place to the left or right.
bool WorkersWindow::onCarryArrowClicked(const CEGUI::EventArgs& e)
{
    Seat* seat = getSeat();
    if(seat == nullptr || mSelectedCarry < 0)
        return true;
    WorkerJobSettings next = seat->getWorkerJobSettings();
    const CEGUI::WindowEventArgs& args = static_cast<const CEGUI::WindowEventArgs&>(e);
    const bool up = (args.window->getName() == "CarryUp");
    const std::array<uint32_t, CARRY_COUNT>::iterator from = std::find(next.carryOrder.begin(), next.carryOrder.end(),
        static_cast<uint32_t>(mSelectedCarry));
    if(from == next.carryOrder.end())
        return true;
    const std::size_t place = static_cast<std::size_t>(from - next.carryOrder.begin());
    if(up && place == 0)
        return true;
    if(!up && place + 1 >= CARRY_COUNT)
        return true;
    if(moveOrderEntry(next.carryOrder, place, up ? place - 1 : place + 1))
        sendSettings(next);
    return true;
}

//! \brief The tick box of "Gold first": switches it.
bool WorkersWindow::onGoldFirstClicked(const CEGUI::EventArgs&)
{
    Seat* seat = getSeat();
    if(seat == nullptr)
        return true;
    WorkerJobSettings next = seat->getWorkerJobSettings();
    next.goldFirst = (next.goldFirst == 0) ? 1 : 0;
    sendSettings(next);
    return true;
}

//! \brief Sends the proposed settings; the server stores them if valid and answers with the stored ones.
void WorkersWindow::sendSettings(const WorkerJobSettings& settings)
{
    if(!validWorkerJobSettings(settings))
    {
        OD_LOG_ERR("Invalid worker settings not sent");
        return;
    }
    ODClient::getSingleton().sendWorkerJobSettings(settings);
}

//! \brief Index of the slot named prefix + index whose area contains the point, -1 if none.
int32_t WorkersWindow::findSlotAt(const char* prefix, std::size_t count, float x, float y) const
{
    const CEGUI::Vector2f point(x, y);
    for(std::size_t i = 0; i < count; ++i)
    {
        CEGUI::Window* slot = mWindow->getChild(std::string(prefix) + std::to_string(i));
        if(slot->getUnclippedOuterRect().get().isPointInRect(point))
            return static_cast<int32_t>(i);
    }
    return -1;
}

//! \brief Greyed arrows show the disabled picture and do not react; enabled arrows show the normal, hover and pressed ones.
void WorkersWindow::setArrowEnabled(CEGUI::Window* arrow, bool up, bool enabled)
{
    const std::string direction = up ? "Up" : "Down";
    const std::string prefix = "OpenDungeonsIcons/WorkerArrow" + direction;
    arrow->setEnabled(enabled);
    arrow->setProperty("NormalImage", prefix + (enabled ? "Normal" : "Disabled"));
    arrow->setProperty("HoverImage", prefix + (enabled ? "Hover" : "Disabled"));
    arrow->setProperty("PushedImage", prefix + (enabled ? "Pressed" : "Disabled"));
}

//! \brief Tablet order: own list in mode Priority list, the predefined priority of the game in mode Automatic.
std::array<uint32_t, WorkersWindow::JOB_COUNT> WorkersWindow::getDisplayOrder(const WorkerJobSettings& settings,
    const WorkerJobSettings& defaults)
{
    if(settings.freeMode == static_cast<uint32_t>(WorkerFreeMode::priority))
        return settings.priority;
    return defaults.priority;
}

//! \brief Roman numeral of a rank.
const char* WorkersWindow::getRankNumeral(std::size_t rank)
{
    return rank < JOB_COUNT ? RANK_NUMERALS[rank] : "";
}

//! \brief Name of a job.
const char* WorkersWindow::getJobName(uint32_t job)
{
    return job < JOB_COUNT ? JOB_NAMES[job] : "";
}

//! \brief Name of a carry entry.
const char* WorkersWindow::getCarryName(uint32_t entry)
{
    return entry < CARRY_COUNT ? CARRY_NAMES[entry] : "";
}

//! \brief Everything the window shows, in one list.
std::vector<uint32_t> WorkersWindow::getShownState() const
{
    std::vector<uint32_t> state;
    Seat* seat = getSeat();
    if(seat == nullptr)
        return state;
    const WorkerJobSettings& settings = seat->getWorkerJobSettings();
    const WorkerJobSettings& defaults = ConfigManager::getSingleton().getDefaultWorkerJobSettings();
    state.push_back(settings.freeMode);
    state.push_back(settings.goldFirst);
    state.push_back(seat->getFreeWorkers());
    state.insert(state.end(), settings.fixed.begin(), settings.fixed.end());
    state.insert(state.end(), settings.priority.begin(), settings.priority.end());
    state.insert(state.end(), settings.carryOrder.begin(), settings.carryOrder.end());
    state.insert(state.end(), defaults.priority.begin(), defaults.priority.end());
    const std::array<uint32_t, JOB_COUNT>& counts = seat->getWorkerJobCounts();
    state.insert(state.end(), counts.begin(), counts.end());
    state.push_back(static_cast<uint32_t>(mSelectedJob + 1));
    state.push_back(static_cast<uint32_t>(mSelectedCarry + 1));
    return state;
}

//! \brief Redraws the free workers, the mode, the tablets, the carry entries and the tick box from the stored data.
void WorkersWindow::refresh()
{
    Seat* seat = getSeat();
    if(seat == nullptr)
        return;
    const WorkerJobSettings& settings = seat->getWorkerJobSettings();
    if(settings.freeMode != static_cast<uint32_t>(WorkerFreeMode::priority))
        mSelectedJob = -1;
    const std::vector<uint32_t> state = getShownState();
    if(state == mShownState)
        return;
    mShownState = state;

    const WorkerJobSettings& defaults = ConfigManager::getSingleton().getDefaultWorkerJobSettings();
    const bool priorityMode = (settings.freeMode == static_cast<uint32_t>(WorkerFreeMode::priority));
    const uint32_t freeWorkers = seat->getFreeWorkers();
    const std::array<uint32_t, JOB_COUNT>& counts = seat->getWorkerJobCounts();

    mWindow->getChild("FreeCount")->setText(std::to_string(freeWorkers));

    // Mode selector: the active mode is lit
    for(int32_t mode = 0; mode < 2; ++mode)
    {
        const bool active = (static_cast<uint32_t>(mode) == settings.freeMode);
        CEGUI::Window* button = mWindow->getChild(mode == 0 ? "ModeAutomatic" : "ModePriority");
        button->getChild("Hand")->setProperty("Image", active ? "OpenDungeonsIcons/WorkerHandActive" :
            "OpenDungeonsIcons/WorkerHandInactive");
        button->getChild("Label")->setProperty("TextColours", active ? COLOUR_LIT : COLOUR_NORMAL);
    }

    // Tablets in rank order
    const std::array<uint32_t, JOB_COUNT> order = getDisplayOrder(settings, defaults);
    for(std::size_t rank = 0; rank < JOB_COUNT; ++rank)
    {
        const uint32_t job = order[rank];
        CEGUI::Window* tablet = mWindow->getChild("Rank" + std::to_string(rank));
        const bool selected = (priorityMode && mSelectedJob == static_cast<int32_t>(job));
        tablet->getChild("Frame")->setProperty("Image", selected ? "OpenDungeonsIcons/WorkerTabletSelected" :
            "OpenDungeonsIcons/WorkerTabletNormal");
        tablet->getChild("Numeral")->setText(RANK_NUMERALS[rank]);
        tablet->getChild("Figure")->setProperty("Image", JOB_IMAGES[job]);
        tablet->getChild("Name")->setText(JOB_NAMES[job]);
        tablet->getChild("Count")->setText(std::to_string(settings.fixed[job]));
        tablet->getChild("Minus")->setEnabled(settings.fixed[job] > 0);
        tablet->getChild("Plus")->setEnabled(freeWorkers > 0);
        mWindow->getChild("Working" + std::to_string(rank))->setText("Working: " + std::to_string(counts[job]));
    }

    // Priority arrows and hint: only in mode Priority list, and only where the selected tablet can move
    std::size_t selectedPlace = JOB_COUNT;
    if(priorityMode && mSelectedJob >= 0)
    {
        for(std::size_t place = 0; place < JOB_COUNT; ++place)
        {
            if(settings.priority[place] == static_cast<uint32_t>(mSelectedJob))
                selectedPlace = place;
        }
    }
    setArrowEnabled(mWindow->getChild("PriorityUp"), true, selectedPlace < JOB_COUNT && selectedPlace > 0);
    setArrowEnabled(mWindow->getChild("PriorityDown"), false, selectedPlace < JOB_COUNT && selectedPlace + 1 < JOB_COUNT);
    mWindow->getChild("DragHint")->setProperty("TextColours", priorityMode ? COLOUR_NORMAL : "FF7A6F5E");
    mWindow->getChild("DragHand")->setAlpha(priorityMode ? 1.0f : 0.4f);
    mWindow->getChild("PriorityLabel")->setProperty("TextColours", priorityMode ? COLOUR_LIT : "FF7A6F5E");

    // Carry order
    std::size_t carryPlace = CARRY_COUNT;
    for(std::size_t place = 0; place < CARRY_COUNT; ++place)
    {
        const uint32_t entry = settings.carryOrder[place];
        CEGUI::Window* frame = mWindow->getChild("Carry" + std::to_string(place));
        frame->getChild("Frame")->setProperty("Image", mSelectedCarry == static_cast<int32_t>(entry) ?
            "OpenDungeonsIcons/WorkerCarryFrameSelected" : "OpenDungeonsIcons/WorkerCarryFrameNormal");
        frame->getChild("Number")->setText(std::to_string(place + 1));
        frame->getChild("Picture")->setProperty("Image", CARRY_IMAGES[entry]);
        frame->getChild("Name")->setText(CARRY_NAMES[entry]);
        if(mSelectedCarry == static_cast<int32_t>(entry))
            carryPlace = place;
    }
    setArrowEnabled(mWindow->getChild("CarryUp"), true, carryPlace < CARRY_COUNT && carryPlace > 0);
    setArrowEnabled(mWindow->getChild("CarryDown"), false, carryPlace < CARRY_COUNT && carryPlace + 1 < CARRY_COUNT);

    // Gold first
    CEGUI::Window* check = mWindow->getChild("GoldCheck");
    const char* checkImage = (settings.goldFirst != 0) ? "OpenDungeonsIcons/WorkerCheckboxChecked" :
        "OpenDungeonsIcons/WorkerCheckboxEmpty";
    check->setProperty("NormalImage", checkImage);
    check->setProperty("HoverImage", checkImage);
    check->setProperty("PushedImage", checkImage);
}
