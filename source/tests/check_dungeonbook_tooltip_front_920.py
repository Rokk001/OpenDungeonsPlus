"""Static check: the item tooltip of a Dungeonbook slot is drawn in front of the book (owner decision 920). No game and
no compiler needed.

Cause found in the CEGUI 0.8 source: the default tooltip (CEGUI::Tooltip, always on top) stays attached to the root
window between two targets, and Window::addChild_impl does nothing for a window that is already a child, so a new
target does not bring it forward. GameMode::raiseShownDialog makes every shown dialog, the Dungeonbook too, always on
top as well and moves it to the front, and every click into the book raises it again (Window::moveToFront_impl, rise
on click). The book then lay over the tooltip, which showed the item values behind the book: nothing could be seen
when hovering a slot, also for the pickaxe of a worker. The fix re-attaches the tooltip at the front of its layer
after every change of the drawing order.
Checked here:
1. Gui.cpp counts a change of the drawing order (EventZOrderChanged of the default tooltip), and keepTooltipInFront
   removes and adds the tooltip again, without moveToFront (that would activate it and take the keyboard), ignoring its
   own change; ODFrameListener calls it every frame before the time pulse, outside of the CEGUI window update.
2. A model of the CEGUI drawing order: without the fix a dialog raised after the tooltip covers it, with it the
   tooltip is the last (front) window of the always-on-top layer.
3. Every filled slot still gets item->describe as tooltip, also the worker tool of the spawn fallback, and the box
   repeats it (decision 863).
"""
from pathlib import Path
import re

repo = Path(__file__).resolve().parents[2]
gui = (repo / 'source/render/Gui.cpp').read_text(encoding='utf-8')
gui_h = (repo / 'source/render/Gui.h').read_text(encoding='utf-8')
frame = (repo / 'source/render/ODFrameListener.cpp').read_text(encoding='utf-8')
game = (repo / 'source/modes/GameMode.cpp').read_text(encoding='utf-8')
creature = (repo / 'source/entities/Creature.cpp').read_text(encoding='utf-8')
social = (repo / 'source/render/SocialWindow.cpp').read_text(encoding='utf-8')


def function_of(text, signature):
    body = text[text.index(signature):]
    return body[:body.index('\n}\n')]


# 1. The fix in the code
assert 'static void keepTooltipInFront();' in gui_h
assert re.search(r'defaultTooltip->subscribeEvent\(CEGUI::Window::EventZOrderChanged,\s*CEGUI::Event::Subscriber\('
                 r'\[\]\(const CEGUI::EventArgs&\)\s*\{\s*if\(!sRaisingTooltip\)\s*sTooltipOrderChanged = true;', gui), \
    'the default tooltip must note every change of the drawing order of its siblings'
keep = function_of(gui, 'void Gui::keepTooltipInFront()')
assert 'if(!sTooltipOrderChanged' in keep and 'sTooltipOrderChanged = false;' in keep
assert 'getDefaultTooltipObject()' in keep and 'tooltip->getParent()' in keep
assert keep.index('sRaisingTooltip = true;') < keep.index('parent->removeChild(tooltip);') < \
    keep.index('parent->addChild(tooltip);') < keep.index('sRaisingTooltip = false;'), \
    'the tooltip is removed and added again at the front of its layer, its own change is not counted'
assert 'moveToFront' not in keep.replace('moveToFront is', ''), 'moveToFront would activate the tooltip'
pulse = frame.index('getDefaultGUIContext().injectTimePulse(evt.timeSinceLastFrame);')
call = frame.index('Gui::keepTooltipInFront();')
assert call < frame.index('CEGUI::System::getSingleton().injectTimePulse(evt.timeSinceLastFrame);') < pulse, \
    'the tooltip is brought forward once per frame before the time pulse, outside of the window update'
raise_dialog = function_of(game, 'bool GameMode::raiseShownDialog(const CEGUI::EventArgs& e)')
assert 'setAlwaysOnTop(true)' in raise_dialog and 'moveToFront()' in raise_dialog, \
    'the dialogs share the always-on-top layer with the tooltip; that is the case the fix handles'


# 2. Model of the drawing order of the root window (CEGUI Window::addWindowToDrawList, addChild_impl, moveToFront)
class Root:
    def __init__(self):
        self.draw = []

    def add(self, name, top):
        if name in [n for n, _ in self.draw]:
            return  # Window::addChild_impl: "if the element is already a child of this Window, this is a NOOP"
        self.draw.append((name, top)) if top else self.draw.insert(
            len([1 for _, t in self.draw if not t]), (name, top))

    def remove(self, name):
        self.draw = [(n, t) for n, t in self.draw if n != name]

    def raise_window(self, name):
        top = dict(self.draw)[name]
        self.remove(name)
        self.add(name, top)

    def front(self):
        return self.draw[-1][0]


def scenario(with_fix):
    root = Root()
    root.add('HUD', False)
    root.add('Tooltip', True)  # attached by the first hovered window, hidden while its target has no text
    changed = False
    root.add('SocialWindow', True)
    root.raise_window('SocialWindow')  # raiseShownDialog, then a click into the book (rise on click)
    changed = True
    root.add('Tooltip', True)  # the pointer enters the slot: setTargetWindow adds the tooltip again, a no-op
    if with_fix and changed:
        root.remove('Tooltip')
        root.add('Tooltip', True)
    return root.front()


assert scenario(False) == 'SocialWindow', 'the model shows the reported fault: the book covers the tooltip'
assert scenario(True) == 'Tooltip', 'with the fix the tooltip is in front of the book'

# 3. Every filled slot has the item values as tooltip, the worker tool too
fill = function_of(creature, 'void Creature::fillItemSlotWindows(')
assert fill.index('spawnFallback = ItemDrops::poorWeapon(*weapon);') < \
    fill.index('image->setTooltipText(item == nullptr ? "" : item->describe(creature->getGameMap(), heldWeapon));'), \
    'the spawn tool of a worker is a filled slot with the item values'
inventory = function_of(social, 'void SocialWindow::refreshInventory(')
assert 'slot->getParent()->setTooltipText(slot->getTooltipText());' in inventory

print('check_dungeonbook_tooltip_front_920: OK')
