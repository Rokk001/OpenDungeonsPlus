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

#include "render/SocialWindow.h"

#include "creaturemood/CreatureMood.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/CreatureMoodValues.h"
#include "game/CreatureAppearance.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "modes/ModeManager.h"
#include "network/ODClient.h"
#include "render/Gui.h"
#include "render/CreatureAppearancePicture.h"
#include "render/CreaturePortrait.h"
#include "render/ODFrameListener.h"
#include "rooms/RoomType.h"
#include "social/CreaturePosts.h"
#include "social/PostLog.h"
#include "social/SocialGenerator.h"
#include "social/SocialProfileCache.h"
#include "ODApplication.h"

#include <CEGUI/Font.h>
#include <CEGUI/Image.h>
#include <CEGUI/ImageManager.h>
#include <CEGUI/InputEvent.h>
#include <CEGUI/PropertyHelper.h>
#include <CEGUI/widgets/PushButton.h>
#include <CEGUI/widgets/Scrollbar.h>
#include <CEGUI/Window.h>
#include <CEGUI/WindowManager.h>

#include <algorithm>
#include <cmath>
#include <deque>
#include <iomanip>
#include <sstream>

namespace
{
//! Number of posts shown in the feed at most
const std::size_t MAX_FEED_ROWS = 25;
//! Number of posts shown as pictures in the posts column of the profile at most (ProfilePage/PostThumb0..5)
const std::size_t MAX_OWN_POSTS = 6;
//! Rows of the creature list and of the two feeds in gui/WindowSocial.layout (ListRows/Row0.., FeedRows/Row0..).
//! A post row holds the portrait, the name line, two lines of text and the picture of the post below them.
const std::size_t LIST_ROWS = 7;
const std::size_t FEED_ROWS = 3;
//! Number of item slots of the inventory page (6 equipment, 3 potions, 4 inventory)
const std::size_t ITEM_SLOTS = 13;
//! The window checks for changes at most this often (real seconds), so at most 4 redraws per second
const float REFRESH_CHECK_INTERVAL = 0.25f;
//! The relative times of the feed are refreshed at least this often while the window is open
const float FEED_TIME_REFRESH_INTERVAL = 5.0f;

//! Posts younger than this many seconds are shown as "just now"
const double AGE_JUST_NOW_SECONDS = 10.0;
const double SECONDS_PER_MINUTE = 60.0;
const double SECONDS_PER_HOUR = 3600.0;
//! Colours of the caption of the active and of the inactive tab (ARGB)
const char* const TAB_COLOUR_ACTIVE = "FFF2C860";
const char* const TAB_COLOUR_INACTIVE = "FFF0E2C0";

const char* const FEED_NAME_COLOUR = "[colour='FFF2C860']";
const char* const FEED_TIME_COLOUR = "[colour='FFB8AC90']";
const char* const FEED_TEXT_COLOUR = "[colour='FFE8DCC0']";

//! Names of the filter buttons and of the navigation buttons, in the order of the filters and of the pages
const char* const FILTER_BUTTONS[] = {"FilterAll", "FilterWorkers", "FilterFighters", "FilterUnhappy"};
const char* const FILTER_LABELS[] = {"All", "Workers", "Fighters", "Unhappy"};
const char* const NAV_BUTTONS[] = {"NavFeed", "NavProfile", "NavValues", "NavInventory"};

bool isEntryBefore(const std::pair<std::string, std::string>& a, const std::pair<std::string, std::string>& b)
{
    return a.first < b.first;
}

//! \brief CEGUI reads [ as the start of a tag in parsed text
std::string escapeMarkup(const std::string& text)
{
    std::string result;
    for(std::size_t i = 0; i < text.size(); ++i)
    {
        if(text[i] == '[')
            result += '\\';
        result += text[i];
    }
    return result;
}

std::string formatAge(int64_t turns)
{
    double seconds = static_cast<double>(turns) / ODApplication::turnsPerSecond;
    std::ostringstream stream;
    if(seconds < AGE_JUST_NOW_SECONDS)
        stream << "just now";
    else if(seconds < SECONDS_PER_MINUTE)
        stream << static_cast<int32_t>(seconds) << " sec ago";
    else if(seconds < SECONDS_PER_HOUR)
        stream << static_cast<int32_t>(seconds / SECONDS_PER_MINUTE) << " min ago";
    else
        stream << static_cast<int32_t>(seconds / SECONDS_PER_HOUR) << " h ago";
    return stream.str();
}

//! \brief Uses locally recorded creatures when roster snapshots cannot be requested.
bool useLocalCreatureRoster()
{
    const ODClient& client = ODClient::getSingleton();
    return client.isReplay() || !client.supportsDungeonbookRoster();
}

//! \brief The text of a post, empty if its category has no template
std::string renderPostText(const social::Post& post, const social::CreatureProfile& profile)
{
    social::SocialProfileCache& cache = social::SocialProfileCache::getSingleton();
    int32_t level = 0;
    std::string room;
    if((post.mCategory == social::PostCategory::LevelUp) || (post.mCategory == social::PostCategory::Payday))
        level = post.mArgument;
    else if((post.mCategory == social::PostCategory::Work) || (post.mCategory == social::PostCategory::Train) ||
        (post.mCategory == social::PostCategory::Wish) || (post.mCategory == social::PostCategory::ThanksWish))
        room = social::CreaturePosts::getRoomName(post.mArgument);

    return social::SocialGenerator::renderPost(cache.getData(), profile, post.mIsWorker,
        social::getPostCategoryName(post.mCategory), post.mVariant, level, room,
        post.mCategory >= social::PostCategory::Bought ? "" : post.mOther,
        post.mCategory >= social::PostCategory::Bought ? post.mOther : "");
}

//! \brief Name of the HUD picture of a room type in the OpenDungeonsIcons imageset, empty if the room has none.
std::string roomPictureName(int32_t roomType)
{
    switch(static_cast<RoomType>(roomType))
    {
        case RoomType::dungeonTemple: return "TempleButton";
        case RoomType::dormitory: return "DormitoryButton";
        case RoomType::treasury: return "TreasuryButton";
        case RoomType::portal:
        case RoomType::portalWave: return "PortalButton";
        case RoomType::workshop: return "WorkshopButton";
        case RoomType::trainingHall: return "TrainingHallButton";
        case RoomType::library: return "LibraryButton";
        case RoomType::hatchery: return "HatcheryButton";
        case RoomType::crypt: return "CryptButton";
        case RoomType::prison: return "PrisonButton";
        case RoomType::bridgeWooden: return "WoodenBridgeButton";
        case RoomType::bridgeStone: return "StoneBridgeButton";
        case RoomType::arena: return "ArenaButton";
        case RoomType::casino: return "CasinoButton";
        case RoomType::torture: return "TortureButton";
        case RoomType::guardRoom: return "GuardRoomButton";
        case RoomType::temple: return "PrayerTempleButton";
        case RoomType::toilet: return "ToiletButton";
        case RoomType::merchant: return "MerchantButton";
        case RoomType::herbGarden: return "HerbGardenButton";
        case RoomType::alchemyLab: return "AlchemyLabButton";
        case RoomType::tavern: return "TavernButton";
        case RoomType::infirmary: return "InfirmaryButton";
        case RoomType::ghostRoom: return "GhostRoomButton";
        case RoomType::spa: return "SpaButton";
        default: return "";
    }
}

//! \brief Name of the game picture (OpenDungeonsIcons) of what the post is about: the room of a work, training or
//! wish post, the room or the thing of a meal, a night, a payday, a drink, a purchase and so on. Empty when the post
//! is about the creature itself (level up, hurt, friendship, ...); the book shows the portrait of the creature then.
std::string postPictureName(const social::Post& post)
{
    using social::PostCategory;
    switch(post.mCategory)
    {
        case PostCategory::Work:
        case PostCategory::Wish:
        case PostCategory::ThanksWish:
            return roomPictureName(post.mArgument);
        case PostCategory::Train:
        {
            const std::string room = roomPictureName(post.mArgument);
            return room.empty() ? "TrainingHallButton" : room;
        }
        case PostCategory::Eat:
        case PostCategory::ComplainHungry:
        case PostCategory::ThanksHungry:
            return "HatcheryButton";
        case PostCategory::Sleep:
        case PostCategory::ComplainBed:
        case PostCategory::ThanksBed:
        case PostCategory::ComplainTired:
        case PostCategory::ThanksTired:
            return "DormitoryButton";
        case PostCategory::Payday:
        case PostCategory::ComplainWage:
        case PostCategory::ThanksWage:
            return "GoldCoin";
        case PostCategory::Fight:
        case PostCategory::ComplainFight:
        case PostCategory::ThanksFight:
            return "FighterButton";
        case PostCategory::Jail:
            return "PrisonButton";
        case PostCategory::PickedUp:
        case PostCategory::ComplainHeld:
        case PostCategory::ThanksHeld:
            return "WorkerHandActive";
        case PostCategory::Arrived:
            return "PortalButton";
        case PostCategory::Relieved:
            return "ToiletButton";
        case PostCategory::Bought:
        case PostCategory::Bargain:
        case PostCategory::Fleeced:
            return "MerchantButton";
        case PostCategory::Gift:
            return "WorkerCarryGift";
        case PostCategory::Drank:
        case PostCategory::ComplainThirsty:
        case PostCategory::ThanksThirsty:
            return "BeerButton";
        case PostCategory::DuelWon:
        case PostCategory::DuelLost:
        case PostCategory::Drunk:
        case PostCategory::Hungover:
            return "TavernButton";
        case PostCategory::GhostScared:
        case PostCategory::GhostHunted:
            return "GhostRoomButton";
        case PostCategory::Relaxed:
            return "SpaButton";
        default:
            return "";
    }
}

//! \brief The text shortened with "..." so it is not wider than the given pixel width
std::string elideToWidth(const CEGUI::Font* font, const std::string& text, float maxWidth)
{
    if((font == nullptr) || (font->getTextExtent(text) <= maxWidth))
        return text;

    std::string shortened = text;
    while(!shortened.empty() && (font->getTextExtent(shortened + "...") > maxWidth))
        shortened.erase(shortened.size() - 1);
    return shortened + "...";
}

//! \brief Sets the plain text of a single-line window, shortened with "..." to the width of the window.
void setElidedText(CEGUI::Window* window, const std::string& text)
{
    window->setText(escapeMarkup(elideToWidth(window->getFont(), text, window->getPixelSize().d_width)));
}

//! \brief True if the text of the window is not higher than the given pixel height.
bool isTileTextFitting(const CEGUI::Window* tile, float height)
{
    return CEGUI::PropertyHelper<float>::fromString(tile->getProperty("VertExtent")) <= height;
}

//! \brief Returns the value after "label: " of the first line of the statistics text that starts with the label,
//! without colour and font markup tags. The result is empty if the line does not exist.
std::string findStatisticsValue(const std::string& stats, const std::string& label)
{
    const std::string prefix = label + ": ";
    std::string::size_type lineStart = 0;
    while(lineStart < stats.size())
    {
        std::string::size_type lineEnd = stats.find('\n', lineStart);
        if(lineEnd == std::string::npos)
            lineEnd = stats.size();
        const std::string line = stats.substr(lineStart, lineEnd - lineStart);
        lineStart = lineEnd + 1;
        // The markup of a line may start before the label (a font or colour tag), so the tags are dropped first
        std::string plain;
        bool inTag = false;
        for(std::size_t i = 0; i < line.size(); ++i)
        {
            if(line[i] == '[')
                inTag = true;
            else if(line[i] == ']' && inTag)
                inTag = false;
            else if(!inTag)
                plain += line[i];
        }
        if(plain.compare(0, prefix.size(), prefix) == 0)
            return plain.substr(prefix.size());
    }
    return std::string();
}

//! \brief Formats a Dungeonbook value for display with at most two decimals and without trailing zeros.
//! The stored values are doubles (for example 1.83149...), which would otherwise show four or more decimals.
std::string formatProfileValue(double value)
{
    std::ostringstream text;
    text << std::fixed << std::setprecision(2) << value;
    std::string result = text.str();
    if(result.find('.') != std::string::npos)
    {
        while(!result.empty() && result[result.size() - 1] == '0')
            result.erase(result.size() - 1);
        if(!result.empty() && result[result.size() - 1] == '.')
            result.erase(result.size() - 1);
    }
    if(result == "-0")
        result = "0";
    return result;
}

//! \brief Splits a statistics value like "12.5 / 40" at its " / " separators.
std::vector<std::string> splitStatisticsValue(const std::string& value)
{
    std::vector<std::string> parts;
    std::string::size_type start = 0;
    while(true)
    {
        const std::string::size_type separator = value.find(" / ", start);
        parts.push_back(value.substr(start, separator == std::string::npos ? std::string::npos : separator - start));
        if(separator == std::string::npos)
            return parts;
        start = separator + 3;
    }
}

//! \brief The statistics value with every part that is a plain number rounded like the other values of the book.
std::string formatStatisticsNumbers(const std::string& value)
{
    if(value.empty())
        return "-";

    const std::vector<std::string> parts = splitStatisticsValue(value);
    std::string result;
    for(std::size_t i = 0; i < parts.size(); ++i)
    {
        std::istringstream parser(parts[i]);
        double number = 0.0;
        std::string rest;
        const bool isNumber = static_cast<bool>(parser >> number) && !(parser >> rest);
        result += (i > 0 ? " / " : "") + (isNumber ? formatProfileValue(number) : parts[i]);
    }
    return result;
}

//! \brief "filled / slots" for a statistics value listing one item or "-" per slot ("Healing Draught / - / -").
std::string countFilledSlots(const std::string& value)
{
    if(value.empty())
        return "-";

    const std::vector<std::string> parts = splitStatisticsValue(value);
    std::size_t filled = 0;
    for(const std::string& part : parts)
    {
        if(!part.empty() && part != "-")
            ++filled;
    }
    return std::to_string(filled) + " / " + std::to_string(parts.size());
}

//! \brief Fills a text window with a head (markup) and a value, shortening the value with "..." until the text
//! fits the height of the window, so the window never needs a scrollbar.
void fitTextToWindow(CEGUI::Window* window, const std::string& head, const std::string& value)
{
    const float height = window->getPixelSize().d_height;
    window->setText(head + escapeMarkup(value));
    if(height <= 0.0f || isTileTextFitting(window, height))
        return;

    // Binary search for the longest prefix (cut at a character boundary) that fits together with the dots
    std::size_t low = 0;
    std::size_t high = value.size();
    while(low < high)
    {
        std::size_t middle = (low + high + 1) / 2;
        while(middle > 0 && (static_cast<unsigned char>(value[middle]) & 0xC0) == 0x80)
            --middle;
        window->setText(head + escapeMarkup(value.substr(0, middle) + "..."));
        if(middle > low && isTileTextFitting(window, height))
            low = middle;
        else
            high = (middle > low) ? middle - 1 : low;
    }
    window->setText(head + escapeMarkup(value.substr(0, low) + "..."));
}

//! \brief Lets the mouse wheel of every window below the given one reach it.
void propagateMouseInput(CEGUI::Window* window)
{
    for(std::size_t i = 0; i < window->getChildCount(); ++i)
    {
        CEGUI::Window* child = window->getChildAtIdx(i);
        child->setMouseInputPropagationEnabled(true);
        propagateMouseInput(child);
    }
}

//! \brief Sets the range of a row scrollbar (one step per row) and returns the first shown row.
std::size_t setupRowScroll(CEGUI::Scrollbar* bar, std::size_t count, std::size_t rows)
{
    bar->setDocumentSize(static_cast<float>(count));
    bar->setPageSize(static_cast<float>(rows));
    bar->setStepSize(1.0f);
    bar->setVisible(count > rows);
    const float maximum = count > rows ? static_cast<float>(count - rows) : 0.0f;
    const float position = std::floor(std::max(0.0f, std::min(bar->getScrollPosition(), maximum)) + 0.5f);
    if(position != bar->getScrollPosition())
        bar->setScrollPosition(position);
    return static_cast<std::size_t>(position);
}

//! \brief Shows the image of the given name in the window, or no image.
void setImage(CEGUI::Window* window, const CEGUI::Image* image)
{
    window->setProperty("Image", image == nullptr ? "" : image->getName());
}

//! \brief Colours the label of a navigation button gold while its page is shown.
void setNavState(CEGUI::Window* button, bool active)
{
    button->getChild("Label")->setProperty("TextColours", active ? TAB_COLOUR_ACTIVE : TAB_COLOUR_INACTIVE);
}
}

