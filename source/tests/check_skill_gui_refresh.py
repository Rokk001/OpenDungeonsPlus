"""Check that the skill GUI is not refreshed in every frame while the skill tree is closed. It does not start a game.

refreshGuiSkill() runs in every frame. The stored research type and progress are never updated, so while a
research runs the progress check forced a full refresh (all skill buttons, the tree layout and the action bar) in
every frame, also with the tree closed. The progress is shown only inside the tree: while it is closed, a change
of the progress alone now only marks the tree as outdated, and the tree is refreshed when it opens. All other
triggers (seat refresh flag, library lost or regained, forced refreshes) refresh as before, and with the tree
open the progress still refreshes in every frame.
"""
from pathlib import Path
import sys

repo = Path(__file__).resolve().parents[2]
game_mode = (repo / 'source/modes/GameMode.cpp').read_text(encoding='utf-8')
header = (repo / 'source/modes/GameMode.h').read_text(encoding='utf-8')


def function(text, signature):
    start = text.index(signature)
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


assert 'bool mIsSkillTreeOutdated = false;' in header, 'the outdated flag of the skill tree is missing'

refresh = function(game_mode, 'void GameMode::refreshGuiSkill(')
progress = refresh.index('(mCurrentSkillProgress != curSkillProgress)))')
early_return = refresh.index('if(!forceRefresh && !localPlayerSeat->getGuiSkillNeedsRefresh())')
before = refresh[progress:early_return]
assert 'if(mIsSkillWindowOpen)\n            forceRefresh = true;\n        else\n            mIsSkillTreeOutdated = true;' \
    in before, 'a progress change must refresh only with the tree open'
assert 'if(mIsSkillWindowOpen && mIsSkillTreeOutdated)\n        forceRefresh = true;' in before, \
    'an outdated tree must refresh once it is open'
assert 'mIsLibraryLostShown = localPlayerSeat->isLibraryLost();\n        forceRefresh = true;' in before, \
    'losing or regaining the library must still refresh'
after = refresh[early_return:]
assert after.index('mIsSkillTreeOutdated = false;') < after.index('SkillManager::listAllSkills('), \
    'a refresh must clear the outdated flag'
assert 'refreshSkillConnections();' in after and 'arrangeActionButtonPanels(mRootWindow);' in after
assert refresh.count('mIsSkillTreeOutdated = true;') == 1

# Opening the tree brings it up to date before it is shown
show = function(game_mode, 'bool GameMode::showSkillWindow(')
assert show.index('resetSkillTree();') < show.index('refreshGuiSkill();') < show.index('->show();'), \
    'the tree must be refreshed when it opens'
assert 'mIsSkillWindowOpen = true;' in function(game_mode, 'void GameMode::resetSkillTree(')

# The per-frame call and the forced refreshes stay
assert function(game_mode, 'void GameMode::onFrameStarted(').count('refreshGuiSkill();') == 1
assert game_mode.count('refreshGuiSkill(true);') == 4, 'the forced skill refreshes changed'

print('skill gui refresh ok: progress refresh only with the tree open, tree refreshed on open')
sys.exit(0)
