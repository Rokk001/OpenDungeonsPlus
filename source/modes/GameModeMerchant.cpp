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

#include <algorithm>
#include <cmath>
#include <sstream>

namespace
{
static const float ICON_DESIGN_SIZE = 64.0f;
static const float STOCK_DESIGN_WIDTH = 740.0f;
static const float MARGIN_STEP = 5.0f;
static const uint32_t QUALITY_COLOURS[] = {0xFF8A8A8A,0xFFFFFFFF,0xFF3E7BFF,0xFFA64DFF};

//! \brief Draws the actual item and its quality frame in the merchant's image column.
class MerchantImageItem : public CEGUI::ListboxTextItem
{
public:
    //! \brief Retains image names while the existing list owns the item and its tooltip.
    MerchantImageItem(const ItemInstance& item, uint32_t index) : CEGUI::ListboxTextItem("", index),
        mImage("ItemImages/" + item.getImageName()), mFrame("OpenDungeonsIcons/ItemFrame" + qualityName(item.mQuality)) {}
    //! \brief Fits the 64-design-pixel row height to the registered window's actual scale.
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

//! \brief Resolves transport identities into creature profile names for the approved history sentences.
std::string historyText(const std::string& encoded)
{
    std::stringstream stream(encoded);
    std::vector<std::string> fields;
    std::string part;
    while(std::getline(stream, part, '\t')) fields.push_back(part);
    static const size_t FIELD_COUNT = 7;
    if(fields.size() != FIELD_COUNT) return std::string();
    std::string name = fields[1];
    if(!fields[2].empty()) name = social::SocialProfileCache::getSingleton().getProfile(fields[1], fields[2], fields[3] == "1").getFullName();
    return fields[0] + " " + name + " " + fields[4] + " " + fields[5] + " for " + fields[6];
}
}

//! \brief Sets up one stock list and the approved owner controls after the layout imports are registered.
void GameMode::initializeMerchantWindow()
{
    CEGUI::MultiColumnList* list = static_cast<CEGUI::MultiColumnList*>(mRootWindow->getChild("MerchantWindow/StockList"));
    list->setSelectionMode(CEGUI::MultiColumnList::RowSingle);
    if(list->getColumnCount() == 0)
    {
        list->addColumn("Image", 0, CEGUI::UDim(0.0f, ICON_DESIGN_SIZE));
        list->addColumn("Name", 1, CEGUI::UDim(0.25f, 0));
        list->addColumn("Quality", 2, CEGUI::UDim(0.11f, 0));
        list->addColumn("Price", 3, CEGUI::UDim(0.11f, 0));
        list->addColumn("Bonuses", 4, CEGUI::UDim(0.40f, 0));
    }
    addEventConnection(mRootWindow->getChild("MerchantButton")->subscribeEvent(CEGUI::PushButton::EventClicked,
        CEGUI::Event::Subscriber(&GameMode::toggleMerchantWindow, this)));
    addEventConnection(mRootWindow->getChild("MerchantWindow")->subscribeEvent(CEGUI::FrameWindow::EventCloseClicked,
        CEGUI::Event::Subscriber(&GameMode::hideMerchantWindow, this)));
    addEventConnection(mRootWindow->getChild("MerchantWindow/CloseButton")->subscribeEvent(CEGUI::PushButton::EventClicked,
        CEGUI::Event::Subscriber(&GameMode::hideMerchantWindow, this)));
    addEventConnection(list->subscribeEvent(CEGUI::MultiColumnList::EventSelectionChanged,
        CEGUI::Event::Subscriber(&GameMode::refreshMerchantSelection, this)));
    CEGUI::Slider* slider = static_cast<CEGUI::Slider*>(mRootWindow->getChild("MerchantWindow/MarginSlider"));
    slider->setMaxValue(static_cast<float>(ConfigManager::getSingleton().getRoomConfigInt32("MerchantMarginMax")));
    slider->setClickStep(MARGIN_STEP);
    addEventConnection(slider->subscribeEvent(CEGUI::Slider::EventValueChanged,
        CEGUI::Event::Subscriber(&GameMode::changeMerchantMargin, this)));
    addEventConnection(mRootWindow->getChild("MerchantWindow/ModeButton")->subscribeEvent(CEGUI::PushButton::EventClicked,
        CEGUI::Event::Subscriber(&GameMode::cycleMerchantMode, this)));
    addEventConnection(mRootWindow->getChild("MerchantWindow/BuyButton")->subscribeEvent(CEGUI::PushButton::EventClicked,
        CEGUI::Event::Subscriber(&GameMode::buyMerchantItem, this)));
    mRootWindow->getChild("MerchantWindow")->hide();
}

//! \brief Opens the window only for a seat with a merchant room and starts its live subscription.
bool GameMode::toggleMerchantWindow(const CEGUI::EventArgs&)
{
    if(mRootWindow->getChild("MerchantWindow")->isVisible()) return hideMerchantWindow();
    Player* player = mGameMap->getLocalPlayer();
    if(!isConnected() || player == nullptr || player->getSeat()->getNbRooms(RoomType::merchant) == 0) return true;
    mRootWindow->getChild("MerchantWindow")->show();
    mMerchantSnapshotReceived = false;
    ClientNotification* request = new ClientNotification(ClientNotificationType::askMerchantWindow);
    request->mPacket << true;
    ODClient::getSingleton().queueClientNotification(request);
    return true;
}

//! \brief Closes the merchant window and releases its server-side live subscription.
bool GameMode::hideMerchantWindow(const CEGUI::EventArgs&)
{
    mRootWindow->getChild("MerchantWindow")->hide();
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
    const float value = static_cast<CEGUI::Slider*>(mRootWindow->getChild("MerchantWindow/MarginSlider"))->getCurrentValue();
    const int32_t margin = static_cast<int32_t>(std::round(value / MARGIN_STEP) * MARGIN_STEP);
    ClientNotification* request = new ClientNotification(ClientNotificationType::askMerchantSettings);
    request->mPacket << margin << mMerchantModeShown;
    ODClient::getSingleton().queueClientNotification(request);
    return true;
}

//! \brief Toggles fair and profit without changing the keeper's current margin.
bool GameMode::cycleMerchantMode(const CEGUI::EventArgs&)
{
    if(!isConnected()) return true;
    ClientNotification* request = new ClientNotification(ClientNotificationType::askMerchantSettings);
    const std::string mode = mMerchantModeShown == "fair" ? "profit" : "fair";
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
    static_cast<CEGUI::Slider*>(mRootWindow->getChild("MerchantWindow/MarginSlider"))->setCurrentValue(static_cast<float>(margin));
    mRootWindow->getChild("MerchantWindow/MarginLabel")->setText("Margin: " + Helper::toString(margin) + " %");
    mRootWindow->getChild("MerchantWindow/ModeButton")->setText(mode == "fair" ? "Fair" : "Profit");
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
    std::string history;
    for(uint32_t index = 0; index < historyCount; ++index)
    {
        std::string encoded;
        if(!(packet >> encoded)) return;
        history += historyText(encoded) + '\n';
    }
    const bool newDeal = mMerchantSnapshotReceived && history != mMerchantHistoryShown;
    mMerchantHistoryShown = history;
    mMerchantSnapshotReceived = true;
    mMerchantItems = items;
    setMerchantSettingsShown(margin, mode);
    CEGUI::MultiColumnList* list = static_cast<CEGUI::MultiColumnList*>(mRootWindow->getChild("MerchantWindow/StockList"));
    const CEGUI::ListboxItem* selected = list->getFirstSelectedItem();
    const uint32_t selectedId = selected == nullptr ? 0 : selected->getID();
    list->resetList();
    const float iconScale = list->getPixelSize().d_width / STOCK_DESIGN_WIDTH;
    list->setColumnHeaderWidth(0, CEGUI::UDim(0.0f, ICON_DESIGN_SIZE * iconScale));
    for(const std::pair<uint32_t, ItemInstance>& entry : mMerchantItems)
    {
        const ItemInstance& item = entry.second;
        const uint32_t row = list->addRow(entry.first);
        const std::string tooltip = item.describe(mGameMap);
        CEGUI::ListboxTextItem* image = new MerchantImageItem(item, entry.first);
        image->setTooltipText(tooltip);
        image->setSelectionBrushImage("OpenDungeonsSkin/SelectionBrush");
        list->setItem(image, 0, row);
        std::ostringstream bonuses;
        std::istringstream description(tooltip);
        std::string line;
        std::getline(description, line);
        for(size_t bonus = 0; bonus < item.mBonuses.size() && std::getline(description, line); ++bonus)
            bonuses << line << ' ';
        const std::string values[] = {item.getDisplayName(mGameMap), qualityName(item.mQuality),
            Helper::toString(item.getPrice(mGameMap)), bonuses.str()};
        static const uint32_t TEXT_COLUMNS = 4;
        for(uint32_t column = 0; column < TEXT_COLUMNS; ++column)
        {
            CEGUI::ListboxTextItem* cell = new CEGUI::ListboxTextItem(values[column], entry.first);
            cell->setTooltipText(tooltip);
            cell->setTextColours(CEGUI::Colour(QUALITY_COLOURS[static_cast<size_t>(item.mQuality)]));
            cell->setSelectionBrushImage("OpenDungeonsSkin/SelectionBrush");
            list->setItem(cell, column + 1, row);
        }
        if(entry.first == selectedId) list->setItemSelectState(image, true);
    }
    mRootWindow->getChild("MerchantWindow/HistoryText")->setText(history);
    refreshMerchantSelection();
    if(newDeal && isConnected() && mRootWindow->getChild("MerchantWindow")->isVisible())
    {
        ClientNotification* request = new ClientNotification(ClientNotificationType::askMerchantWindow);
        request->mPacket << true;
        ODClient::getSingleton().queueClientNotification(request);
    }
}

//! \brief Keeps the approved buy label and treasury-enabled state matched to the selected good.
bool GameMode::refreshMerchantSelection(const CEGUI::EventArgs&)
{
    CEGUI::MultiColumnList* list = static_cast<CEGUI::MultiColumnList*>(mRootWindow->getChild("MerchantWindow/StockList"));
    CEGUI::ListboxItem* selected = list->getFirstSelectedItem();
    Player* player = mGameMap->getLocalPlayer();
    CEGUI::Window* button = mRootWindow->getChild("MerchantWindow/BuyButton");
    button->setEnabled(false);
    button->setText("Buy");
    if(selected == nullptr || player == nullptr) return true;
    for(const std::pair<uint32_t, ItemInstance>& entry : mMerchantItems)
        if(entry.first == selected->getID())
        {
            const double price = entry.second.getPrice(mGameMap);
            button->setText("Buy (" + Helper::toString(price) + ")");
            button->setEnabled(player->getSeat()->getGold() >= price);
            break;
        }
    return true;
}

//! \brief Asks the server to buy the stable selected goods index at its base price.
bool GameMode::buyMerchantItem(const CEGUI::EventArgs&)
{
    if(!isConnected()) return true;
    CEGUI::ListboxItem* selected = static_cast<CEGUI::MultiColumnList*>(mRootWindow->getChild("MerchantWindow/StockList"))->getFirstSelectedItem();
    if(selected != nullptr)
    {
        ClientNotification* request = new ClientNotification(ClientNotificationType::askMerchantBuy);
        request->mPacket << static_cast<uint32_t>(selected->getID());
        ODClient::getSingleton().queueClientNotification(request);
    }
    return true;
}