SocialWindow::SocialWindow(CEGUI::Window* rootWindow, GameMap& gameMap) :
    mGameMap(gameMap),
    mWindow(rootWindow->getChild("SocialWindow")),
    mFilter(CreatureFilter::All),
    mPage(Page::Home),
    mUpdatingRows(false),
    mProfilePage(nullptr),
    mShownRosterVersion(0),
    mShownPostVersion(0),
    mSinceRefreshCheck(0.0f),
    mSinceFeedRebuild(0.0f),
    mShownProfilePostVersion(0),
    mSinceProfileRefresh(0.0f)
{
    CEGUI::Window* home = mWindow->getChild("HomePage");
    for(std::size_t i = 0; i < 4; ++i)
    {
        CEGUI::Window* filter = home->getChild(FILTER_BUTTONS[i]);
        filter->setUserString("Filter", std::to_string(i));
        connect(filter, CEGUI::PushButton::EventClicked, CEGUI::Event::Subscriber(&SocialWindow::onFilterClicked, this));
        CEGUI::Window* nav = mWindow->getChild(std::string("NavBar/") + NAV_BUTTONS[i]);
        // The pages of one creature follow the start page in the order of the navigation buttons
        nav->setUserString("Page", std::to_string(i + 1));
        connect(nav, CEGUI::PushButton::EventClicked, CEGUI::Event::Subscriber(&SocialWindow::onNavClicked, this));
    }
    for(std::size_t i = 0; i < LIST_ROWS; ++i)
    {
        CEGUI::Window* button = home->getChild("ListRows/Row" + std::to_string(i) + "/Button");
        button->setUserString("Row", std::to_string(i));
        connect(button, CEGUI::PushButton::EventClicked, CEGUI::Event::Subscriber(&SocialWindow::onListRowClicked, this));
    }
    connect(mWindow->getChild("Header/BackButton"), CEGUI::PushButton::EventClicked,
        CEGUI::Event::Subscriber(&SocialWindow::onBackClicked, this));
    connect(mWindow->getChild("Header/PrevButton"), CEGUI::PushButton::EventClicked,
        CEGUI::Event::Subscriber(&SocialWindow::onPreviousClicked, this));
    connect(mWindow->getChild("Header/NextButton"), CEGUI::PushButton::EventClicked,
        CEGUI::Event::Subscriber(&SocialWindow::onNextClicked, this));
    connect(home->getChild("ListScroll"), CEGUI::Scrollbar::EventScrollPositionChanged,
        CEGUI::Event::Subscriber(&SocialWindow::onListScrolled, this));
    connect(home->getChild("ListRows"), CEGUI::Window::EventMouseWheel,
        CEGUI::Event::Subscriber(&SocialWindow::onListWheel, this));
    propagateMouseInput(home->getChild("ListRows"));
    const char* const feedPages[] = {"HomePage", "FeedPage"};
    for(const char* feedPage : feedPages)
    {
        CEGUI::Window* page = mWindow->getChild(feedPage);
        connect(page->getChild("FeedScroll"), CEGUI::Scrollbar::EventScrollPositionChanged,
            CEGUI::Event::Subscriber(&SocialWindow::onFeedScrolled, this));
        connect(page->getChild("FeedRows"), CEGUI::Window::EventMouseWheel,
            CEGUI::Event::Subscriber(&SocialWindow::onFeedWheel, this));
        propagateMouseInput(page->getChild("FeedRows"));
    }
}

