#include "modes/GameMode.h"

#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "modes/ModeManager.h"
#include "network/ClientNotification.h"
#include "network/ODClient.h"
#include "network/ODPacket.h"
#include "rooms/RoomType.h"
#include "social/SocialProfileCache.h"
#include "social/SocialGenerator.h"
#include "utils/Helper.h"
#include "utils/ConfigManager.h"

#include <CEGUI/CEGUI.h>
#include <CEGUI/ImageManager.h>
#include <CEGUI/widgets/MultiColumnList.h>
#include <CEGUI/widgets/ListboxTextItem.h>
#include <CEGUI/widgets/Slider.h>
#include <CEGUI/widgets/PushButton.h>
#include <CEGUI/widgets/Tooltip.h>
#include <CEGUI/widgets/Scrollbar.h>
#include <CEGUI/widgets/ListHeader.h>

#include <algorithm>
#include <cmath>
#include <sstream>

namespace
{
static const float ICON_DESIGN_SIZE = 76.0f;
// Design width of the stock list inside the Room Manager's right page, less its margins.
static const float STOCK_DESIGN_WIDTH = 485.12f;
static const float MARGIN_STEP = 5.0f;
//! \brief Locates a stock cell using the same clipped area, scroll offsets and header widths as CEGUI.
CEGUI::ListboxItem* merchantItemAtPointer(CEGUI::MultiColumnList* list, const CEGUI::Vector2f& position)
{
    const CEGUI::Vector2f point = CEGUI::CoordConverter::screenToWindow(*list, position);
    const CEGUI::Rectf area = list->getListRenderArea();
    if(!area.isPointInRect(point)) return nullptr;
    float top = area.top() - list->getVertScrollbar()->getScrollPosition();
    for(uint32_t row = 0; row < list->getRowCount(); ++row)
    {
        CEGUI::ListboxItem* first = list->getItemAtGridReference(CEGUI::MCLGridRef(row, 0));
        const float height = first == nullptr ? 0.0f : first->getPixelSize().d_height;
        if(point.d_y >= top && point.d_y < top + height)
        {
            float left = area.left() - list->getHorzScrollbar()->getScrollPosition();
            for(uint32_t column = 0; column < list->getColumnCount(); ++column)
            {
                const float width = CEGUI::CoordConverter::asAbsolute(list->getColumnHeaderWidth(column), list->getListHeader()->getPixelSize().d_width);
                if(point.d_x >= left && point.d_x < left + width)
                    return list->getItemAtGridReference(CEGUI::MCLGridRef(row, column));
                left += width;
            }
        }
        top += height;
    }
    return nullptr;
}

//! \brief Draws the actual item and its quality frame in the merchant's image column.
class MerchantImageItem : public CEGUI::ListboxTextItem
{
public:
    //! \brief Retains image names while the existing list owns the item and its tooltip.
    MerchantImageItem(const ItemInstance& item, uint32_t index) : CEGUI::ListboxTextItem("", index),
        mImage(index == 0 ? "" : "ItemImages/" + item.getImageName()), mFrame("OpenDungeonsIcons/ItemFrame" + qualityName(item.mQuality)) {}
    //! \brief Fits the 76-design-pixel slot height to the registered window's actual scale.
    CEGUI::Sizef getPixelSize() const override
    {
        const float scale = getOwnerWindow() == nullptr ? 1.0f : getOwnerWindow()->getPixelSize().d_width / STOCK_DESIGN_WIDTH;
        return CEGUI::Sizef(ICON_DESIGN_SIZE * scale, ICON_DESIGN_SIZE * scale);
    }
    //! \brief Overlays the quality frame on the icon while retaining the normal selection brush.
    void draw(CEGUI::GeometryBuffer& buffer, const CEGUI::Rectf& target, float alpha, const CEGUI::Rectf* clipper) const override
    {
        CEGUI::ListboxTextItem::draw(buffer, target, alpha, clipper);
        const float edge = std::min(target.getWidth(), getPixelSize().d_height);
        const CEGUI::Rectf area(target.left(), target.top(), target.left() + edge, target.top() + edge);
        CEGUI::ColourRect colours(0xFFFFFFFF);
        colours.setAlpha(alpha);
        if(CEGUI::ImageManager::getSingleton().isDefined(mImage))
            CEGUI::ImageManager::getSingleton().get(mImage).render(buffer, area, clipper, colours);
        if(CEGUI::ImageManager::getSingleton().isDefined(mFrame))
            CEGUI::ImageManager::getSingleton().get(mFrame).render(buffer, area, clipper, colours);
    }
private:
    //! \brief ItemImages entry for the actual quality or potion.
    std::string mImage;
    //! \brief Existing shared quality frame drawn over the item.
    std::string mFrame;
};

// History remains a transport field; the page displays only stock and settings.

}

