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
#include "game/Player.h"
#include "gamemap/GameMap.h"
#include "social/CreaturePosts.h"
#include "social/PostLog.h"
#include "social/SocialGenerator.h"
#include "social/SocialProfileCache.h"
#include "ODApplication.h"

#include <CEGUI/widgets/Listbox.h>
#include <CEGUI/widgets/ListboxTextItem.h>
#include <CEGUI/widgets/Scrollbar.h>
#include <CEGUI/Window.h>

#include <algorithm>
#include <deque>
#include <sstream>

namespace
{
//! Number of posts shown in the feed at most
const std::size_t MAX_FEED_ROWS = 25;
//! The window checks for changes at most this often (real seconds), so at most 4 redraws per second
const float REFRESH_CHECK_INTERVAL = 0.25f;
//! The relative times of the feed are refreshed at least this often while the window is open
const float FEED_TIME_REFRESH_INTERVAL = 5.0f;

const char* const FEED_NAME_COLOUR = "[colour='FFF2C860']";
const char* const FEED_TIME_COLOUR = "[colour='FFB8AC90']";
const char* const FEED_TEXT_COLOUR = "[colour='FFE8DCC0']";

struct CreatureListEntry
{
    std::string mSortKey;
    std::string mText;
    std::string mName;
};

bool isEntryBefore(const CreatureListEntry& a, const CreatureListEntry& b)
{
    return a.mSortKey < b.mSortKey;
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
    if(seconds < 10.0)
        stream << "just now";
    else if(seconds < 60.0)
        stream << static_cast<int32_t>(seconds) << " sec ago";
    else if(seconds < 3600.0)
        stream << static_cast<int32_t>(seconds / 60.0) << " min ago";
    else
        stream << static_cast<int32_t>(seconds / 3600.0) << " h ago";
    return stream.str();
}

bool isUnhappy(const Creature& creature)
{
    uint32_t bits = creature.getOverlayMoodValue();
    if((bits & (CreatureMoodValues::Hungry | CreatureMoodValues::Tired)) != 0)
        return true;

    return static_cast<int32_t>(creature.getMoodValue()) >= static_cast<int32_t>(CreatureMoodLevel::Upset);
}

//! \brief The text of a post, empty if its category has no template
std::string renderPostText(const social::Post& post, const social::CreatureProfile& profile)
{
    social::SocialProfileCache& cache = social::SocialProfileCache::getSingleton();
    int32_t level = 0;
    std::string room;
    if((post.mCategory == social::PostCategory::LevelUp) || (post.mCategory == social::PostCategory::Payday))
        level = post.mArgument;
    else if((post.mCategory == social::PostCategory::Work) || (post.mCategory == social::PostCategory::Train))
        room = social::CreaturePosts::getRoomName(post.mArgument);

    return social::SocialGenerator::renderPost(cache.getData(), profile, post.mIsWorker,
        social::getPostCategoryName(post.mCategory), post.mVariant, level, room);
}

//! \brief One entry of the feed: name and age on the first line, the text below
std::string renderFeedEntry(const social::Post& post, int64_t turnNow)
{
    social::SocialProfileCache& cache = social::SocialProfileCache::getSingleton();
    const social::CreatureProfile& profile = cache.getProfile(post.mCreature, post.mClassName, post.mIsWorker);
    std::string text = renderPostText(post, profile);
    if(text.empty())
        return text;

    std::string entry = std::string(FEED_NAME_COLOUR) + escapeMarkup(profile.getFullName()) + FEED_TIME_COLOUR +
        "   " + formatAge(turnNow - post.mTurn) + "\n" + FEED_TEXT_COLOUR + escapeMarkup(text) + "\n\n";
    return entry;
}
}