//! \brief Disconnects the controls and destroys the page created for this game.
SocialWindow::~SocialWindow()
{
    for(CEGUI::Event::Connection& connection : mLinkConnections)
        connection->disconnect();
    CEGUI::WindowManager& windows = CEGUI::WindowManager::getSingleton();
    if(mProfilePage != nullptr)
        windows.destroyWindow(mProfilePage);
}

void SocialWindow::connect(CEGUI::Window* window, const CEGUI::String& event, const CEGUI::Event::Subscriber& subscriber)
{
    mLinkConnections.push_back(window->subscribeEvent(event, subscriber));
}

void SocialWindow::setTabState(CEGUI::Window* tab, const std::string& label, bool active)
{
    // A bare '[' starts a CEGUI markup tag and would swallow the caption
    tab->setText(active ? "\\[ " + label + " ]" : label);
    tab->setProperty("NormalTextColour", active ? TAB_COLOUR_ACTIVE : TAB_COLOUR_INACTIVE);
}

bool SocialWindow::isVisible() const
{
    return mWindow->isVisible();
}

//! \brief Opens the Dungeonbook and subscribes to its allied roster.
void SocialWindow::show()
{
    if(!mWindow->isVisible() && !useLocalCreatureRoster())
    {
        social::PostLog::getSingleton().clearDungeonbookRoster();
        ODClient::getSingleton().queueClientNotification(ClientNotificationType::askDungeonbookRoster, true);
    }
    mWindow->show();
    mWindow->moveToFront();
    rebuildCreatureList();
    showPage(mSelectedCreature.empty() ? Page::Home : mPage);
    mSinceRefreshCheck = 0.0f;
}

