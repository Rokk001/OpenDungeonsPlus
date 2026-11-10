"""T-C1: exercise production Room Manager navigation and check its GUI integration.

The runtime probe includes the real navigation header and fixes the expected eight
types, room counts and selection transitions. Use --source-only to check the GUI
contracts without compiling the small standalone probe.
"""
from pathlib import Path
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    """Read one repository file."""
    return (ROOT / path).read_text(encoding='utf-8')


def props(node):
    """Return the properties of a layout window."""
    return {entry.get('name'): entry.get('value') for entry in node.findall('Property')}


def body(text, signature):
    """Extract a C++ function while preserving nested brace blocks."""
    start = text.index(signature)
    opening = text.index('{', start)
    level, end = 1, opening + 1
    while level:
        level += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def unicode_glyph(font, codepoint):
    """Read Unicode cmap formats 4/12 from the tracked TTF without external packages."""
    data = font.read_bytes()
    u16 = lambda offset: struct.unpack_from('>H', data, offset)[0]
    u32 = lambda offset: struct.unpack_from('>I', data, offset)[0]
    cmap = None
    for index in range(u16(4)):
        record = 12 + index * 16
        if data[record:record + 4] == b'cmap':
            cmap = u32(record + 8)
            break
    assert cmap is not None, 'font has a Unicode character map'
    for index in range(u16(cmap + 2)):
        platform, encoding, offset = struct.unpack_from('>HHI', data, cmap + 4 + index * 8)
        if not (platform == 0 or platform == 3 and encoding in (1, 10)):
            continue
        base = cmap + offset
        if u16(base) == 12:
            for group in range(u32(base + 12)):
                start, end, glyph = struct.unpack_from('>III', data, base + 16 + group * 12)
                if start <= codepoint <= end:
                    return glyph + codepoint - start
        elif u16(base) == 4 and codepoint <= 0xFFFF:
            count = u16(base + 6) // 2
            ends = base + 14
            starts = ends + count * 2 + 2
            deltas = starts + count * 2
            ranges = deltas + count * 2
            for segment in range(count):
                start, end = u16(starts + segment * 2), u16(ends + segment * 2)
                if start <= codepoint <= end:
                    delta = struct.unpack_from('>h', data, deltas + segment * 2)[0]
                    relative = u16(ranges + segment * 2)
                    if relative == 0:
                        return (codepoint + delta) & 0xFFFF
                    glyph = u16(ranges + segment * 2 + relative + 2 * (codepoint - start))
                    return (glyph + delta) & 0xFFFF if glyph else 0
    return 0


def check_page_bounds(manager):
    """Check every embedded control through its shared frame at 640px through 8K."""
    numbers = lambda value: [float(number) for number in re.findall(r'-?\d+(?:\.\d+)?', value)]
    area = numbers(props(manager)['Area'])
    width, height = area[5] - area[1], area[7] - area[3]
    page_area = numbers(props(manager.find("Window[@name='Pages']"))['Area'])
    for screen_w, screen_h in ((640,480), (800,600), (1024,768), (1280,720), (1366,768),
                               (1920,1080), (2560,1440), (3440,1440), (3840,2160), (7680,4320)):
        for user in (0.8, 0.9, 1.0, 1.1, 1.2):
            layout_scale = min(screen_w / 1024, screen_h / 768) * user
            fit = min(1, screen_w / (width * layout_scale), screen_h / (height * layout_scale))
            scale = layout_scale * fit
            font_scale = min(screen_w / 800, screen_h / 600) * user
            # Dungeonbook frame side and bottom images are 36 design pixels;
            # its title uses 20pt font line spacing plus 12 design pixels padding.
            client_w = (width - 72) * scale
            client_h = height * scale - (20 * 4 / 3 * 1.35 * font_scale + 12 * scale) - 36 * scale
            page_w = (page_area[4] - page_area[0]) * client_w + (page_area[5] - page_area[1]) * scale
            page_h = (page_area[6] - page_area[2]) * client_h + (page_area[7] - page_area[3]) * scale
            for kind in ('Ghost', 'Merchant', 'Tavern', 'Spa', 'Infirmary', 'Alchemy', 'Casino', 'Workshop'):
                page = ET.parse(ROOT / ('gui/RoomManager' + kind + 'Page.layout')).getroot().find('Window')
                assert page.get('type') == 'DefaultWindow', kind + ' is an embedded page'
                for child in page.findall('Window'):
                    bounds = numbers(props(child)['Area'])
                    left = bounds[0] * page_w + bounds[1] * scale
                    top = bounds[2] * page_h + bounds[3] * scale
                    right = bounds[4] * page_w + bounds[5] * scale
                    bottom = bounds[6] * page_h + bounds[7] * scale
                    context = (kind, child.get('name'), screen_w, screen_h, user)
                    assert 0 <= left < right <= page_w + 0.5, ('horizontal bounds', context)
                    assert 0 <= top < bottom <= page_h + 0.5, ('vertical bounds', context)


