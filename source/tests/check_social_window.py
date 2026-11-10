"""Check the Dungeonbook (social browser): window layout, HUD button, hotkey, event hooks and limits.

The window is a fixed size OD/FrameWindow imported into the game layout (so it is registered for UI
scaling like the other windows), it closes with its cross and with Escape (closeTopWindow), the
hotkey B is used only once, and the posts come only from client side events that are guarded so they
cost nothing while the feed is not running.
"""
from pathlib import Path
import re

repo = Path(__file__).resolve().parents[2]
checks = 0


def check(condition, message):
    global checks
    checks += 1
    assert condition, message


def read(path):
    return (repo / path).read_text(encoding='utf-8', errors='replace')


layout = read('gui/WindowSocial.layout')
check('name="SocialWindow"' in layout and 'type="OD/FrameWindow"' in layout, 'frame window')
check('<Property name="SizingEnabled" value="False" />' in layout, 'the window must not be resizable')
m = re.search(r'name="Area" value="\{\{0\.5,(-?\d+)\},\{0\.5,(-?\d+)\},\{0\.5,(\d+)\},\{0\.5,(\d+)\}\}"', layout)
check(m is not None, 'a fixed size centred area is expected')
width, height = int(m[3]) - int(m[1]), int(m[4]) - int(m[2])
check(width <= 1024 - 64 and height <= 768 - 120, 'the window must fit into 1024x768 with the HUD: %dx%d' % (width, height))
check('name="Visible" value="False"' in layout, 'hidden by default')
for name in ('HomePage', 'CreaturesLabel', 'Filter', 'ListRows',
             'ListScroll', 'FeedRows', 'FeedScroll', 'FeedPage', 'ProfilePage', 'SocialHolder', 'PostThumb0', 'ValuesPage',
             'InventoryPage', 'Header', 'BackButton', 'PrevButton', 'NextButton', 'NavBar', 'NavFeed', 'NavProfile',
             'NavValues', 'NavInventory'):
    check('name="%s"' % name in layout, name)
check('OpenProfileButton' not in layout, 'the profile opens in the book, not in a window')
# The start page has the list on the left and the feed of all creatures on the right, inside the shared frame client.
import xml.etree.ElementTree as ET
social_root = ET.fromstring(layout).find('Window')


def area(name):
    """Return the relative coordinates of a named social-window child."""
    window = social_root.find(".//Window[@name='%s']" % name)
    value = window.find("Property[@name='Area']").get('value')
    dims = re.findall(r'\{(-?[0-9.]+),(-?[0-9.]+)\}', value)
    check(len(dims) == 4 and all(float(offset) == 0 for _, offset in dims), name + ' scales with its client')
    return [float(scale) for scale, _ in dims]


list_area = area('ListRows')
feed = area('FeedRows')
check(feed[0] > list_area[2], 'the feed must not overlap the list')
check(area('ListScroll')[0] >= list_area[2] and area('ListScroll')[2] <= feed[0], 'the list scrollbar sits between')
# The feed column keeps the original minimum text-column width (light frame of at most 16 design pixels per side).
check((width - 2 * 16) * (feed[2] - feed[0]) >= 400, 'the feed needs about 400 design pixels')
pages = [w.get('name') for w in social_root.findall('Window')]
check(pages[:5] == ['HomePage', 'FeedPage', 'ProfilePage', 'ValuesPage', 'InventoryPage'], pages)
for page in pages[1:5] + ['Header']:
    own = social_root.find("Window[@name='%s']" % page).findall('Property')
    check(any(p.get('name') == 'Visible' and p.get('value') == 'False' for p in own),
          page + ' is hidden until a creature is opened')
filter_window = social_root.find("Window[@name='HomePage']/Window[@name='Filter']")
check(filter_window.get('type') == 'OD/Combobox', 'filter is a dropdown')
check(filter_window.find("Property[@name='ReadOnly']").get('value') == 'True', 'filter selects a fixed entry')
check(area('CreaturesLabel')[2] == area('Filter')[0], 'dropdown sits beside the roster heading')
check(not any('name="Filter%s"' % name in layout for name in ('All', 'Workers', 'Fighters', 'Unhappy')),
      'old filter buttons are replaced')