void SocialWindow::showCreature(const std::string& creatureName)
{
    mFilter = CreatureFilter::All;
    mSelectedCreature = creatureName;
    mPage = Page::Profile;
    show();
}

std::string SocialWindow::renderPostTextForLog(const social::Post& post)
{
    social::SocialProfileCache& cache = social::SocialProfileCache::getSingleton();
    return renderPostText(post, cache.getProfile(post.mCreature, post.mClassName, post.mIsWorker));
}

std::string SocialWindow::describeLatestPost(const std::string& creatureName, int64_t turnNow)
{
    const social::Post* post = social::PostLog::getSingleton().findLatestPost(creatureName);
    if(post == nullptr)
        return "";

    social::SocialProfileCache& cache = social::SocialProfileCache::getSingleton();
    std::string text = renderPostText(*post, cache.getProfile(post->mCreature, post->mClassName, post->mIsWorker));
    if(text.empty())
        return text;

    return "Latest: " + text + "  (" + formatAge(turnNow - post->mTurn) + ")";
}

//! \brief Closes the Dungeonbook and stops its roster updates.
void SocialWindow::hide()
{
    if(!mWindow->isVisible())
        return;
    if(!useLocalCreatureRoster())
    {
        ODClient::getSingleton().queueClientNotification(ClientNotificationType::askDungeonbookRoster, false);
        social::PostLog::getSingleton().clearDungeonbookRoster();
    }
    mWindow->hide();
}

void SocialWindow::update(float elapsed)
{
    if(!mWindow->isVisible())
        return;

    mSinceRefreshCheck += elapsed;
    mSinceFeedRebuild += elapsed;
    mSinceProfileRefresh += elapsed;
    if(mSinceRefreshCheck < REFRESH_CHECK_INTERVAL)
        return;

    mSinceRefreshCheck = 0.0f;
    social::PostLog& log = social::PostLog::getSingleton();
    if(log.getRosterVersion() != mShownRosterVersion)
        rebuildCreatureList();
    if((log.getVersion() != mShownPostVersion) || (mSinceFeedRebuild >= FEED_TIME_REFRESH_INTERVAL))
        rebuildFeed();
    if((mPage != Page::Home) &&
       ((log.getVersion() != mShownProfilePostVersion) || (mSinceProfileRefresh >= FEED_TIME_REFRESH_INTERVAL)))
        refreshPage();
}

bool SocialWindow::onCloseClicked(const CEGUI::EventArgs& /*e*/)
{
    hide();
    return true;
}

bool SocialWindow::onFilterClicked(const CEGUI::EventArgs& e)
{
    const CEGUI::WindowEventArgs& args = static_cast<const CEGUI::WindowEventArgs&>(e);
    const std::string index = args.window->getUserString("Filter").c_str();
    const CreatureFilter filters[] = {CreatureFilter::All, CreatureFilter::Workers, CreatureFilter::Fighters,
        CreatureFilter::Unhappy};
    for(std::size_t i = 0; i < 4; ++i)
    {
        if(index == std::to_string(i))
            mFilter = filters[i];
    }
    rebuildCreatureList();
    return true;
}

bool SocialWindow::onListRowClicked(const CEGUI::EventArgs& e)
{
    const CEGUI::WindowEventArgs& args = static_cast<const CEGUI::WindowEventArgs&>(e);
    std::istringstream parser(args.window->getUserString("Row").c_str());
    std::size_t row = 0;
    if(!(parser >> row))
        return true;

    CEGUI::Scrollbar* bar = static_cast<CEGUI::Scrollbar*>(mWindow->getChild("HomePage/ListScroll"));
    const std::size_t index = static_cast<std::size_t>(bar->getScrollPosition() + 0.5f) + row;
    // Selecting a creature shows its profile right away
    if(index < mListedCreatures.size())
        selectCreature(mListedCreatures[index], Page::Profile);
    return true;
}

bool SocialWindow::onNavClicked(const CEGUI::EventArgs& e)
{
    const CEGUI::WindowEventArgs& args = static_cast<const CEGUI::WindowEventArgs&>(e);
    const std::string index = args.window->getUserString("Page").c_str();
    const Page pages[] = {Page::Feed, Page::Profile, Page::Values, Page::Inventory};
    Page page = Page::Home;
    for(std::size_t i = 0; i < 4; ++i)
    {
        if(index == std::to_string(i + 1))
            page = pages[i];
    }
    // The feed button of the start page is the start page itself; the other buttons need a creature, the selected
    // one or else the first of the list
    if(mPage == Page::Home && page == Page::Feed)
        return true;
    if(mSelectedCreature.empty() && !mListedCreatures.empty())
        mSelectedCreature = mListedCreatures[0];
    if(mSelectedCreature.empty())
        return true;

    showPage(page);
    return true;
}

bool SocialWindow::onBackClicked(const CEGUI::EventArgs& /*e*/)
{
    showPage(Page::Home);
    return true;
}

bool SocialWindow::onPreviousClicked(const CEGUI::EventArgs& /*e*/)
{
    stepCreature(-1);
    return true;
}

bool SocialWindow::onNextClicked(const CEGUI::EventArgs& /*e*/)
{
    stepCreature(1);
    return true;
}

bool SocialWindow::onLinkClicked(const CEGUI::EventArgs& e)
{
    const CEGUI::WindowEventArgs& args = static_cast<const CEGUI::WindowEventArgs&>(e);
    if(args.window->isUserStringDefined("Creature"))
        selectCreature(std::string(args.window->getUserString("Creature").c_str()), Page::Profile);
    return true;
}

bool SocialWindow::onListScrolled(const CEGUI::EventArgs& /*e*/)
{
    if(!mUpdatingRows)
        refreshListRows();
    return true;
}

bool SocialWindow::onFeedScrolled(const CEGUI::EventArgs& /*e*/)
{
    if(!mUpdatingRows)
        rebuildFeed();
    return true;
}

bool SocialWindow::onListWheel(const CEGUI::EventArgs& e)
{
    const CEGUI::MouseEventArgs& args = static_cast<const CEGUI::MouseEventArgs&>(e);
    CEGUI::Scrollbar* bar = static_cast<CEGUI::Scrollbar*>(mWindow->getChild("HomePage/ListScroll"));
    if(!bar->isVisible())
        return false;

    bar->setScrollPosition(bar->getScrollPosition() - args.wheelChange);
    return true;
}