PROBE = r'''
#include "rooms/RoomManagerNavigation.h"
#include <cstdlib>
#include <iostream>

//! \brief Reports one failed acceptance case without disabling release assertions.
void expect(bool condition, const char* message)
{
    if(!condition)
    {
        std::cerr << message << std::endl;
        std::exit(1);
    }
}

//! \brief Exercises ownership, first-row opening, shortcuts and room-loss transitions.
int main()
{
    const std::array<RoomType, 8> expected = {{RoomType::ghostRoom, RoomType::merchant,
        RoomType::tavern, RoomType::spa, RoomType::infirmary, RoomType::alchemyLab,
        RoomType::casino, RoomType::workshop}};
    expect(RoomManagerNavigation::order() == expected, "fixed room order");
    RoomManagerNavigation nav;
    expect(!nav.isOpen() && nav.listedCount() == 0, "starts closed with hidden button");
    nav.openFirst();
    expect(!nav.isOpen(), "button cannot open an empty manager");

    // Exhaust all owned-type subsets and every shortcut target against fixed expectations.
    for(unsigned mask = 0; mask < 256; ++mask)
    {
        std::array<uint32_t, 8> counts = {{0,0,0,0,0,0,0,0}};
        unsigned listed = 0;
        RoomType first = RoomType::nullRoomType;
        for(unsigned index = 0; index < 8; ++index)
        {
            if((mask & (1u << index)) == 0)
                continue;
            counts[index] = index + 2;
            ++listed;
            if(first == RoomType::nullRoomType)
                first = expected[index];
        }
        nav.close();
        nav.updateOwned(counts);
        expect(nav.listedCount() == listed, "Rooms counts types, not room instances");
        nav.openFirst();
        expect(nav.isOpen() == (listed != 0) && nav.selected() == first, "button opens first owned row");
        nav.close();
        expect(!nav.isOpen(), "button closes manager");
        for(unsigned index = 0; index < 8; ++index)
        {
            nav.openFirst();
            const bool owned = (mask & (1u << index)) != 0;
            expect(nav.owned(expected[index]) == owned, "only owned rows listed");
            const bool beforeOpen = nav.isOpen();
            const RoomType beforeSelected = nav.selected();
            nav.toggleType(expected[index]);
            if(!owned)
                expect(nav.isOpen() == beforeOpen && nav.selected() == beforeSelected, "unowned shortcut does nothing");
            else if(beforeSelected == expected[index])
                expect(!nav.isOpen(), "same shortcut closes selected row");
            else
                expect(nav.isOpen() && nav.selected() == expected[index], "shortcut changes row");
            nav.close();
            nav.toggleType(expected[index]);
            expect(nav.isOpen() == owned, "shortcut opens only owned target");
            if(owned)
            {
                expect(nav.selected() == expected[index], "shortcut opens requested target");
                nav.toggleType(expected[index]);
                expect(!nav.isOpen(), "shortcut closes target again");
                nav.selectType(expected[index]);
                nav.selectType(expected[index]);
                expect(nav.isOpen() && nav.selected() == expected[index], "clicking selected row keeps it open");
            }
        }
        nav.close();
        nav.toggleType(RoomType::library);
        expect(!nav.isOpen() && !nav.owned(RoomType::library), "unmanaged types never create a row");
    }

    std::array<uint32_t, 8> counts = {{1,2,0,0,3,1,0,1}};
    nav.updateOwned(counts);
    nav.selectType(RoomType::infirmary);
    counts[4] = 2;
    nav.updateOwned(counts);
    expect(nav.selected() == RoomType::infirmary, "losing a non-last room preserves selection");
    counts[4] = 0;
    nav.updateOwned(counts);
    expect(nav.isOpen() && nav.selected() == RoomType::ghostRoom, "losing selected type selects first row");
    counts = {{0,0,0,0,0,0,0,1}};
    nav.updateOwned(counts);
    expect(nav.isOpen() && nav.selected() == RoomType::workshop, "first remaining row becomes selected");
    counts[7] = 0;
    nav.updateOwned(counts);
    expect(!nav.isOpen() && nav.listedCount() == 0, "losing final type closes window and hides button");
    counts[1] = 1;
    nav.updateOwned(counts);
    expect(!nav.isOpen(), "new ownership does not open a closed window");
    std::cout << "Room Manager navigation runtime passed" << std::endl;
}
'''