nav_areas = [area(n) for n in ('NavFeed', 'NavProfile', 'NavValues', 'NavInventory')]
check(all(abs((a[2] - a[0]) - (nav_areas[0][2] - nav_areas[0][0])) < 1e-6 for a in nav_areas), 'equal navigation widths')
check(area('NavBar')[1] >= max(area(p)[3] for p in pages[1:5]) - 1e-6,
      'the navigation bar sits below the selected creature pages')
check(area('NavBar')[0] >= area('ListPanel')[2], 'navigation leaves the persistent roster visible')
check('Area" value="{{0.5' in layout and 'UDim' not in layout, 'design pixels only')

hud = read('gui/ModeGame.layout')
check('filename="WindowSocial.layout"' in hud, 'window not imported')
button = hud[hud.index('name="SocialButton"'):]
button = button[:button.index('</Window>')]
check('{{0,148},{1,-224},{0,188},{1,-184}}' in button, 'button is not in the free slot')
check('ContextHelp' in button and 'TooltipText' in button, 'tooltip and context help')
icon = re.search(r'NormalImage" value="OpenDungeonsIcons/(\w+)"', button)
check(icon is not None and 'name="%s"' % icon[1] in read('gui/ODIcons.imageset'), 'button icon must exist')

gamemode = read('source/modes/GameMode.cpp')
check(gamemode.count('case OIS::KC_B:') == 1, 'one B case in GameMode')
for path in Path(repo / 'source').rglob('*.cpp'):
    if path.name != 'GameMode.cpp':
        check('KC_B' not in path.read_text(encoding='utf-8', errors='replace'), 'KC_B used in ' + path.name)
check('toggleSocialWindow' in gamemode and 'EventCloseClicked, CEGUI::Event::Subscriber(&SocialWindow::onCloseClicked' in gamemode,
      'button and close handler')
body = gamemode[gamemode.index('bool GameMode::toggleSocialWindow'):]
body = body[:body.index('\n}\n')]
check('closeTopWindow' in body and 'getLocalPlayer() == nullptr' in body, 'exclusive windows / no local player')
check('B opens the Dungeonbook' in gamemode, 'help text')
check('PostLog::getSingleton().start(' in gamemode and 'PostLog::getSingleton().stop()' in gamemode
      and 'SocialProfileCache::getSingleton().clear()' in gamemode, 'the feed is reset when a game starts and ends')
frame = gamemode[gamemode.index('void GameMode::onFrameStarted'):]
frame = frame[:frame.index('\n}\n')]
check('mSocialWindow->update(' in frame and 'PostLog' not in frame, 'the feed is not polled per frame')

window = read('source/render/SocialWindow.cpp')
server = read('source/network/ODServer.cpp')
check('seat->isAlliedSeat(owner)' in server and 'keeper->getNick()' in server and '"Keeper: " + entry.keeper' in window,
      'the server sends allied creatures with their keeper name')
check('row->getChild("Button")->setTooltipText(' in window and 'entry->keeper' in window,
      'full name, class and keeper remain available when the name is elided')

# Older peers and replays have no on-demand server roster; use recorded creatures and the original profile.
local_start = window.index('bool useLocalCreatureRoster()')
local_end = window.index('\n}', local_start)
local_mode = window[local_start:local_end]
check('client.isReplay()' in local_mode and '!client.supportsDungeonbookRoster()' in local_mode,
      'recorded and unsupported connections use local data')
client_header = read('source/network/ODClient.h')
check('bool isReplay() const' in client_header, 'replay state is publicly available to the view')
show = window[window.index('void SocialWindow::show()'):window.index('void SocialWindow::showCreature(')]
hide = window[window.index('void SocialWindow::hide()'):window.index('void SocialWindow::update(')]
check('!useLocalCreatureRoster()' in show and 'askDungeonbookRoster, true' in show,
      'no roster subscription is sent when it cannot be answered')
