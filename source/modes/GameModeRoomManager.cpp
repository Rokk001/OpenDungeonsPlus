#include "modes/GameMode.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "entities/Tile.h"
#include "rooms/Room.h"
#include "rooms/RoomManager.h"
#include "rooms/RoomManagerStatus.h"
#include "utils/Helper.h"

#include <CEGUI/CEGUI.h>
#include <CEGUI/widgets/PushButton.h>

namespace
{
const char* const PAGE_NAMES[] = {"GhostPage", "MerchantPage", "TavernPage", "SpaPage",
    "InfirmaryPage", "AlchemyPage", "CasinoPage", "WorkshopPage"};
const char* const ROOM_ICONS[] = {"GhostRoomButton", "MerchantButton", "TavernButton", "SpaButton",
    "InfirmaryButton", "AlchemyLabButton", "CasinoButton", "WorkshopButton"};
const TileVisual ROOM_VISUALS[] = {TileVisual::ghostRoom, TileVisual::merchantRoom, TileVisual::tavernRoom,
    TileVisual::spaRoom, TileVisual::infirmaryRoom, TileVisual::alchemyLabRoom,
    TileVisual::casinoRoom, TileVisual::workshopRoom};

//! \brief Sets the colour and visibility of a room indicator without sending notifications.
void showRoomDot(CEGUI::Window* window, RoomManagerDot dot)
{
    window->setVisible(dot != RoomManagerDot::none);
    const char* colour = dot == RoomManagerDot::red ? "FFFF4040" :
        dot == RoomManagerDot::yellow ? "FFFFD040" : "FF50D050";
    window->setProperty("TextColours", colour);
}
}

//! \brief Connects the shared management frame and each selectable room row.
void GameMode::initializeRoomManager()
{
    addEventConnection(mRootWindow->getChild("RoomManagerButton")->subscribeEvent(
        CEGUI::PushButton::EventClicked, CEGUI::Event::Subscriber(&GameMode::toggleRoomManager, this)));
    addEventConnection(mRootWindow->getChild("RoomManagerWindow")->subscribeEvent(
        CEGUI::FrameWindow::EventCloseClicked, CEGUI::Event::Subscriber(&GameMode::closeRoomManager, this)));
    addEventConnection(mRootWindow->getChild("RoomManagerWindow")->subscribeEvent(
        CEGUI::Window::EventHidden, CEGUI::Event::Subscriber(&GameMode::closeRoomManager, this)));
    for(std::size_t index = 0; index < RoomManagerNavigation::order().size(); ++index)
    {
        CEGUI::Window* button = mRootWindow->getChild("RoomManagerWindow/Rows/Row" +
            Helper::toString(index) + "/Button");
        button->setID(static_cast<uint32_t>(index));
        addEventConnection(button->subscribeEvent(CEGUI::Window::EventMouseClick,
            CEGUI::Event::Subscriber(&GameMode::selectRoomManagerRow, this)));
    }
}