def compile_probe():
    """Compile and execute the production header probe without building the game."""
    with tempfile.TemporaryDirectory(prefix='odp-room-manager-navigation-') as directory:
        work = Path(directory)
        (work / 'check.cpp').write_text(PROBE, encoding='utf-8')
        args = ['cl', '/nologo', '/EHsc', '/MD', '/O2', '/W3',
                '/I' + str(ROOT / 'source'), 'check.cpp', '/Fecheck.exe']
        if shutil.which('cl'):
            subprocess.run(args, cwd=work, check=True)
        else:
            vcvars = Path(os.environ['ProgramFiles(x86)']) / 'Microsoft Visual Studio/18/BuildTools/VC/Auxiliary/Build/vcvars64.bat'
            batch = work / 'compile.cmd'
            batch.write_text('@echo off\ncall "' + str(vcvars) + '" >nul\n' +
                             subprocess.list2cmdline(args) + '\nexit /b %errorlevel%\n', encoding='utf-8')
            subprocess.run(['cmd', '/d', '/c', str(batch)], cwd=work, check=True)
        subprocess.run([str(work / 'check.exe')], cwd=work, check=True)


if '--runtime-only' in sys.argv:
    compile_probe()
    sys.exit(0)

# The GUI contracts below bind the tested state to actual input handlers and layouts.
layout = ET.parse(ROOT / 'gui/WindowRoomManager.layout').getroot().find('Window')
assert layout.get('name') == 'RoomManagerWindow' and layout.get('type') == 'OD/FrameWindow'
assert props(layout)['Text'] == 'Room Manager'
assert props(layout)['Visible'] == 'False'
check_page_bounds(layout)
rows = layout.find("Window[@name='Rows']")
assert rows is not None
assert len(rows.findall('Window')) == 8, 'fixed eight room-type row slots'
book = ET.parse(ROOT / 'gui/WindowSocial.layout').getroot().find('Window')
book_row = book.find("Window[@name='HomePage']/Window[@name='ListRows']/Window[@name='Row0']")
for row in rows.findall('Window'):
    assert props(row.find("Window[@name='Highlight']")) == props(book_row.find("Window[@name='Highlight']")), 'Dungeonbook selection highlight'
    assert props(row.find("Window[@name='Name']"))['Font'] == props(book_row.find("Window[@name='Name']"))['Font'], 'Dungeonbook row font'
    height = re.findall(r'-?\d+(?:\.\d+)?', props(row)['Area'])
    assert float(height[7]) - float(height[3]) == 66, 'Dungeonbook design row height'
    assert row.find("Window[@name='Icon']") is not None and row.find("Window[@name='Button']") is not None
assert len(list(layout.iter('LayoutImport'))) == 8, 'eight room pages inside shared frame'
hud = ET.parse(ROOT / 'gui/ModeGame.layout').getroot()
windows = {node.get('name'): node for node in hud.iter('Window')}
button = windows['RoomManagerButton']
assert props(button)['TooltipText'] == 'Room Manager'
assert props(button)['NormalImage'] == 'OpenDungeonsIcons/NavigationRooms'
assert props(button)['Visible'] == 'False'
assert unicode_glyph(ROOT / 'gui/fonts/SourceSerif4-Semibold.ttf', 0x2022) == 508, 'tracked dot glyph'
assert props(button.find("Window[@name='Dot']"))['Text'] == '\u2022', 'HUD uses the covered circular bullet'
for row in rows.findall('Window'):
    assert props(row.find("Window[@name='Dot']"))['Text'] == '\u2022', 'rows use the covered circular bullet'