check('!useLocalCreatureRoster()' in hide and 'askDungeonbookRoster, false' in hide,
      'no unsubscribe is sent to a replay or unsupported peer')
roster_body = window[window.index('void SocialWindow::rebuildCreatureList()'):window.index('void SocialWindow::rebuildFeed()')]
for source in ('mGameMap.getSeats()', 'isAlliedSeat(seat)', 'mGameMap.getCreaturesBySeat(seat)',
               'entry.name = creature->getName()', 'entry.keeper = seat->getPlayer()->getNick()',
               'entry.appearance = CreatureAppearanceLogic::toToken(creature->getAppearance())'):
    check(source in roster_body, 'local list uses the recorded allied creature data: ' + source)
profile_body = window[window.index('void SocialWindow::refreshProfile('):window.index('void SocialWindow::refreshValues(')]
check('creature->fillProfilePage(mProfilePage)' in profile_body and 'if(creature != nullptr)' in profile_body,
      'a creature known here shows the existing social profile')
check('getStatsText(' not in window, 'the book does not invent server-only statistics')
values_body = window[window.index('void SocialWindow::refreshValues('):window.index('void SocialWindow::refreshInventory(')]
check('const bool known = !useLocalCreatureRoster();' in values_body and 'known ?' in values_body,
      'replays and older peers show no server-only values')
check('Known creatures (' in roster_body and 'detailed server statistics are unavailable' in roster_body,
      'local roster is identified as incomplete')
destructor = window[window.index('SocialWindow::~SocialWindow()'):window.index('void SocialWindow::setTabState')]
check('connection->disconnect()' in destructor and 'windows.destroyWindow(mProfilePage)' in destructor,
      'the dynamic page and all subscriptions are released')
check('mLinkConnections.push_back(window->subscribeEvent(event, subscriber))' in window,
      'every control subscription of the book is kept for the release')
client = read('source/network/ODClient.cpp')
check('getDungeonbookRosterOpen()' in server and 'notifyDungeonbookRoster(gameMap, player)' in server,
      'server sends snapshots only to subscribed clients')
check('askDungeonbookRoster, true' in window and 'askDungeonbookRoster, false' in window,
      'opening and closing the book starts and stops roster updates')
for fragment in ('getStatsText(owner)', 'getStrength()', 'getDexterity()', 'getLife()', 'getMana()',
                 'CreatureAppearanceLogic::toToken(creature->getAppearance())'):
    check(fragment in server, 'server roster includes actual profile data: ' + fragment)
for fragment in ('entry.name', 'entry.className', 'entry.keeper', 'entry.appearance', 'entry.stats',
                 'entry.level', 'entry.strength', 'entry.dexterity', 'entry.life', 'entry.mana',
                 'entry.worker', 'entry.champion', 'entry.unhappy'):
    check(fragment in client[client.index('case ServerNotificationType::dungeonbookRoster:'):],
          'client reads server roster field ' + fragment)
check('getDungeonbookRoster()' in window and 'getCircularCreatureAppearanceImage' in window,
      'the book uses the server roster and its assigned portrait')
header = read('source/render/SocialWindow.h')
check('onOpenProfileClicked' not in window + gamemode + header and 'createStatsWindow' not in window,
      'no window is opened from the Dungeonbook')
for handler in ('onNavClicked', 'onBackClicked', 'onPreviousClicked', 'onNextClicked', 'onFilterClicked',
                'onListRowClicked'):
    check('SocialWindow::' + handler in window and '&SocialWindow::' + handler in window, handler)
check('SocialWindow::onLinkClicked' in window and '&SocialWindow::onLinkClicked' in window,
      'the names in the friends and foe rows select a creature')
page = read('gui/WindowCreatureProfilePage.layout')
check('name="OwnPostsText"' in page and '"OwnPostsText"' in window,
      'the recent posts of the shared page give way to the posts column of the book')
