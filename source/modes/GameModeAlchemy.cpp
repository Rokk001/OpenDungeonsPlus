#include "modes/GameMode.h"
#include "entities/PotionDefinition.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "network/ClientNotification.h"
#include "network/ODClient.h"
#include "rooms/RoomType.h"
#include "utils/Helper.h"
#include <CEGUI/Window.h>
#include <CEGUI/widgets/ListboxTextItem.h>
#include <CEGUI/widgets/MultiColumnList.h>
#include <cmath>
#include <sstream>

//! \brief Requests owner-seat data and opens the laboratory overview when a lab exists.
void GameMode::showAlchemyLabWindow()
{
    Player* player = mGameMap->getLocalPlayer();
    if(!isConnected() || player == nullptr || player->getSeat() == nullptr ||
       player->getSeat()->getNbRooms(RoomType::alchemyLab) == 0)
        return;
    mRootWindow->getChild("AlchemyLabWindow")->show();
    setLabModeShown(player->getSeat()->getLabMode());
    ClientNotification* request = new ClientNotification(ClientNotificationType::askLabWindow);
    request->mPacket << true;
    ODClient::getSingleton().queueClientNotification(request);
}

//! \brief Toggles the laboratory window from the minimap control and the L key.
bool GameMode::toggleAlchemyLabWindow(const CEGUI::EventArgs& event)
{
    if(mRootWindow->getChild("AlchemyLabWindow")->isVisible())
        return hideAlchemyLabWindow(event);
    showAlchemyLabWindow();
    return true;
}

//! \brief Closes the overview and stops server snapshots for this player.
bool GameMode::hideAlchemyLabWindow(const CEGUI::EventArgs&)
{
    mRootWindow->getChild("AlchemyLabWindow")->hide();
    if(isConnected())
    {
        ClientNotification* request = new ClientNotification(ClientNotificationType::askLabWindow);
        request->mPacket << false;
        ODClient::getSingleton().queueClientNotification(request);
    }
    return true;
}

//! \brief Requests the next of the three approved brewing modes.
bool GameMode::cycleLabMode(const CEGUI::EventArgs&)
{
    Player* player = mGameMap->getLocalPlayer();
    if(!isConnected() || player == nullptr || player->getSeat() == nullptr)
        return true;
    ClientNotification* request = new ClientNotification(ClientNotificationType::askLabSetting);
    request->mPacket << static_cast<int32_t>((player->getSeat()->getLabMode()+1)%3);
    ODClient::getSingleton().queueClientNotification(request);
    return true;
}

//! \brief Adopts the validated server setting and displays its approved label.
void GameMode::setLabModeShown(int32_t mode)
{
    if(mode < 0 || mode > 2)
        return;
    Player* player = mGameMap->getLocalPlayer();
    if(player != nullptr && player->getSeat() != nullptr)
        player->getSeat()->setLabMode(mode);
    static const char* const labels[] = {"Automatic", "Healing and mana", "Combat potions"};
    mRootWindow->getChild("AlchemyLabWindow/ModeButton")->setText(labels[mode]);
}

//! \brief Replaces cauldron rows and herb totals with one coherent owner-seat snapshot.
void GameMode::setLabWindowData(const LabWindowData& data)
{
    CEGUI::MultiColumnList* list = static_cast<CEGUI::MultiColumnList*>(
        mRootWindow->getChild("AlchemyLabWindow/CauldronList"));
    if(list->getColumnCount() == 0)
    {
        list->addColumn("Cauldron", 0, CEGUI::UDim(0.17f, 0));
        list->addColumn("Potion", 1, CEGUI::UDim(0.36f, 0));
        list->addColumn("Brewer", 2, CEGUI::UDim(0.29f, 0));
        list->addColumn("Remaining s", 3, CEGUI::UDim(0.18f, 0));
        list->setUserSortControlEnabled(false);
    }
    list->resetList();
    for(std::size_t index = 0; index < data.mCauldrons.size(); ++index)
    {
        const LabCauldronRow& cauldron = data.mCauldrons[index];
        const uint32_t row = list->addRow();
        list->setItem(new CEGUI::ListboxTextItem(Helper::toString(index+1)), 0, row);
        list->setItem(new CEGUI::ListboxTextItem(cauldron.mPotion), 1, row);
        list->setItem(new CEGUI::ListboxTextItem(cauldron.mBrewer), 2, row);
        list->setItem(new CEGUI::ListboxTextItem(Helper::toString(static_cast<uint32_t>(std::ceil(cauldron.mRemaining)))), 3, row);
    }
    std::ostringstream stock;
    bool first = true;
    for(const HerbDefinition& herb : ConfigManager::getSingleton().getHerbs())
    {
        if(!first)
            stock << ", ";
        first = false;
        std::map<std::string, uint32_t>::const_iterator amount = data.mHerbs.find(herb.mId);
        stock << herb.mDisplay << " " << (amount == data.mHerbs.end() ? 0 : amount->second);
    }
    mRootWindow->getChild("AlchemyLabWindow/HerbStock")->setText(stock.str());
    setLabModeShown(data.mMode);
}