//! \brief Sets up one stock list and the approved owner controls after the layout imports are registered.
void GameMode::initializeMerchantWindow()
{
    CEGUI::MultiColumnList* list = static_cast<CEGUI::MultiColumnList*>(mRootWindow->getChild("RoomManagerWindow/Pages/MerchantPage/StockList"));
    list->setSelectionMode(CEGUI::MultiColumnList::CellSingle);
    list->setUserSortControlEnabled(false);
    list->setShowHorzScrollbar(false);
    if(list->getColumnCount() == 0)
        for(uint32_t column = 0; column < 6; ++column)
            list->addColumn("", column, CEGUI::UDim(0.155f, 0));
    addEventConnection(list->subscribeEvent(CEGUI::Window::EventMouseClick,
        CEGUI::Event::Subscriber(&GameMode::confirmMerchantItem, this)));
    addEventConnection(list->subscribeEvent(CEGUI::Window::EventMouseMove,
        CEGUI::Event::Subscriber(&GameMode::hoverMerchantItem, this)));
    CEGUI::Slider* slider = static_cast<CEGUI::Slider*>(mRootWindow->getChild("RoomManagerWindow/Pages/MerchantPage/MarginSlider"));
    slider->setMaxValue(static_cast<float>(ConfigManager::getSingleton().getRoomConfigInt32("MerchantMarginMax")));
    slider->setClickStep(MARGIN_STEP);
    addEventConnection(slider->subscribeEvent(CEGUI::Slider::EventValueChanged,
        CEGUI::Event::Subscriber(&GameMode::changeMerchantMargin, this)));
    addEventConnection(mRootWindow->getChild("RoomManagerWindow/Pages/MerchantPage/ModeButton")->subscribeEvent(CEGUI::PushButton::EventClicked,
        CEGUI::Event::Subscriber(&GameMode::cycleMerchantMode, this)));
    addEventConnection(mRootWindow->getChild("RoomManagerWindow/Pages/MerchantPage/ProfitButton")->subscribeEvent(CEGUI::PushButton::EventClicked,
        CEGUI::Event::Subscriber(&GameMode::cycleMerchantMode, this)));
    addEventConnection(mRootWindow->getChild("RoomManagerWindow/Pages/MerchantPage/Confirmation/Cancel")->subscribeEvent(CEGUI::PushButton::EventClicked,
        CEGUI::Event::Subscriber(&GameMode::cancelMerchantItem, this)));
    addEventConnection(mRootWindow->getChild("RoomManagerWindow/Pages/MerchantPage/Confirmation/OK")->subscribeEvent(CEGUI::PushButton::EventClicked,
        CEGUI::Event::Subscriber(&GameMode::buyMerchantItem, this)));
    mRootWindow->getChild("RoomManagerWindow/Pages/MerchantPage")->hide();
}

//! \brief Opens the window only for a seat with a merchant room and starts its live subscription.
bool GameMode::toggleMerchantWindow(const CEGUI::EventArgs&)
{
    return selectRoomManagerType(RoomType::merchant);
}

//! \brief Starts live stock updates when the merchant page becomes selected.
void GameMode::showMerchantPage()
{
    mRootWindow->getChild("RoomManagerWindow/Pages/MerchantPage")->show();
    cancelMerchantItem();
    ClientNotification* request = new ClientNotification(ClientNotificationType::askMerchantWindow);
    request->mPacket << true;
    ODClient::getSingleton().queueClientNotification(request);
}

