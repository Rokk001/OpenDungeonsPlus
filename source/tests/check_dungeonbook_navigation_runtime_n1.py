"""Exercise production navigation handlers with isolated window/network services.

--source-only validates contracts and emits the probe without compiling during a plan.
The default invocation compiles and runs it during FINAL. Save/load coverage here
checks the UI lifecycle (fresh book over restored creatures), not game serialization.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from item_probe_support import ROOT, compile_and_run, function, source


def make_probe():
    """Keep the actual handlers unchanged while replacing external game services."""
    social = source('source/render/SocialWindow.cpp')
    signatures = [
        'void SocialWindow::show()', 'void SocialWindow::showCreature(',
        'void SocialWindow::hide()', 'bool SocialWindow::onFilterClicked(',
        'bool SocialWindow::onListRowClicked(', 'bool SocialWindow::onLinkClicked(',
        'bool SocialWindow::onBackClicked(', 'bool SocialWindow::onNavClicked(',
        'void SocialWindow::selectCreature(', 'void SocialWindow::showPage(',
    ]
    implementations = '\n'.join(function(social, name) for name in signatures)
    roster = function(social, 'void SocialWindow::rebuildCreatureList()')
    predicates = roster[roster.index('        if((mFilter'):roster.index('        const social::CreatureProfile&')]
    # The overview feed must not consult the roster filter or filtered creature list.
    feed = function(social, 'void SocialWindow::rebuildFeed()')
    assert 'const bool all = (mPage == Page::Home);' in feed
    assert 'if(!all && (it->mCreature != mSelectedCreature))' in feed
    assert 'mFilter' not in feed and 'mListedCreatures' not in feed
    assert 'mSocialWindow->showCreature(selectedCreature);' in source('source/modes/GameMode.cpp')
    # Navigation remains a UI concern; the save writer has no filter/selection state.
    for name in ('source/gamemap/MapHandler.cpp', 'source/gamemap/GameMap.cpp'):
        assert 'mFilter' not in source(name) and 'mSelectedCreature' not in source(name)
    return r'''
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <map>
#include <sstream>
#include <string>
#include <vector>
namespace CEGUI {
//! Supplies event and widget state, retaining popup selection separately from edit text.
struct EventArgs {};
struct ListboxItem { unsigned id = 0; unsigned getID() const { return id; } };
struct Window {
    bool visible = false, enabled = true;
    std::string text;
    std::map<std::string, Window*> children;
    std::map<std::string, std::string> strings;
    //! Resolves the fixed widget paths used by production handlers.
    Window* getChild(const std::string& name) { assert(children.count(name)); return children[name]; }
    //! Reports the window visibility observed by production handlers.
    bool isVisible() const { return visible; }
    //! Records the requested window visibility.
    void setVisible(bool value) { visible = value; }
    //! Records whether a navigation button can be used.
    void setEnabled(bool value) { enabled = value; }
    //! Opens the fixture window.
    void show() { visible = true; }
    //! Closes the fixture window.
    void hide() { visible = false; }
    //! Leaves drawing order outside this handler probe.
    void moveToFront() {}
    //! Records edit text separately from popup selection.
    void setText(const std::string& value) { text = value; }
    //! Reports whether the event widget has a creature or row identifier.
    bool isUserStringDefined(const std::string& name) const { return strings.count(name) != 0; }
    //! Reads a production-handler event identifier.
    const std::string& getUserString(const std::string& name) const { return strings.at(name); }
};
//! Supplies a combobox whose selected item is independent of its displayed text.
struct Combobox : Window {
    ListboxItem item;
    //! Supplies the popup item independently of edit text.
    const ListboxItem* getSelectedItem() const { return &item; }
    //! Selects the popup item requested by a reset.
    void setItemSelectState(std::size_t index, bool selected) { assert(selected); item.id = unsigned(index); }
};
//! Supplies a deterministic list scroll position.
struct Scrollbar : Window { float getScrollPosition() const { return 0; } };
struct WindowEventArgs : EventArgs { Window* window = nullptr; };
}
namespace social {
struct DungeonbookEntry { std::string name; bool worker; bool unhappy; };
//! Supplies the asynchronous roster-ready flag used by the actual page guards.
struct PostLog {
    bool ready = true;
    //! Returns the isolated roster service.
    static PostLog& getSingleton() { static PostLog log; return log; }
    //! Reports whether a simulated roster has arrived.
    bool isDungeonbookRosterReady() const { return ready; }
    //! Simulates waiting for the next roster snapshot.
    void clearDungeonbookRoster() { ready = false; }
};
}
enum class ClientNotificationType { askDungeonbookRoster };
//! Records subscription service calls without opening a network connection.
struct ODClient {
    //! Returns the isolated client service.
    static ODClient& getSingleton() { static ODClient client; return client; }
    //! Accepts subscription messages without network activity.
    void queueClientNotification(ClientNotificationType, bool) {}
};
//! Uses the local roster fixture so opening does not discard its restored creatures.
bool useLocalCreatureRoster() { return true; }
const char* const FILTER_LABELS[] = {"All", "Workers", "Fighters", "Unhappy"};
const char* const NAV_BUTTONS[] = {"NavFeed", "NavProfile", "NavValues", "NavInventory"};
//! Replaces painting only; page and button visibility run through production showPage.
void setNavState(CEGUI::Window*, bool) {}
//! Hosts unchanged production handlers with explicit roster and painting service boundaries.
struct SocialWindow {
    enum class CreatureFilter { All, Workers, Fighters, Unhappy };
    enum class Page { Home, Feed, Profile, Values, Inventory };
    CEGUI::Window* mWindow;
    CreatureFilter mFilter = CreatureFilter::All;
    Page mPage = Page::Home;
    std::string mSelectedCreature;
    std::vector<std::string> mListedCreatures = {"worker", "fighter"};
    float mSinceRefreshCheck = 0;
    void show(); void showCreature(const std::string&); void hide();
    bool onFilterClicked(const CEGUI::EventArgs&); bool onListRowClicked(const CEGUI::EventArgs&);
    bool onLinkClicked(const CEGUI::EventArgs&); bool onBackClicked(const CEGUI::EventArgs&);
    bool onNavClicked(const CEGUI::EventArgs&);
    void selectCreature(const std::string&, Page); void showPage(Page);
    //! Applies the production filter predicates to a stable two-creature roster fixture.
    void rebuildCreatureList() {
        const social::DungeonbookEntry entries[] = {{"worker", true, false}, {"fighter", false, true}};
        mListedCreatures.clear();
        for(const social::DungeonbookEntry& creature : entries) {
''' + predicates + r'''
            mListedCreatures.push_back(creature.name);
        }
    }
    //! Keeps painting outside this navigation-handler probe.
    void refreshListRows() {}
    //! Keeps creature-page painting outside this navigation-handler probe.
    void refreshPage() {}
    //! Keeps feed painting outside this navigation-handler probe; source contracts check its selection guard.
    void rebuildFeed() {}
    //! Resolves either fixture creature while rejecting missing selections.
    const social::DungeonbookEntry* findEntry(const std::string& name) const {
        static social::DungeonbookEntry entry;
        return name == "worker" || name == "fighter" ? &entry : nullptr;
    }
};
''' + implementations + r'''
//! Runs selection, all filter choices, every tab, reopen and restored-world UI lifecycle scenarios.
int main() {
    CEGUI::Window root;
    CEGUI::Combobox filter;
    CEGUI::Scrollbar scroll;
    const char* names[] = {"HomePage", "FeedPage", "ProfilePage", "ValuesPage", "InventoryPage", "NavBar", "Header",
        "HomePage/FeedPanel", "HomePage/FeedTitle", "HomePage/FeedTitleRule", "HomePage/FeedRows",
        "HomePage/FeedScroll", "HomePage/FeedEmpty", "NavBar/NavFeed", "NavBar/NavProfile", "NavBar/NavValues", "NavBar/NavInventory"};
    CEGUI::Window windows[17];
    for(std::size_t i = 0; i < 17; ++i) root.children[names[i]] = &windows[i];
    root.children["HomePage/Filter"] = &filter;
    root.children["HomePage/ListScroll"] = &scroll;
    SocialWindow book;
    book.mWindow = &root;
    book.show();
    assert(book.mPage == SocialWindow::Page::Home && root.getChild("HomePage")->visible);
    assert(root.getChild("HomePage/FeedRows")->visible && !root.getChild("NavBar")->visible);
    CEGUI::Window row;
    row.strings["Row"] = "0";
    CEGUI::WindowEventArgs event;
    event.window = &row;
    for(unsigned choice = 0; choice < 4; ++choice) {
        book.onListRowClicked(event);
        assert(book.mPage == SocialWindow::Page::Inventory && book.mSelectedCreature == "worker");
        assert(root.getChild("HomePage")->visible && root.getChild("NavBar")->visible);
        assert(!root.getChild("HomePage/FeedRows")->visible);
        filter.item.id = choice;
        book.onFilterClicked(event);
        const std::vector<std::string> expected[] = {{"worker", "fighter"}, {"worker"}, {"fighter"}, {"fighter"}};
        assert(book.mListedCreatures == expected[choice]);
        assert(book.mSelectedCreature.empty() && book.mPage == SocialWindow::Page::Home);
        assert(root.getChild("HomePage")->visible && root.getChild("HomePage/FeedRows")->visible);
        assert(!root.getChild("NavBar")->visible && !root.getChild("Header")->visible);
        book.hide(); book.show();
        assert(book.mFilter == SocialWindow::CreatureFilter::All && filter.item.id == 0 && filter.text == "All");
    }
    book.showCreature("fighter");
    assert(book.mPage == SocialWindow::Page::Inventory && book.mSelectedCreature == "fighter");
    row.strings["Creature"] = "worker";
    book.onLinkClicked(event);
    assert(book.mPage == SocialWindow::Page::Inventory && book.mSelectedCreature == "worker");
    book.mFilter = SocialWindow::CreatureFilter::Fighters;
    book.rebuildCreatureList();
    filter.item.id = 2;
    book.onLinkClicked(event);
    assert(book.mFilter == SocialWindow::CreatureFilter::All && filter.item.id == 0);
    assert(book.mPage == SocialWindow::Page::Inventory && book.mSelectedCreature == "worker");
    for(unsigned tab = 1; tab <= 4; ++tab) {
        row.strings["Page"] = std::to_string(tab);
        book.onNavClicked(event);
        assert(static_cast<unsigned>(book.mPage) == tab && root.getChild("HomePage")->visible);
        assert(root.getChild("NavBar")->visible);
    }
    book.onBackClicked(event);
    assert(book.mSelectedCreature.empty() && book.mPage == SocialWindow::Page::Home);
    // Saving keeps the live UI unchanged; loading creates a fresh book over restored creatures.
    filter.item.id = 3;
    book.onFilterClicked(event);
    const std::vector<std::string> savedCreatures = {"worker", "fighter"};
    assert(book.mFilter == SocialWindow::CreatureFilter::Unhappy);
    book.hide();
    SocialWindow loaded;
    loaded.mWindow = &root;
    loaded.mListedCreatures = savedCreatures;
    loaded.show();
    assert(loaded.mListedCreatures == savedCreatures && loaded.mFilter == SocialWindow::CreatureFilter::All);
    assert(filter.item.id == 0 && filter.text == "All" && loaded.mSelectedCreature.empty());
    assert(root.getChild("HomePage/FeedRows")->visible && !root.getChild("NavBar")->visible);
}
'''


def main():
    """Emit the bounded runtime probe during a plan, or execute it during FINAL."""
    probe = make_probe()
    if '--source-only' in sys.argv:
        destination = ROOT / 'out/dungeonbook-navigation-n1/probe.cpp'
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(probe, encoding='utf-8')
        print('N1 source contracts passed; production-handler runtime/UI reload probe emitted, execution deferred')
    else:
        compile_and_run('dungeonbook-navigation-n1', probe)


if __name__ == '__main__':
    main()