bool SocialWindow::onFeedWheel(const CEGUI::EventArgs& e)
{
    const CEGUI::MouseEventArgs& args = static_cast<const CEGUI::MouseEventArgs&>(e);
    CEGUI::Window* page = mWindow->getChild(mPage == Page::Home ? "HomePage" : "FeedPage");
    CEGUI::Scrollbar* bar = static_cast<CEGUI::Scrollbar*>(page->getChild("FeedScroll"));
    if(!bar->isVisible())
        return false;

    bar->setScrollPosition(bar->getScrollPosition() - args.wheelChange);
    return true;
}

void SocialWindow::selectCreature(const std::string& creatureName, Page page)
{
    if((mFilter != CreatureFilter::All) &&
       (std::find(mListedCreatures.begin(), mListedCreatures.end(), creatureName) == mListedCreatures.end()))
    {
        mFilter = CreatureFilter::All;
    }
    mSelectedCreature = creatureName;
    rebuildCreatureList();
    if(!mSelectedCreature.empty())
        showPage(page);
}

void SocialWindow::stepCreature(int direction)
{
    if(mListedCreatures.empty())
        return;

    const std::size_t count = mListedCreatures.size();
    std::vector<std::string>::const_iterator it = std::find(mListedCreatures.cbegin(), mListedCreatures.cend(),
        mSelectedCreature);
    std::size_t index = 0;
    if(it != mListedCreatures.cend())
        index = (static_cast<std::size_t>(it - mListedCreatures.cbegin()) + count + (direction < 0 ? count - 1 : 1)) % count;
    mSelectedCreature = mListedCreatures[index];
    refreshListRows();
    showPage(mPage);
}

void SocialWindow::showPage(Page page)
{
    // Right after opening, the server roster is still on its way; the page of the creature is filled when it arrives
    const bool waitingForRoster = !mSelectedCreature.empty() && !useLocalCreatureRoster() &&
        !social::PostLog::getSingleton().isDungeonbookRosterReady();
    if(page != Page::Home && findEntry(mSelectedCreature) == nullptr && !waitingForRoster)
        page = Page::Home;
    mPage = page;
    const char* const pageNames[] = {"HomePage", "FeedPage", "ProfilePage", "ValuesPage", "InventoryPage"};
    const Page pages[] = {Page::Home, Page::Feed, Page::Profile, Page::Values, Page::Inventory};
    for(std::size_t i = 0; i < 5; ++i)
        mWindow->getChild(pageNames[i])->setVisible(pages[i] == page);
    mWindow->getChild("Header")->setVisible(page != Page::Home);
    // The start page is the feed of all creatures, so its feed button is the active one there
    const Page navPages[] = {Page::Feed, Page::Profile, Page::Values, Page::Inventory};
    for(std::size_t i = 0; i < 4; ++i)
    {
        const bool active = (navPages[i] == page) || (page == Page::Home && i == 0);
        setNavState(mWindow->getChild(std::string("NavBar/") + NAV_BUTTONS[i]), active);
        mWindow->getChild(std::string("NavBar/") + NAV_BUTTONS[i])->setEnabled(
            i == 0 || !mSelectedCreature.empty() || !mListedCreatures.empty());
    }
    if(page == Page::Home)
        refreshListRows();
    if(page == Page::Home || page == Page::Feed)
        rebuildFeed();
    refreshPage();
}

const social::DungeonbookEntry* SocialWindow::findEntry(const std::string& creatureName) const
{
    if(creatureName.empty())
        return nullptr;

    for(const social::DungeonbookEntry& entry : mEntries)
    {
        if(entry.name == creatureName)
            return &entry;
    }
    return nullptr;
}

const CEGUI::Image* SocialWindow::findPortrait(const std::string& creatureName, const std::string& className,
    bool worker, bool circular) const
{
    // The roster carries the appearance of every listed creature; a creature that left it may still be known here
    std::string token;
    const social::DungeonbookEntry* entry = findEntry(creatureName);
    if(entry != nullptr)
        token = entry->appearance;
    else
    {
        Creature* creature = mGameMap.getCreature(creatureName);
        if(creature != nullptr)
            token = CreatureAppearanceLogic::toToken(creature->getAppearance());
    }
    CreatureAppearance appearance;
    const CEGUI::Image* image = nullptr;
    if(!token.empty() && CreatureAppearanceLogic::fromToken(token, appearance))
        image = circular ? getCircularCreatureAppearanceImage(creatureName, appearance) :
            getCreatureAppearanceImage(creatureName, appearance);
    if(image != nullptr)
        return image;

    const CreatureDefinition* definition = mGameMap.getClassDescription(className);
    if(definition == nullptr)
        return nullptr;
    const social::CreatureProfile& profile = social::SocialProfileCache::getSingleton().getProfile(creatureName,
        className, worker);
    // The book never shows the square preview portrait of the creature bar; its fallback is the round tinted one
    return &getCircularCreatureProfilePortraitImage(creatureName, definition->getMeshName(), profile.mGender);
}

const CEGUI::Image* SocialWindow::findPostPicture(const social::Post& post) const
{
    const std::string name = postPictureName(post);
    CEGUI::ImageManager& images = CEGUI::ImageManager::getSingleton();
    if(!name.empty() && images.isDefined("OpenDungeonsIcons/" + name))
        return &images.get("OpenDungeonsIcons/" + name);
    // Every post has a picture: without a room or a thing it is the portrait of the creature
    return findPortrait(post.mCreature, post.mClassName, post.mIsWorker, false);
}

void SocialWindow::describeMood(const social::DungeonbookEntry& entry, std::string& text, std::string& icon) const
{
    // The own creatures carry their mood level on this side; for the others only the unhappy mark of the roster is known
    Creature* creature = mGameMap.getCreature(entry.name);
    const CreatureMoodLevel level = creature == nullptr ? CreatureMoodLevel::Unknown : creature->getMoodValue();
    const uint32_t bits = creature == nullptr ? 0 : creature->getOverlayMoodValue();
    icon = "DungeonbookIcons/MoodUnhappy";
    if((bits & CreatureMoodValues::Hungry) != 0)
        text = "Hungry";
    else if((bits & CreatureMoodValues::Tired) != 0)
        text = "Tired";
    else if(level == CreatureMoodLevel::Happy)
    {
        text = "Happy";
        icon = "DungeonbookIcons/MoodHappy";
    }
    else if(level == CreatureMoodLevel::Neutral)
    {
        text = "Neutral";
        icon = "DungeonbookIcons/MoodNeutral";
    }
    else if(level == CreatureMoodLevel::Upset)
        text = "Upset";
    else if(level == CreatureMoodLevel::Angry)
        text = "Angry";
    else if(level == CreatureMoodLevel::Furious)
        text = "Furious";
    else if(entry.unhappy)
        text = "Unhappy";
    else
    {
        text = "Content";
        icon = "DungeonbookIcons/MoodHappy";
    }
}