//! \brief Closes the merchant window and releases its server-side live subscription.
bool GameMode::hideMerchantWindow(const CEGUI::EventArgs&)
{
    cancelMerchantItem();
    mRootWindow->getChild("RoomManagerWindow/Pages/MerchantPage")->hide();
    if(isConnected())
    {
        ClientNotification* request = new ClientNotification(ClientNotificationType::askMerchantWindow);
        request->mPacket << false;
        ODClient::getSingleton().queueClientNotification(request);
    }
    return true;
}

//! \brief Sends only a user-triggered five-point margin step.
bool GameMode::changeMerchantMargin(const CEGUI::EventArgs&)
{
    if(mMerchantUpdating || !isConnected()) return true;
    const float value = static_cast<CEGUI::Slider*>(mRootWindow->getChild("RoomManagerWindow/Pages/MerchantPage/MarginSlider"))->getCurrentValue();
    const int32_t margin = static_cast<int32_t>(std::round(value / MARGIN_STEP) * MARGIN_STEP);
    ClientNotification* request = new ClientNotification(ClientNotificationType::askMerchantSettings);
    request->mPacket << margin << mMerchantModeShown;
    ODClient::getSingleton().queueClientNotification(request);
    return true;
}

//! \brief Toggles fair and profit without changing the keeper's current margin.
bool GameMode::cycleMerchantMode(const CEGUI::EventArgs& args)
{
    if(!isConnected()) return true;
    ClientNotification* request = new ClientNotification(ClientNotificationType::askMerchantSettings);
    const CEGUI::WindowEventArgs& event = static_cast<const CEGUI::WindowEventArgs&>(args);
    const std::string mode = event.window->getName() == "ProfitButton" ? "profit" : "fair";
    request->mPacket << mMerchantMarginShown << mode;
    ODClient::getSingleton().queueClientNotification(request);
    return true;
}

//! \brief Applies settings without sending a second request from the slider callback.
void GameMode::setMerchantSettingsShown(int32_t margin, const std::string& mode)
{
    mMerchantUpdating = true;
    mMerchantMarginShown = margin;
    mMerchantModeShown = mode;
    static_cast<CEGUI::Slider*>(mRootWindow->getChild("RoomManagerWindow/Pages/MerchantPage/MarginSlider"))->setCurrentValue(static_cast<float>(margin));
    mRootWindow->getChild("RoomManagerWindow/Pages/MerchantPage/MarginLabel")->setText(Helper::toString(margin) + " %");
    mRootWindow->getChild("RoomManagerWindow/Pages/MerchantPage/ModeButton/Check")->setVisible(mode == "fair");
    mRootWindow->getChild("RoomManagerWindow/Pages/MerchantPage/ProfitButton/Check")->setVisible(mode == "profit");
    mRootWindow->getChild("RoomManagerWindow/Pages/MerchantPage/MarginSlider")->setVisible(mode == "profit");
    mRootWindow->getChild("RoomManagerWindow/Pages/MerchantPage/MarginLabel")->setVisible(mode == "profit");
    mMerchantUpdating = false;
}

//! \brief Accepts only a complete stock snapshot and renders item images, frames and full tooltips.
void GameMode::receiveMerchantWindow(ODPacket& packet)
{
    int32_t margin = 0;
    std::string mode;
    uint32_t count = 0;
    if(!(packet >> margin >> mode >> count)) return;
    std::vector<std::pair<uint32_t, ItemInstance>> items;
    for(uint32_t index = 0; index < count; ++index)
    {
        uint32_t id = 0;
        ItemInstance item;
        if(!(packet >> id) || !item.importFromPacket(packet)) return;
        items.push_back(std::make_pair(id, item));
    }
    uint32_t historyCount = 0;
    if(!(packet >> historyCount)) return;
    for(uint32_t index = 0; index < historyCount; ++index)
    {
        std::string encoded;
        if(!(packet >> encoded)) return;
    }
    mMerchantItems = items;
    setMerchantSettingsShown(margin, mode);
    CEGUI::MultiColumnList* list = static_cast<CEGUI::MultiColumnList*>(mRootWindow->getChild("RoomManagerWindow/Pages/MerchantPage/StockList"));
    list->resetList();
    const std::size_t slots = std::max<std::size_t>(18, ((items.size() + 5) / 6) * 6);
    for(std::size_t index = 0; index < slots; ++index)
    {
        if(index % 6 == 0) list->addRow();
        CEGUI::ListboxTextItem* cell;
        if(index < items.size())
        {
            cell = new MerchantImageItem(items[index].second, items[index].first);
            cell->setTooltipText(items[index].second.describe(mGameMap));
        }
        else
        {
            cell = new MerchantImageItem(ItemInstance(), 0);
            cell->setDisabled(true);
        }
        list->setItem(cell, static_cast<uint32_t>(index % 6), static_cast<uint32_t>(index / 6));
    }
    refreshMerchantSelection();
}