//! \brief Refreshes the owned list and repairs selection when the last room of a type is lost.
void GameMode::refreshRoomManager()
{
    Player* player = mGameMap->getLocalPlayer();
    Seat* seat = player == nullptr ? nullptr : player->getSeat();
    std::array<uint32_t, 8> counts = {{0, 0, 0, 0, 0, 0, 0, 0}};
    std::array<RoomManagerEntry, 8> entries = emptyRoomManagerEntries();
    if(seat != nullptr)
    {
        entries = seat->getRoomManagerEntries();
        for(std::size_t index = 0; index < counts.size(); ++index)
        {
            counts[index] = seat->getNbRooms(RoomManagerNavigation::order()[index]);
            entries[index].count = counts[index];
        }
    }
    mRoomManagerNavigation.updateOwned(counts);
    mRootWindow->getChild("RoomManagerButton")->setVisible(mRoomManagerNavigation.listedCount() > 0);
    showRoomDot(mRootWindow->getChild("RoomManagerButton/Dot"), roomManagerButtonDot(entries));
    CEGUI::Window* frame = mRootWindow->getChild("RoomManagerWindow");
    if(!mRoomManagerNavigation.isOpen())
    {
        closeRoomManager();
        return;
    }
    frame->getChild("RoomsLabel")->setText("Rooms (" + Helper::toString(mRoomManagerNavigation.listedCount()) + ")");
    std::size_t visibleRow = 0;
    for(std::size_t index = 0; index < counts.size(); ++index)
    {
        CEGUI::Window* row = frame->getChild("Rows/Row" + Helper::toString(index));
        row->setVisible(counts[index] > 0);
        if(counts[index] == 0)
            continue;
        row->setYPosition(CEGUI::UDim(0, static_cast<float>(visibleRow++) * row->getSize().d_height.d_offset));
        row->getChild("Name")->setText(RoomManager::getRoomReadableName(entries[index].type));
        row->getChild("Icon")->setProperty("Image", std::string("OpenDungeonsIcons/") + ROOM_ICONS[index]);
        row->getChild("Highlight")->setVisible(entries[index].type == mRoomManagerNavigation.selected());
        showRoomDot(row->getChild("Dot"), entries[index].dot);
    }
    // A keeper-wide setting must follow another owned room if its previous target tile is lost.
    int targetX = -1;
    int targetY = -1;
    TileVisual targetVisual = TileVisual::nullTileVisual;
    switch(mRoomManagerPageType)
    {
    case RoomType::tavern: targetX = mTavernX; targetY = mTavernY; targetVisual = TileVisual::tavernRoom; break;
    case RoomType::spa: targetX = mSpaX; targetY = mSpaY; targetVisual = TileVisual::spaRoom; break;
    case RoomType::casino: targetX = mCasinoX; targetY = mCasinoY; targetVisual = TileVisual::casinoRoom; break;
    default: break;
    }
    if(targetVisual != TileVisual::nullTileVisual)
    {
        Tile* target = mGameMap->getTile(targetX, targetY);
        if(target == nullptr || target->getSeat() != seat || target->getTileVisual() != targetVisual)
            mRoomManagerPageType = RoomType::nullRoomType;
    }
    if(mRoomManagerPageType != mRoomManagerNavigation.selected())
    {
        // Stop the old page subscriptions before requesting the newly selected type.
        hideMerchantWindow();
        hideInfirmaryWindow();
        hideAlchemyLabWindow(CEGUI::EventArgs());
        hideGhostRoomWindow();
        hideTavernWindow();
        hideSpaWindow();
        hideCasinoPayoutWindow();
        closeTrapProductionQueue();
        mRoomManagerPageType = mRoomManagerNavigation.selected();
        Tile* tile = nullptr;
        std::size_t selectedIndex = 0;
        while(RoomManagerNavigation::order()[selectedIndex] != mRoomManagerPageType)
            ++selectedIndex;
        // Client tiles carry visuals; authoritative Room objects exist only on the server.
        for(int y = 0; tile == nullptr && y < mGameMap->getMapSizeY(); ++y)
            for(int x = 0; tile == nullptr && x < mGameMap->getMapSizeX(); ++x)
            {
                Tile* candidate = mGameMap->getTile(x, y);
                if(candidate != nullptr && candidate->getSeat() == seat &&
                    candidate->getTileVisual() == ROOM_VISUALS[selectedIndex])
                    tile = candidate;
            }
        switch(mRoomManagerPageType)
        {
        case RoomType::ghostRoom: showGhostRoomWindow(tile); break;
        case RoomType::merchant: showMerchantPage(); break;
        case RoomType::infirmary: showInfirmaryWindow(); break;
        case RoomType::alchemyLab: showAlchemyLabWindow(); break;
        case RoomType::tavern: if(tile != nullptr) showTavernWindow(tile); break;
        case RoomType::spa: if(tile != nullptr) showSpaWindow(tile); break;
        case RoomType::casino: if(tile != nullptr) showCasinoPayoutWindow(tile); break;
        case RoomType::workshop: requestTrapProductionQueue(); break;
        default: break;
        }
    }
    for(std::size_t index = 0; index < counts.size(); ++index)
        frame->getChild(std::string("Pages/") + PAGE_NAMES[index])->setVisible(
            entries[index].type == mRoomManagerNavigation.selected());
    frame->show();
}

//! \brief Toggles the HUD frame, opening the first owned room after closing other windows.
bool GameMode::toggleRoomManager(const CEGUI::EventArgs&)
{
    refreshRoomManager();
    const bool wasOpen = mRoomManagerNavigation.isOpen();
    closeAllTopWindows();
    if(!wasOpen)
        mRoomManagerNavigation.openFirst();
    refreshRoomManager();
    mRootWindow->getChild("RoomManagerWindow")->moveToFront();
    return true;
}

//! \brief Handles owned shortcut targets while preserving the distinct keyboard/options close policy.
bool GameMode::selectRoomManagerType(RoomType type, bool closeOthers, bool toggle)
{
    refreshRoomManager();
    if(!mRoomManagerNavigation.owned(type))
        return true;
    const bool close = toggle && mRoomManagerNavigation.isOpen() && mRoomManagerNavigation.selected() == type;
    if(closeOthers)
        closeAllTopWindows();
    if(close)
        closeRoomManager();
    else
    {
        if(toggle && !closeOthers)
            mRoomManagerNavigation.toggleType(type);
        else
            mRoomManagerNavigation.selectType(type);
        refreshRoomManager();
        mRootWindow->getChild("RoomManagerWindow")->moveToFront();
    }
    return true;
}

//! \brief Selects the clicked row without toggling an already selected page closed.
bool GameMode::selectRoomManagerRow(const CEGUI::EventArgs& args)
{
    const CEGUI::WindowEventArgs& event = static_cast<const CEGUI::WindowEventArgs&>(args);
    if(event.window->getID() < RoomManagerNavigation::order().size())
        selectRoomManagerType(RoomManagerNavigation::order()[event.window->getID()], false, false);
    return true;
}

//! \brief Releases live page updates and closes the one management frame.
bool GameMode::closeRoomManager(const CEGUI::EventArgs&)
{
    mRoomManagerNavigation.close();
    if(mRoomManagerPageType != RoomType::nullRoomType)
    {
        mRoomManagerPageType = RoomType::nullRoomType;
        hideMerchantWindow();
        hideInfirmaryWindow();
        hideAlchemyLabWindow(CEGUI::EventArgs());
    }
    for(const char* page : PAGE_NAMES)
        mRootWindow->getChild(std::string("RoomManagerWindow/Pages/") + page)->hide();
    mRootWindow->getChild("RoomManagerWindow")->hide();
    return true;
}