for removed in ('ProductionButton', 'InfirmaryButton', 'MerchantButton', 'GhostHuntersButton', 'LabButton'):
    assert removed not in windows, removed
imports = [node.get('filename') for node in hud.iter('LayoutImport')]
for removed in ('Production', 'Infirmary', 'Merchant', 'GhostRoom', 'AlchemyLab', 'Tavern', 'Spa', 'CasinoPayout'):
    assert 'Window' + removed + '.layout' not in imports
assert 'WindowRoomManager.layout' in imports
game = read('source/modes/GameMode.cpp')
nav = read('source/modes/GameModeRoomManager.cpp')
all_code = game + nav + read('source/modes/GameModeMerchant.cpp') + read('source/modes/GameModeAlchemy.cpp')
assert 'RoomManagerNavigation mRoomManagerNavigation;' in read('source/modes/GameMode.h')
for method in ('updateOwned(', 'openFirst()', 'toggleType(', 'selectType(', 'listedCount()', 'owned(', 'selected()'):
    assert 'mRoomManagerNavigation.' + method in all_code, method
mouse = body(game, 'bool GameMode::mousePressed(')
for forbidden in ('showInfirmaryWindow(', 'toggleMerchantWindow(', 'showAlchemyLabWindow(',
                  'showCasinoPayoutWindow(', 'showTavernWindow(', 'showSpaWindow(', 'showGhostRoomWindow('):
    assert forbidden not in mouse, 'room tile/figure click still opens ' + forbidden
for key, handler in (('I', 'toggleInfirmaryWindow'), ('K', 'toggleMerchantWindow'), ('L', 'toggleAlchemyLabWindow')):
    key_block = re.search(r'case OIS::KC_' + key + r':(.*?)(?=\n    case |\n    default:)', game, re.S)
    assert key_block and handler + '(' in key_block.group(1), key
for kind, path, handler in (('infirmary', 'source/modes/GameMode.cpp', 'toggleInfirmaryWindow'),
                             ('merchant', 'source/modes/GameModeMerchant.cpp', 'toggleMerchantWindow'),
                             ('alchemyLab', 'source/modes/GameModeAlchemy.cpp', 'toggleAlchemyLabWindow')):
    shortcut = body(read(path), 'bool GameMode::' + handler + '(')
    assert 'selectRoomManagerType(RoomType::' + kind in shortcut and 'closeAllTopWindows' not in shortcut
assert 'selectRoomManagerType(RoomType::workshop, true' in body(game, 'bool GameMode::showTrapProductionQueue(')
assert 'closeAllTopWindows()' in body(nav, 'bool GameMode::toggleRoomManager(')
shortcut = body(nav, 'bool GameMode::selectRoomManagerType(')
assert shortcut.index('!mRoomManagerNavigation.owned(type)') < shortcut.index('closeAllTopWindows()'), 'unowned options target leaves other windows open'
assert re.search(r'if\(closeOthers\)\s+closeAllTopWindows\(\);', shortcut), 'keyboard targets preserve other windows'
refresh = body(nav, 'void GameMode::refreshRoomManager(')
assert '"Rooms (" + Helper::toString(mRoomManagerNavigation.listedCount())' in refresh
assert 'setVisible(mRoomManagerNavigation.listedCount() > 0)' in refresh
assert 'row->setVisible(counts[index] > 0)' in refresh, 'only owned types appear'
assert 'mRoomManagerNavigation.updateOwned(counts)' in refresh and 'closeRoomManager()' in refresh
assert 'RoomManagerButton' in body(nav, 'void GameMode::initializeRoomManager(')
assert '&GameMode::toggleRoomManager' in body(nav, 'void GameMode::initializeRoomManager(')
assert '&GameMode::showTrapProductionQueue' in game and 'GameOptionsWindow/ProductionButton' in game
assert 'initializeRoomManager();' in game and 'refreshRoomManager();' in body(game, 'void GameMode::onFrameStarted(')
print('Room Manager navigation source contracts passed')
if '--source-only' not in sys.argv:
    compile_probe()
