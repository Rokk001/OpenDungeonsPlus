"""Check Dungeonbook navigation wiring and the six existing visual asset blobs."""
from pathlib import Path
import hashlib
import re
import xml.etree.ElementTree as ET

repo = Path(__file__).resolve().parents[2]
source = (repo / 'source/render/SocialWindow.cpp').read_text(encoding='utf-8')
book = ET.parse(repo / 'gui/WindowSocial.layout').getroot().find('Window')
home = book.find("Window[@name='HomePage']")
assert home.find("Window[@name='Filter']").get('type') == 'OD/Combobox'
assert all(label in source for label in ('"All", "Workers", "Fighters", "Unhappy"',))

def body(signature):
    return source.split(signature, 1)[1].split('\n}', 1)[0]

assert 'mFilter = CreatureFilter::All' in body('void SocialWindow::show()')
assert 'Page::Inventory' in body('void SocialWindow::showCreature(')
assert 'Page::Inventory' in body('bool SocialWindow::onListRowClicked(')
assert 'Page::Inventory' in body('bool SocialWindow::onLinkClicked(')
assert 'mSelectedCreature.clear()' in body('bool SocialWindow::onFilterClicked(')
assert 'showPage(Page::Home)' in body('bool SocialWindow::onFilterClicked(')
assert 'setVisible(true)' in body('void SocialWindow::showPage(')
assert 'setVisible(page != Page::Home)' in body('void SocialWindow::showPage(')
assert 'if(!all && (it->mCreature != mSelectedCreature))' in body('void SocialWindow::rebuildFeed()')
for name in ('NavFeed', 'NavProfile', 'NavValues', 'NavInventory'):
    assert book.find("Window[@name='NavBar']/Window[@name='%s']" % name) is not None
for page in ('HomePage', 'FeedPage'):
    for row in range(3):
        assert book.find("Window[@name='%s']/Window[@name='FeedRows']/Window[@name='Row%d']/Window[@name='ProfileLink']" % (page, row)) is not None

expected = {
    'DungeonbookIcons.png': '1f8c0171d312b6a7c432eb9640cd754089ace73f',
    'DungeonbookIcons.imageset': '917403f14a5141d3596a8ce695644c9a73930ddb',
    'DungeonbookFrame.png': '063c2b8218920147fc09e48895625fd1ef8b4588',
    'DungeonbookFrame.imageset': 'a3849a2059181573d6bfa587858c10598de4f8d6',
    'DungeonbookPage.png': 'b0486c52b0fe410979301f20636dd3fb03a36bce',
    'DungeonbookPage.imageset': 'c1003912e3e5c1037805e6ef1311d527eef393d1',
}
for name, digest in expected.items():
    data = (repo / 'gui' / name).read_bytes()
    if name.endswith('.imageset'):
        data = data.replace(b'\r\n', b'\n')
    assert hashlib.sha1(('blob %d\0' % len(data)).encode() + data).hexdigest() == digest, name
print('Dungeonbook navigation wiring and six visual assets: OK')