//! \brief Lists the server roster of own and allied creatures (or the locally known ones) with the active filter.
void SocialWindow::rebuildCreatureList()
{
    mShownRosterVersion = social::PostLog::getSingleton().getRosterVersion();
    const bool localRoster = useLocalCreatureRoster();
    mEntries.clear();
    if(localRoster)
    {
        Player* localPlayer = mGameMap.getLocalPlayer();
        if(localPlayer != nullptr && localPlayer->getSeat() != nullptr)
        {
            for(Seat* seat : mGameMap.getSeats())
            {
                if(seat == nullptr || seat->getPlayer() == nullptr || !localPlayer->getSeat()->isAlliedSeat(seat))
                    continue;
                for(Creature* creature : mGameMap.getCreaturesBySeat(seat))
                {
                    social::DungeonbookEntry entry{};
                    entry.name = creature->getName();
                    entry.className = creature->getDefinition()->getClassName();
                    entry.keeper = seat->getPlayer()->getNick();
                    entry.appearance = CreatureAppearanceLogic::toToken(creature->getAppearance());
                    entry.level = creature->getLevel();
                    entry.worker = creature->getDefinition()->isWorker();
                    entry.champion = creature->getDefinition()->isChampion();
                    entry.unhappy = (creature->getOverlayMoodValue() &
                        (CreatureMoodValues::Hungry | CreatureMoodValues::Tired)) != 0 ||
                        static_cast<int32_t>(creature->getMoodValue()) >= static_cast<int32_t>(CreatureMoodLevel::Upset);
                    mEntries.push_back(entry);
                }
            }
        }
    }
    else
        mEntries = social::PostLog::getSingleton().getDungeonbookRoster();

    social::SocialProfileCache& cache = social::SocialProfileCache::getSingleton();
    std::vector<std::pair<std::string, std::string> > sorted;
    for(const social::DungeonbookEntry& creature : mEntries)
    {
        if((mFilter == CreatureFilter::Workers) && !creature.worker)
            continue;
        if((mFilter == CreatureFilter::Fighters) && creature.worker)
            continue;
        if((mFilter == CreatureFilter::Unhappy) && !creature.unhappy)
            continue;
        const social::CreatureProfile& profile = cache.getProfile(creature.name, creature.className, creature.worker);
        sorted.push_back(std::make_pair(creature.className + "|" + profile.getFullName() + "|" + creature.name,
            creature.name));
    }
    std::sort(sorted.begin(), sorted.end(), isEntryBefore);
    mListedCreatures.clear();
    for(const std::pair<std::string, std::string>& entry : sorted)
        mListedCreatures.push_back(entry.second);

    // A creature that left the roster (it died or changed sides) cannot be shown any more
    if(findEntry(mSelectedCreature) == nullptr && (localRoster || social::PostLog::getSingleton().isDungeonbookRosterReady()))
        mSelectedCreature.clear();

    CEGUI::Window* home = mWindow->getChild("HomePage");
    for(std::size_t i = 0; i < 4; ++i)
    {
        const CreatureFilter filters[] = {CreatureFilter::All, CreatureFilter::Workers, CreatureFilter::Fighters,
            CreatureFilter::Unhappy};
        setTabState(home->getChild(FILTER_BUTTONS[i]), FILTER_LABELS[i], filters[i] == mFilter);
    }
    std::ostringstream label;
    label << (localRoster ? "Known creatures (" : "Creatures (") << mListedCreatures.size();
    if(mListedCreatures.size() != mEntries.size())
        label << " of " << mEntries.size();
    label << ")";
    setElidedText(home->getChild("CreaturesLabel"), label.str());
    home->getChild("ListRows")->setTooltipText(localRoster ?
        "Only locally known creatures are shown; detailed server statistics are unavailable." :
        "Click a creature to see its pages.");

    refreshListRows();
    if(mPage != Page::Home && mSelectedCreature.empty())
        showPage(Page::Home);
    else if(mPage != Page::Home)
        refreshPage();
    // The levels in the feed come from the roster
    rebuildFeed();
}

void SocialWindow::refreshListRows()
{
    CEGUI::Window* home = mWindow->getChild("HomePage");
    mUpdatingRows = true;
    const std::size_t first = setupRowScroll(static_cast<CEGUI::Scrollbar*>(home->getChild("ListScroll")),
        mListedCreatures.size(), LIST_ROWS);
    mUpdatingRows = false;
    social::SocialProfileCache& cache = social::SocialProfileCache::getSingleton();
    for(std::size_t i = 0; i < LIST_ROWS; ++i)
    {
        CEGUI::Window* row = home->getChild("ListRows/Row" + std::to_string(i));
        const std::size_t index = first + i;
        const social::DungeonbookEntry* entry = index < mListedCreatures.size() ? findEntry(mListedCreatures[index]) : nullptr;
        row->setVisible(entry != nullptr);
        if(entry == nullptr)
            continue;

        const social::CreatureProfile& profile = cache.getProfile(entry->name, entry->className, entry->worker);
        row->getChild("Highlight")->setVisible(entry->name == mSelectedCreature);
        setImage(row->getChild("Portrait"), findPortrait(entry->name, entry->className, entry->worker, false));
        setElidedText(row->getChild("Name"), profile.getFullName());
        // The champion shows a crown instead of its level
        row->getChild("Level")->setText(entry->champion ? CHAMPION_CROWN_MARKUP : "Lv. " + std::to_string(entry->level));
        std::string mood;
        std::string icon;
        describeMood(*entry, mood, icon);
        row->getChild("MoodIcon")->setProperty("Image", icon);
        setElidedText(row->getChild("Mood"), mood);
        row->getChild("Button")->setTooltipText(profile.getFullName() + " (" +
            social::SocialGenerator::displayClassName(cache.getData(), entry->className) + "), keeper " + entry->keeper);
    }
}