SocialWindow::SocialWindow(CEGUI::Window* rootWindow, GameMap& gameMap) :
    mGameMap(gameMap),
    mWindow(rootWindow->getChild("SocialWindow")),
    mFilter(CreatureFilter::All),
    mSelectedOnly(false),
    mRebuildingList(false),
    mShownRosterVersion(0),
    mShownPostVersion(0),
    mSinceRefreshCheck(0.0f),
    mSinceFeedRebuild(0.0f)
{
}

bool SocialWindow::isVisible() const
{
    return mWindow->isVisible();
}

void SocialWindow::show()
{
    mWindow->show();
    mWindow->moveToFront();
    rebuildCreatureList();
    rebuildFeed();
    mSinceRefreshCheck = 0.0f;
}

void SocialWindow::showCreature(const std::string& creatureName)
{
    mFilter = CreatureFilter::All;
    mWindow->getChild("FilterButton")->setText("Show: all creatures");
    mSelectedCreature = creatureName;
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

void SocialWindow::hide()
{
    mWindow->hide();
}

void SocialWindow::update(float elapsed)
{
    if(!mWindow->isVisible())
        return;

    mSinceRefreshCheck += elapsed;
    mSinceFeedRebuild += elapsed;
    if(mSinceRefreshCheck < REFRESH_CHECK_INTERVAL)
        return;

    mSinceRefreshCheck = 0.0f;
    social::PostLog& log = social::PostLog::getSingleton();
    if(log.getRosterVersion() != mShownRosterVersion)
        rebuildCreatureList();
    if((log.getVersion() != mShownPostVersion) || (mSinceFeedRebuild >= FEED_TIME_REFRESH_INTERVAL))
        rebuildFeed();
}

bool SocialWindow::onCloseClicked(const CEGUI::EventArgs& /*e*/)
{
    hide();
    return true;
}

bool SocialWindow::onFilterClicked(const CEGUI::EventArgs& /*e*/)
{
    const char* label = "Show: all creatures";
    switch(mFilter)
    {
        case CreatureFilter::All:
            mFilter = CreatureFilter::Workers;
            label = "Show: workers";
            break;
        case CreatureFilter::Workers:
            mFilter = CreatureFilter::Fighters;
            label = "Show: fighters";
            break;
        case CreatureFilter::Fighters:
            mFilter = CreatureFilter::Unhappy;
            label = "Show: unhappy creatures";
            break;
        default:
            mFilter = CreatureFilter::All;
            break;
    }
    mWindow->getChild("FilterButton")->setText(label);
    rebuildCreatureList();
    return true;
}

bool SocialWindow::onFeedModeClicked(const CEGUI::EventArgs& /*e*/)
{
    mSelectedOnly = !mSelectedOnly;
    mWindow->getChild("FeedModeButton")->setText(mSelectedOnly ? "Posts of: selected creature" : "Posts of: everyone");
    rebuildFeed();
    return true;
}

bool SocialWindow::onSelectionChanged(const CEGUI::EventArgs& /*e*/)
{
    if(mRebuildingList)
        return true;

    CEGUI::Listbox* list = static_cast<CEGUI::Listbox*>(mWindow->getChild("CreatureList"));
    CEGUI::ListboxItem* selected = list->getFirstSelectedItem();
    if((selected != nullptr) && (selected->getID() < mListedCreatures.size()))
        mSelectedCreature = mListedCreatures[selected->getID()];
    else
        mSelectedCreature.clear();

    updateButtons();
    if(mSelectedOnly)
        rebuildFeed();
    return true;
}

bool SocialWindow::onOpenProfileClicked(const CEGUI::EventArgs& /*e*/)
{
    if(mSelectedCreature.empty())
        return true;

    Creature* creature = mGameMap.getCreature(mSelectedCreature);
    if(creature != nullptr)
        creature->createStatsWindow();
    return true;
}

void SocialWindow::updateButtons()
{
    mWindow->getChild("OpenProfileButton")->setEnabled(!mSelectedCreature.empty());
}

void SocialWindow::rebuildCreatureList()
{
    CEGUI::Listbox* list = static_cast<CEGUI::Listbox*>(mWindow->getChild("CreatureList"));
    mShownRosterVersion = social::PostLog::getSingleton().getRosterVersion();

    std::vector<CreatureListEntry> entries;
    Player* localPlayer = mGameMap.getLocalPlayer();
    std::size_t total = 0;
    if(localPlayer != nullptr)
    {
        social::SocialProfileCache& cache = social::SocialProfileCache::getSingleton();
        std::vector<Creature*> creatures = mGameMap.getCreaturesBySeat(localPlayer->getSeat());
        total = creatures.size();
        for(Creature* creature : creatures)
        {
            bool isWorker = creature->getDefinition()->isWorker();
            if((mFilter == CreatureFilter::Workers) && !isWorker)
                continue;
            if((mFilter == CreatureFilter::Fighters) && isWorker)
                continue;
            if((mFilter == CreatureFilter::Unhappy) && !isUnhappy(*creature))
                continue;

            const std::string& className = creature->getDefinition()->getClassName();
            const social::CreatureProfile& profile = cache.getProfile(creature->getName(), className, isWorker);
            std::ostringstream text;
            text << profile.getFullName() << " (" << social::SocialGenerator::displayClassName(cache.getData(), className) <<
                ")  L" << creature->getLevel();

            CreatureListEntry entry;
            entry.mSortKey = className + "|" + profile.getFullName() + "|" + creature->getName();
            entry.mText = text.str();
            entry.mName = creature->getName();
            entries.push_back(entry);
        }
    }
    std::sort(entries.begin(), entries.end(), isEntryBefore);

    mRebuildingList = true;
    float scroll = list->getVertScrollbar()->getScrollPosition();
    list->resetList();
    mListedCreatures.clear();
    bool selectionFound = false;
    for(std::size_t i = 0; i < entries.size(); ++i)
    {
        mListedCreatures.push_back(entries[i].mName);
        CEGUI::ListboxTextItem* item = new CEGUI::ListboxTextItem(entries[i].mText, static_cast<CEGUI::uint>(i));
        item->setTextParsingEnabled(false);
        item->setSelectionBrushImage("OpenDungeonsSkin/SelectionBrush");
        list->addItem(item);
        if(entries[i].mName == mSelectedCreature)
        {
            list->setItemSelectState(item, true);
            selectionFound = true;
        }
    }
    list->getVertScrollbar()->setScrollPosition(scroll);
    mRebuildingList = false;

    if(!selectionFound)
        mSelectedCreature.clear();
    updateButtons();

    std::ostringstream label;
    label << "Creatures (" << entries.size();
    if(entries.size() != total)
        label << " of " << total;
    label << ")";
    mWindow->getChild("CreaturesLabel")->setText(label.str());
}

void SocialWindow::rebuildFeed()
{
    social::PostLog& log = social::PostLog::getSingleton();
    mShownPostVersion = log.getVersion();
    mSinceFeedRebuild = 0.0f;

    std::string text;
    if(mSelectedOnly && mSelectedCreature.empty())
    {
        text = "Select a creature in the list to see its posts.";
    }
    else
    {
        int64_t turnNow = mGameMap.getTurnNumber();
        std::size_t rows = 0;
        const std::deque<social::Post>& posts = log.getPosts();
        for(std::deque<social::Post>::const_reverse_iterator it = posts.rbegin();
            (it != posts.rend()) && (rows < MAX_FEED_ROWS); ++it)
        {
            if(mSelectedOnly && (it->mCreature != mSelectedCreature))
                continue;

            std::string entry = renderFeedEntry(*it, turnNow);
            if(entry.empty())
                continue;

            text += entry;
            ++rows;
        }
        if(text.empty())
            text = "Quiet in the dungeon. Somewhere, a kobold is shovelling.";
    }
    mWindow->getChild("FeedText")->setText(text);
}