//! \brief Keeps the pending price and treasury state current without opening a closed confirmation.
bool GameMode::refreshMerchantSelection(const CEGUI::EventArgs&)
{
    if(!mMerchantConfirmationOpen) return true;
    CEGUI::Window* confirmation = mRootWindow->getChild("RoomManagerWindow/Pages/MerchantPage/Confirmation");
    Player* player = mGameMap->getLocalPlayer();
    for(const std::pair<uint32_t, ItemInstance>& entry : mMerchantItems)
        if(entry.first == mMerchantPendingId)
        {
            const double price = entry.second.getPrice(mGameMap);
            confirmation->getChild("Item")->setProperty("Image", "ItemImages/" + entry.second.getImageName());
            confirmation->getChild("Name")->setText(entry.second.getDisplayName(mGameMap));
            confirmation->getChild("Price")->setText(Helper::toString(price));
            confirmation->getChild("OK")->setEnabled(player != nullptr && player->getSeat() != nullptr && player->getSeat()->getGold() >= price);
            return true;
        }
    cancelMerchantItem();
    return true;
}

//! \brief Opens the selected good without treating affordability as permission to see its price.
bool GameMode::confirmMerchantItem(const CEGUI::EventArgs& args)
{
    const CEGUI::MouseEventArgs& event = static_cast<const CEGUI::MouseEventArgs&>(args);
    if(event.button != CEGUI::LeftButton) return true;
    CEGUI::MultiColumnList* list = static_cast<CEGUI::MultiColumnList*>(mRootWindow->getChild("RoomManagerWindow/Pages/MerchantPage/StockList"));
    CEGUI::ListboxItem* selected = merchantItemAtPointer(list, event.position);
    if(selected == nullptr || selected->isDisabled()) return true;
    mMerchantPendingId = selected->getID();
    mMerchantConfirmationOpen = true;
    CEGUI::Window* confirmation = mRootWindow->getChild("RoomManagerWindow/Pages/MerchantPage/Confirmation");
    confirmation->show();
    confirmation->moveToFront();
    refreshMerchantSelection();
    return true;
}

//! \brief Shows only the hovered good's full item description, anchored at the pointer.
bool GameMode::hoverMerchantItem(const CEGUI::EventArgs& args)
{
    const CEGUI::MouseEventArgs& event = static_cast<const CEGUI::MouseEventArgs&>(args);
    CEGUI::MultiColumnList* list = static_cast<CEGUI::MultiColumnList*>(event.window);
    CEGUI::ListboxItem* item = merchantItemAtPointer(list, event.position);
    list->setTooltipText(item == nullptr || item->isDisabled() ? "" : item->getTooltipText());
    if(list->getTooltip() != nullptr) list->getTooltip()->positionSelf();
    return true;
}

//! \brief Cancels a pending good when the user cancels, changes page or the item disappears.
bool GameMode::cancelMerchantItem(const CEGUI::EventArgs&)
{
    mMerchantConfirmationOpen = false;
    mRootWindow->getChild("RoomManagerWindow/Pages/MerchantPage/Confirmation")->hide();
    return true;
}

//! \brief Asks the server to buy only the confirmed stable goods identity at its current price.
bool GameMode::buyMerchantItem(const CEGUI::EventArgs&)
{
    refreshMerchantSelection();
    if(!isConnected() || !mMerchantConfirmationOpen ||
        mRootWindow->getChild("RoomManagerWindow/Pages/MerchantPage/Confirmation/OK")->isDisabled()) return true;
    ClientNotification* request = new ClientNotification(ClientNotificationType::askMerchantBuy);
    request->mPacket << mMerchantPendingId;
    ODClient::getSingleton().queueClientNotification(request);
    cancelMerchantItem();
    return true;
}