//! \brief Fills the rows of the feed of the shown page from the scroll position on.
void SocialWindow::rebuildFeed()
{
    social::PostLog& log = social::PostLog::getSingleton();
    mShownPostVersion = log.getVersion();
    mSinceFeedRebuild = 0.0f;
    if(mPage != Page::Home && mPage != Page::Feed)
        return;

    const bool all = (mPage == Page::Home);
    CEGUI::Window* page = mWindow->getChild(all ? "HomePage" : "FeedPage");
    std::vector<const social::Post*> posts;
    const std::deque<social::Post>& allPosts = log.getPosts();
    for(std::deque<social::Post>::const_reverse_iterator it = allPosts.rbegin();
        (it != allPosts.rend()) && (posts.size() < MAX_FEED_ROWS); ++it)
    {
        if(!all && (it->mCreature != mSelectedCreature))
            continue;
        if(renderPostTextForLog(*it).empty())
            continue;
        posts.push_back(&*it);
    }

    mUpdatingRows = true;
    const std::size_t first = setupRowScroll(static_cast<CEGUI::Scrollbar*>(page->getChild("FeedScroll")),
        posts.size(), FEED_ROWS);
    mUpdatingRows = false;
    social::SocialProfileCache& cache = social::SocialProfileCache::getSingleton();
    const int64_t turnNow = mGameMap.getTurnNumber();
    for(std::size_t i = 0; i < FEED_ROWS; ++i)
    {
        CEGUI::Window* row = page->getChild("FeedRows/Row" + std::to_string(i));
        const std::size_t index = first + i;
        row->setVisible(index < posts.size());
        if(index >= posts.size())
            continue;

        const social::Post& post = *posts[index];
        const social::CreatureProfile& profile = cache.getProfile(post.mCreature, post.mClassName, post.mIsWorker);
        const std::string text = renderPostText(post, profile);
        setImage(row->getChild("Portrait"), findPortrait(post.mCreature, post.mClassName, post.mIsWorker, false));
        // Name, then the level of a listed creature (the crown for the champion) and the age of the post
        const social::DungeonbookEntry* entry = findEntry(post.mCreature);
        std::string level;
        if(entry != nullptr)
            level = (entry->champion ? std::string(CHAMPION_CROWN_MARKUP) : "Lv. " + std::to_string(entry->level)) + " - ";
        const std::string age = formatAge(turnNow - post.mTurn);
        // The name gives way to level and age; the crown is about as wide as two letters
        CEGUI::Window* head = row->getChild("Head");
        const std::string plainMeta = "   " + (entry == nullptr ? std::string() :
            (entry->champion ? std::string("WW - ") : level)) + age;
        const float nameWidth = head->getPixelSize().d_width -
            (head->getFont() == nullptr ? 0.0f : head->getFont()->getTextExtent(plainMeta));
        head->setText(std::string(FEED_NAME_COLOUR) + escapeMarkup(elideToWidth(head->getFont(), profile.getFullName(),
            std::max(0.0f, nameWidth))) + FEED_TIME_COLOUR + "   " + level + age);
        CEGUI::Window* textWindow = row->getChild("Text");
        fitTextToWindow(textWindow, FEED_TEXT_COLOUR, text);
        textWindow->setTooltipText(text);
        // The game picture of the post below its text
        CEGUI::Window* picture = row->getChild("Picture");
        setImage(picture->getChild("Image"), findPostPicture(post));
        picture->setTooltipText(text);
    }
    CEGUI::Window* empty = page->getChild("FeedEmpty");
    empty->setVisible(posts.empty());
    empty->setText(all ? "Quiet in the dungeon. Somewhere, a kobold is shovelling." : "Nothing posted yet.");
}

void SocialWindow::refreshPage()
{
    social::PostLog& log = social::PostLog::getSingleton();
    mShownProfilePostVersion = log.getVersion();
    mSinceProfileRefresh = 0.0f;
    const social::DungeonbookEntry* entry = findEntry(mSelectedCreature);
    if(mPage == Page::Home || entry == nullptr)
        return;

    // The feed of the creature is filled by rebuildFeed(), like the feed of the start page
    refreshHeader(*entry);
    if(mPage == Page::Profile)
        refreshProfile(*entry);
    else if(mPage == Page::Values)
        refreshValues(*entry);
    else if(mPage == Page::Inventory)
        refreshInventory(*entry);
}

void SocialWindow::refreshHeader(const social::DungeonbookEntry& entry)
{
    social::SocialProfileCache& cache = social::SocialProfileCache::getSingleton();
    const social::CreatureProfile& profile = cache.getProfile(entry.name, entry.className, entry.worker);
    CEGUI::Window* header = mWindow->getChild("Header");
    setElidedText(header->getChild("NameText"), profile.getFullName());
    // The arrows switch through the list as it is filtered; with a single creature there is nothing to switch to
    const bool canSwitch = mListedCreatures.size() > 1;
    header->getChild("PrevButton")->setEnabled(canSwitch);
    header->getChild("NextButton")->setEnabled(canSwitch);
}

//! \brief Fills the profile page: portrait, name, keeper, class and mood, the social rows and the recent posts.
void SocialWindow::refreshProfile(const social::DungeonbookEntry& entry)
{
    CEGUI::Window* page = mWindow->getChild("ProfilePage");
    social::SocialProfileCache& cache = social::SocialProfileCache::getSingleton();
    const social::CreatureProfile& profile = cache.getProfile(entry.name, entry.className, entry.worker);
    setImage(page->getChild("Portrait/Clip/Image"), findPortrait(entry.name, entry.className, entry.worker, false));
    setElidedText(page->getChild("NameText"), profile.getFullName());
    setElidedText(page->getChild("KeeperText"), "Keeper: " + entry.keeper);
    std::string mood;
    std::string icon;
    describeMood(entry, mood, icon);
    page->getChild("InfoText")->setText(escapeMarkup(social::SocialGenerator::displayClassName(cache.getData(),
        entry.className)) + " - " + (entry.worker ? "Worker" : "Fighter") + "\n" +
        (entry.champion ? std::string("Champion ") + CHAMPION_CROWN_MARKUP : "Level " + std::to_string(entry.level)) +
        "\nMood: " + mood);

    // With the creature known here the shared social profile shows the real relationships, friends and status
    Creature* creature = mGameMap.getCreature(entry.name);
    CEGUI::Window* holder = page->getChild("SocialHolder");
    CEGUI::Window* fallback = page->getChild("SocialText");
    holder->setVisible(creature != nullptr);
    fallback->setVisible(creature == nullptr);
    if(creature != nullptr)
    {
        if(mProfilePage == nullptr)
        {
            Gui& gui = ODFrameListener::getSingleton().getModeManager()->getGui();
            mProfilePage = gui.createCreatureProfilePage(holder);
            // Portrait, name and items have their own places in the book, the shared page shows the social rows only
            const char* const hidden[] = {"Portrait", "NameText", "AttributesText", "EquipmentText", "EquipmentRow",
                "OwnPostsText"};
            for(const char* name : hidden)
                mProfilePage->getChild(name)->setVisible(false);
            // The names in the friends and foe rows select that creature
            const char* const linkNames[] = {"FriendLink0", "FriendLink1", "FoeLink"};
            for(const char* linkName : linkNames)
            {
                connect(mProfilePage->getChild(linkName), CEGUI::PushButton::EventClicked,
                    CEGUI::Event::Subscriber(&SocialWindow::onLinkClicked, this));
            }
        }
        // A newly selected creature opens on its first rows, while timed refreshes keep the scroll position.
        if(!mProfilePage->isUserStringDefined("ProfileCreature") ||
            mProfilePage->getUserString("ProfileCreature") != mSelectedCreature)
        {
            static_cast<CEGUI::Scrollbar*>(mProfilePage->getChild("ProfileScrollbar"))->setScrollPosition(0);
            mProfilePage->setUserString("ProfileCreature", mSelectedCreature);
        }
        // The same code fills the creature card
        creature->fillProfilePage(mProfilePage);
    }
    else
    {
        // Out of sight the profile still comes from the name, with the path and skills of the roster
        std::vector<std::string> likes;
        std::vector<std::string> dislikes;
        for(std::size_t i = 0; i < 2; ++i)
        {
            if(!profile.mLikes[i].empty())
                likes.push_back(profile.mLikes[i]);
            if(!profile.mDislikes[i].empty())
                dislikes.push_back(profile.mDislikes[i]);
        }
        std::string text = "Age: " + profile.mAgeText + (profile.mGender.empty() ? "" : " - " + profile.mGender) +
            "\nRelationship: " + profile.mRelationship + "\nFrom: " + profile.mHometown + "\nJob: " + profile.mJob +
            "\nPath: " + entry.path + "\nSkills: " + entry.skills + "\nLikes: ";
        for(std::size_t i = 0; i < likes.size(); ++i)
            text += (i > 0 ? ", " : "") + likes[i];
        text += "\nDislikes: ";
        for(std::size_t i = 0; i < dislikes.size(); ++i)
            text += (i > 0 ? ", " : "") + dislikes[i];
        text += "\n\n\"" + profile.mBio + "\"";
        fallback->setText(escapeMarkup(text));
    }

    // The posts of the creature: their number and the pictures of the newest ones, the text in the tooltip
    social::PostLog& log = social::PostLog::getSingleton();
    const int64_t turnNow = mGameMap.getTurnNumber();
    std::size_t count = 0;
    std::size_t rows = 0;
    const std::deque<social::Post>& allPosts = log.getPosts();
    for(std::deque<social::Post>::const_reverse_iterator it = allPosts.rbegin(); it != allPosts.rend(); ++it)
    {
        if(it->mCreature != mSelectedCreature)
            continue;

        const std::string text = renderPostText(*it, cache.getProfile(it->mCreature, it->mClassName, it->mIsWorker));
        if(text.empty())
            continue;

        ++count;
        if(rows < MAX_OWN_POSTS)
        {
            CEGUI::Window* thumb = page->getChild("PostThumb" + std::to_string(rows));
            thumb->setVisible(true);
            setImage(thumb->getChild("Image"), findPostPicture(*it));
            thumb->setTooltipText(text + "  (" + formatAge(turnNow - it->mTurn) + ")");
            ++rows;
        }
    }
    for(std::size_t i = rows; i < MAX_OWN_POSTS; ++i)
        page->getChild("PostThumb" + std::to_string(i))->setVisible(false);
    page->getChild("PostsTitle")->setText("Posts (" + std::to_string(count) + ")");
    CEGUI::Window* empty = page->getChild("PostsEmpty");
    empty->setVisible(rows == 0);
    empty->setText(std::string(FEED_TEXT_COLOUR) + "Nothing posted yet.");
}