check('MAX_OWN_POSTS = 6' in window and '(rows < MAX_OWN_POSTS)' in window,
      'the six recent posts remain available as pictures (book-variant-2)')
for name in ('FriendLink0', 'FriendLink1', 'FoeLink'):
    check('type="OD/InvisibleButton" name="%s"' % name in page, name + ' is a borderless button')
check('LinkButton' not in layout + window + gamemode, 'the friend and foe buttons below the profile are gone')
check('getHorzScrollbar' not in window and 'elideToWidth' not in window and 'fitTextToWindow' not in window
      and '"..."' not in window, 'long names are not shortened (decision 732) and need no horizontal scrollbar')
for name in ('CreaturesLabel', 'Name', 'Head', 'Text', 'NameText', 'KeeperText'):
    windows = social_root.findall(".//Window[@name='%s']" % name)
    check(windows, name)
    for part in windows:
        formatting = part.find("Property[@name='HorzFormatting']")
        check(formatting is not None and formatting.get('value').startswith('WordWrap'),
              name + ' word wraps its whole text (check_dungeonbook_profile_layout.py measures the longest one)')
check('EventMouseDoubleClick' not in window, 'no double click window')
selection = window[window.index('bool SocialWindow::onListRowClicked'):]
selection = selection[:selection.index('\n}\n')]
check('Page::Inventory' in selection, 'selecting a creature opens its inventory')
check('fillProfilePage(mProfilePage)' in window and 'createCreatureProfilePage(holder)' in window,
      'the profile uses the shared fill function')
tabs = window[window.index('void SocialWindow::setTabState'):window.index('bool SocialWindow::isVisible')]
check('setDisabled(' not in tabs and 'setEnabled(' not in tabs, 'the active tab stays enabled')
check('log.getVersion() != mShownProfilePostVersion' in window, 'the profile redraws only when needed')
check('if(!mWindow->isVisible())' in window, 'update does nothing while hidden')
check('REFRESH_CHECK_INTERVAL = 0.25f' in window and 'MAX_FEED_ROWS = 25' in window, 'redraw throttle and row limit')
check('getVersion() != mShownPostVersion' in window, 'redraw only when the feed changed')

postlog = read('source/social/PostLog.h')
check('MAX_POSTS = 200' in postlog, 'post limit')

creature = read('source/entities/Creature.cpp')
update = creature[creature.index('void Creature::updateFromPacket'):]
update = update[:update.index('\n}\n')]
check('isSocialFeedSource()' in update and 'reportUpdate(' in update, 'the update hook must be guarded')
source = creature[creature.index('bool Creature::isSocialFeedSource'):]
source = source[:source.index('\n}\n')]
check('isActive()' in source and 'getIsOnServerMap()' in source, 'posts only from client side creatures')

client = read('source/network/ODClient.cpp')
for call in ('socialCreatureAdded()', 'socialCreatureRemoved()', 'PostCategory::Eat', 'PostCategory::PickedUp'):
    check(call in client, call)

for pattern in ('network/ODServer*', 'network/ServerNotification*', 'network/ServerMode*', 'game/*'):
    for path in (repo / 'source').glob(pattern):
        if path.is_file():
            check('social/' not in read(str(path.relative_to(repo))), '%s includes the social code' % path.name)

cache = read('source/social/SocialProfileCache.cpp')
check('findFriendsAndFoe' in cache and 'getRosterVersion' in creature, 'friends cached per roster version')
for path in ('source/render/SocialWindow.cpp', 'source/render/SocialWindow.h', 'source/social/PostLog.cpp',
             'source/social/PostLog.h', 'source/social/CreaturePosts.cpp', 'source/social/CreaturePosts.h'):
    text = read(path)
    check(not re.search(r'\bauto\b', text), path + ' uses auto')
    check(not re.search('[\x00-\x08\x0b\x0c\x0e-\x1f]', text), path + ' contains control characters')
print('ok (%d checks)' % checks)