//! \brief Fills the values sheet: the statistics column, the portrait ring, the attributes, the combat and defense
//! blocks and the equipment, path and skills tiles. Without server values (replays, older peers) they show "-".
void SocialWindow::refreshValues(const social::DungeonbookEntry& entry)
{
    CEGUI::Window* page = mWindow->getChild("ValuesPage");
    const bool known = !useLocalCreatureRoster();
    setImage(page->getChild("Portrait/Image"), findPortrait(entry.name, entry.className, entry.worker, true));

    // The column of the former statistics page: window, label in the statistics text, how the value is shown
    struct StatisticsLine { const char* window; const char* label; bool slots; };
    const StatisticsLine lines[] = {
        {"Experience", "Experience", false}, {"HitPoints", "HP", false}, {"Gold", "Gold", false},
        {"SightRadius", "Sight radius", false}, {"Potions", "Potions", true}, {"Inventory", "Inventory", true},
        {"DamagePerSecond", "Raw damage per second", false}, {"SkillPoints", "Skill points earned / spent", false}};
    for(const StatisticsLine& line : lines)
    {
        const std::string value = known ? findStatisticsValue(entry.stats, line.label) : std::string();
        CEGUI::Window* valueWindow = page->getChild(std::string(line.window) + "Value");
        setElidedText(valueWindow, line.slots ? countFilledSlots(value) : formatStatisticsNumbers(value));
        // The item names of the potion and inventory slots and the meaning of the skill points stay readable
        std::string tooltip = value;
        if(std::string(line.window) == "SkillPoints" && !value.empty())
            tooltip = "Skill points earned / spent: " + value;
        valueWindow->setTooltipText(tooltip);
        page->getChild(std::string(line.window) + "Label")->setTooltipText(tooltip);
    }

    const char* names[] = {"Strength", "Dexterity", "Life", "Mana"};
    const double values[] = {entry.strength, entry.dexterity, entry.life, entry.mana};
    for(std::size_t i = 0; i < 4; ++i)
    {
        std::ostringstream text;
        text << names[i] << "\n" << (known ? formatProfileValue(values[i]) : std::string("-"));
        page->getChild(names[i])->setText(text.str());
    }
    // The labels are fixed in the layout; the value column holds one line per label, right aligned.
    std::ostringstream combat;
    std::ostringstream defense;
    if(known)
    {
        combat << formatProfileValue(entry.critical) << " %\n" << formatProfileValue(entry.attackRating) << "\n"
            << formatProfileValue(entry.defenseRating);
        defense << formatProfileValue(entry.physicalDefense) << "\n" << formatProfileValue(entry.magicalDefense) << "\n"
            << formatProfileValue(entry.elementDefense);
    }
    else
    {
        combat << "-\n-\n-";
        defense << "-\n-\n-";
    }
    page->getChild("CombatValues")->setText(combat.str());
    page->getChild("DefenseValues")->setText(defense.str());

    const char* const tiles[] = {"Equipment", "Path", "Skills"};
    const std::string tileValues[] = {entry.equipment, entry.path, entry.skills};
    for(std::size_t i = 0; i < 3; ++i)
    {
        const std::string value = (known && !tileValues[i].empty()) ? tileValues[i] : std::string("-");
        CEGUI::Window* tile = page->getChild(std::string(tiles[i]) + "Value");
        fitTextToWindow(tile, FEED_TEXT_COLOUR, value);
        tile->setTooltipText(value);
    }
}

//! \brief Fills the 13 slots of the inventory page with the items the creature shows to the local player.
void SocialWindow::refreshInventory(const social::DungeonbookEntry& entry)
{
    CEGUI::Window* page = mWindow->getChild("InventoryPage");
    setImage(page->getChild("Portrait/Clip/Image"), findPortrait(entry.name, entry.className, entry.worker, false));
    std::vector<CEGUI::Window*> slots;
    for(std::size_t slot = 0; slot < ITEM_SLOTS; ++slot)
        slots.push_back(page->getChild("SlotBox" + std::to_string(slot) + "/Slot" + std::to_string(slot)));
    Creature* creature = mGameMap.getCreature(entry.name);
    Creature::fillItemSlotWindows(creature, slots, true);

    std::string hint;
    if(creature == nullptr)
        hint = "This creature is out of sight; its items are not known here.";
    else if(mGameMap.getLocalPlayer() == nullptr || creature->getSeat() != mGameMap.getLocalPlayer()->getSeat())
        hint = "Only the hands of a creature of another keeper can be seen.";
    page->getChild("HintText")->setText(hint);
}
