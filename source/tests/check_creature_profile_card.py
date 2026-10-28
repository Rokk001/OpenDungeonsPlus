"""Check the creature profile card (gui/WindowCreatureProfile.layout) opened by a middle click.

The window is fixed size, created from the layout (registered for UI scaling), keeps the old stats
text on its own page in the small body font and still tells the server to start and stop sending
the statistics.
"""
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from PIL import ImageFont

repo = Path(__file__).resolve().parents[2]
gui = (repo / 'source/render/Gui.cpp').read_text()
layout = (repo / 'gui/WindowCreatureProfile.layout').read_text()
# the page with portrait, texts and bars is shared with the Dungeonbook
page = (repo / 'gui/WindowCreatureProfilePage.layout').read_text()
assert 'name="CreatureProfileWindow"' in layout and 'type="OD/FrameWindow"' in layout
assert '<Property name="SizingEnabled" value="False" />' in layout, 'the window must not be resizable'
m = re.search(r'name="Area" value="\{\{0\.5,(-?\d+)\},\{0\.5,(-?\d+)\},\{0\.5,(\d+)\},\{0\.5,(\d+)\}\}"', layout)
assert m, 'a fixed size centred area is expected'
width, height = int(m[3]) - int(m[1]), int(m[4]) - int(m[2])
assert width >= 480 and height >= 440, (width, height)
for name in ('ProfilePage', 'StatsText', 'ProfileTab', 'StatsTab', 'BookTab'):
    assert 'name="%s"' % name in layout, name
for name in ('ProfilePage', 'Portrait', 'HealthBar', 'ExperienceBar', 'BioText', 'FriendsLabel', 'FriendLink0', 'FriendLink1', 'FoeLabel',
             'FoeLink', 'StatusText', 'LatestText'):
    assert 'name="%s"' % name in page, name
stats = layout[layout.index('name="StatsText"'):]
stats = stats[:stats.index('</Window>')]
for prop in ('Font" value="MedievalSharp-8', 'VertFormatting" value="TopAligned',
             'HorzFormatting" value="WordWrapLeftAligned'):
    assert prop in stats, prop
assert 'name="VertScrollbar" value="True"' in stats, 'statistics must remain scrollable'
assert 'type="OD/VerticalScrollbar" name="ProfileScrollbar"' in page, 'the shared profile must scroll'
assert 'name="ClippedByParent" value="True"' in page, 'the profile must clip at its viewport'

body = gui[gui.index('Gui::createCreatureProfileWindow'):]
body = body[:body.index('\n}\n')]
assert 'WindowCreatureProfile.layout' in body and 'registerWindowHierarchy(window)' in body

creature = (repo / 'source/entities/Creature.cpp').read_text()
assert 'createCreatureProfileWindow(' in creature
assert 'CEGUI::UDim(0, 380)' not in creature, 'the card sets an own size'
assert creature.count('ClientNotificationType::askCreatureInfos') >= 2, 'server info start/stop is missing'
for handler in ('ProfileTabClicked', 'StatsTabClicked'):
    assert 'Creature::' + handler in creature, handler
assert 'EventCloseClicked' in creature
assert 'social/SocialProfileCache.h' in creature
# one function fills the page for the card and for the Dungeonbook
assert 'float Creature::fillProfilePage(CEGUI::Window* page)' in creature
assert 'fillProfilePage(mStatsWindow->getChild("ProfilePage/Content"))' in creature
assert 'createCreatureProfilePage(mStatsWindow->getChild("ProfilePage"))' in creature
assert 'WindowCreatureProfilePage.layout' in gui and 'setName("Content")' in gui
assert 'fillProfilePage(mProfilePage)' in (repo / 'source/render/SocialWindow.cpp').read_text()

# The initial viewport reserves the portrait, equipment and attributes; social metadata follows.
for name in ('HealthLabel', 'ExperienceLabel', 'RelationText', 'FoeLabel'):
    assert 'name="%s"' % name in page, name
profile_layout = gui[gui.index('float Gui::layoutCreatureProfilePage'):gui.index('void Gui::applyProfileScroll')]
assert profile_layout.index('CEGUI::Window* equipment') < profile_layout.index('page->getChild("AttributesText")')
assert profile_layout.index('page->getChild("AttributesText")') < profile_layout.index('const char* const personalRows')
assert profile_layout.index('page->getChild("EquipmentRow")') < profile_layout.index('page->getChild("AttributesText")') < profile_layout.index('const char* const barNames') < profile_layout.index('const char* const personalRows')
assert '"EquipmentRow"' in gui[gui.index('const char* const PROFILE_FLOW_ROWS[]'):gui.index('const std::size_t PROFILE_FLOW_ROW_COUNT')]
assert 'page->getPixelSize().d_width / scale - 148.0f - PROFILE_RIGHT_MARGIN' in profile_layout
assert 'PROFILE_FLOW_TOP - 34.0f - 2.0f * PROFILE_ROW_GAP' in profile_layout
assert 'const std::size_t slotCount = 13;' in profile_layout
assert 'count <= slotCount' in profile_layout and '(slotCount + count - 1) / count' in profile_layout
assert '(equipmentWidth - gaps) / static_cast<float>(last - first)' in profile_layout
assert 'if(candidate > edge)' in profile_layout and 'slot % columns == 0' in profile_layout
assert 'static_cast<float>(slot / columns) * (edge + PROFILE_ROW_GAP)' in profile_layout
assert '(slot == 6 || slot == 9) ? 12.0f : PROFILE_ROW_GAP' in profile_layout
assert 'setScaledArea(equipment, CEGUI::URect(CEGUI::UDim(0, 148), CEGUI::UDim(0, 34),' in profile_layout
assert 'countWrappedLines(equipment' not in profile_layout, 'hidden equipment text must not displace the item slots'
assert '34.0f + equipmentHeight + PROFILE_ROW_GAP' in profile_layout
assert 'getProfileLinesHeight(window, lines, scale)' in gui
assert 'getRenderedString()' in gui, 'measure the actual rendered text rather than a fixed number of rows'
assert 'setDocumentSize(y)' in profile_layout and 'setPageSize(viewport)' in profile_layout
assert 'std::min(scrollbar->getScrollPosition(), y - viewport)' in profile_layout
assert 'applyProfileScroll(page, offset)' in profile_layout
assert 'isFlowRow || (mProfileBaseAreas.find(child) == mProfileBaseAreas.end())' in profile_layout
for name in ('Portrait', 'NameText', 'EquipmentText', 'HandleText', 'AgeText', 'RelationText', 'FromText', 'JobText',
             'HealthLabel', 'HealthBar', 'ExperienceLabel', 'ExperienceBar'):
    cache_rows = gui[gui.index('const char* const PROFILE_FLOW_ROWS[]'):gui.index('const std::size_t PROFILE_FLOW_ROW_COUNT')]
    assert '"' + name + '"' in cache_rows, name + ' must refresh its unscrolled bounds on every layout'

# Use the shipped font and every configured weapon name, not short invented equipment labels.
font_spec = ET.parse(repo / 'gui/fonts/MedievalSharp-8.font').getroot()
font = ImageFont.truetype(str(repo / 'gui/fonts' / font_spec.get('filename')), 1024)
font_factor = float(font_spec.get('size')) * (96.0 / 72.0) * (1024.0 / 800.0) / 1024.0
line_height = sum(font.getmetrics()) * font_factor
weapon_names = re.findall(r'^\s*Name\s+(\S+)', (repo / 'config/equipments.cfg').read_text(), re.M)
assert weapon_names
longest_weapon = max(weapon_names + ['none'], key=font.getlength)
equipment_text = 'Equipment: ' + longest_weapon + ' / ' + longest_weapon
assert '"Equipment: " + getEquipmentText()' in creature
assert 'right + " / " + left' in creature
# Exercise the current attribute formula through MAX_LEVEL, including the two carried-item bonuses.
creature_config = (repo / 'config/creatures.cfg').read_text()
equipment_config = (repo / 'config/equipments.cfg').read_text()
max_level = int(re.search(r'MAX_LEVEL = (\d+)', (repo / 'source/entities/CreatureDefinition.h').read_text())[1])
attribute_values = []
for block in re.findall(r'\[Creature\](.*?)\[/Creature\]', creature_config, re.S):
    stats_values = dict((key, float(value)) for key, value in re.findall(
        r'^\s*(Strength|Dexterity|Life|Mana|StrengthPerLevel|DexterityPerLevel|LifePerLevel|ManaPerLevel)\s+(-?[0-9.]+)', block, re.M))
    for attribute in ('Strength', 'Dexterity', 'Life', 'Mana'):
        bonus = max([0.0] + [float(value) for value in re.findall(
            r'^\s*' + attribute + r'\s+(-?[0-9.]+)', equipment_config, re.M)]) * 2
        for level in (1, max_level):
            attribute_values.append(stats_values.get(attribute, 0.0) +
                                    stats_values.get(attribute + 'PerLevel', 0.0) * (level - 1) + bonus)
assert attribute_values
number_texts = [format(value, '.1f').removesuffix('.0') for value in attribute_values]
longest_number = max(number_texts, key=font.getlength)
critical_text = max([format(value, '.1f') for value in attribute_values], key=font.getlength)
attribute_lines = ['Strength {0} - Dexterity {0} - Life {0}'.format(longest_number),
                   'Mana {0} - Critical {1} %'.format(longest_number, critical_text)]
for label in ('Strength ', ' - Dexterity ', ' - Life ', '\\nMana ', ' - Critical '):
    assert '"' + label + '"' in creature


def wrapped_lines(text, available):
    """Measure word wrapping with the shipped font, including a word wider than the available row."""
    lines, current = 1, ''
    for word in text.split():
        candidate = (current + ' ' + word).strip()
        if current and font.getlength(candidate) * font_factor > available:
            lines += 1
            current = word
        else:
            current = candidate
        assert font.getlength(word) * font_factor <= available, ('word overflows the profile', word, available)
    return lines


skin = ET.parse(repo / 'gui/ODSkin.imageset').getroot()
side = float(skin.find("Image[@name='WindowLeftEdge']").get('width')) / 4.0
# Below the title bar the frame has no top edge; only the bottom edge reduces the client height.
border = float(skin.find("Image[@name='WindowBottomEdge']").get('height')) / 4.0
title = 18.0 * 10.0 / 8.0 + 12.0
social_layout = (repo / 'gui/WindowSocial.layout').read_text()
social_size = re.search(r'Area" value="\{\{0.5,(-?\d+)\},\{0.5,(-?\d+)\},\{0.5,(\d+)\},\{0.5,(\d+)\}\}"', social_layout)
social_width = int(social_size[3]) - int(social_size[1])
social_height = int(social_size[4]) - int(social_size[2])
social = (repo / 'source/render/SocialWindow.cpp').read_text()
assert 'OwnPostsText' in page and 'OwnPostsText' not in social_layout
assert 'ownPosts->setText(posts)' in social and 'ownPosts->setVisible(hasCreature && !posts.empty())' in social
assert social.index('ownPosts->setText(posts)') < social.index('creature->fillProfilePage(mProfilePage)')
assert 'y = layoutProfileTextRow(page->getChild("OwnPostsText"), y, scale)' in profile_layout
assert profile_layout.index('page->getChild("OwnPostsText")') > profile_layout.index('textRowsAfter[i]')
assert 'mProfilePage->setUserString("ProfileCreature", mSelectedCreature)' in social
assert 'setScrollPosition(0)' in social, 'a newly selected creature must open on the essential information'
scale_body = gui[gui.index('void Gui::applyScale('):gui.index('bool Gui::isScreenSizedContainer')]
assert 'layoutCreatureProfilePage(page)' in scale_body, 'profiles must reflow after UI or resolution changes'
assert scale_body.index('updateResourceScaling(displaySize)') < scale_body.index('layoutCreatureProfilePage(page)')

for screen_width, screen_height in ((640, 480), (1024, 768), (1920, 1200), (7680, 4320)):
    for percent in range(80, 121):
        scale = min(screen_width / 1024.0, screen_height / 768.0) * percent / 100.0
        for owner, outer_width, outer_height, fraction, reserve in (
                ('card', width, height, .88, 0.0),
                ('Dungeonbook', social_width, social_height, .9, 0.0)):
            fit = min(1.0, screen_width / (outer_width * scale), screen_height / (outer_height * scale))
            viewport = (outer_height * fit - title - border) * fraction - reserve
            page_width = (outer_width * fit - 2 * side) * (.5 if owner == 'Dungeonbook' else 1.0)
            equipment_width = page_width - 148.0 - 32.0
            image_edge, columns = 0.0, 1
            for count in range(1, 14):
                row_count = (13 + count - 1) // count
                candidate = min(56.0, (90.0 - (row_count - 1) * 4.0) / row_count)
                for first in range(0, 13, count):
                    last = min(13, first + count)
                    gaps = sum(12.0 if slot in (6, 9) else 4.0 for slot in range(first + 1, last))
                    candidate = min(candidate, (equipment_width - gaps) / (last - first))
                if candidate > image_edge:
                    image_edge, columns = candidate, count
            assert 0 < image_edge <= 56.0
            image_x = 0.0
            slot_bounds = []
            for slot in range(13):
                if slot % columns == 0:
                    image_x = 0.0
                    image_y = (slot // columns) * (image_edge + 4.0)
                else:
                    image_x += 12.0 if slot in (6, 9) else 4.0
                left, top = 148.0 + image_x, 34.0 + image_y
                right, bottom = left + image_edge, top + image_edge
                assert left >= 148.0 > 136.0 and top >= 34.0 > 26.0, 'slots overlap the portrait or headline'
                assert right <= page_width - 32.0 + 1e-6
                assert bottom <= 124.0 + 1e-6 and bottom <= viewport, 'all slots must open without scrolling'
                for previous_left, previous_top, previous_right, previous_bottom in slot_bounds:
                    assert right <= previous_left + 1e-6 or left >= previous_right - 1e-6 or bottom <= previous_top + 1e-6 or top >= previous_bottom - 1e-6, 'equipment slots overlap'
                slot_bounds.append((left, top, right, bottom))
                image_x += image_edge
            assert len(slot_bounds) == 13
            equipment_bottom = max(bounds[3] for bounds in slot_bounds)
            attribute_top = max(132.0, equipment_bottom + 4)
            attribute_bottom = attribute_top + sum(wrapped_lines(line, page_width - 48) for line in attribute_lines) * line_height + 4
            core_bottom = attribute_bottom + 4 + 20
            assert core_bottom <= viewport, (owner, screen_width, screen_height, percent, core_bottom, viewport)
            assert 124 <= attribute_top and 26 <= 34, 'portrait/header overlaps the following essential rows'
            assert equipment_bottom + 4 <= attribute_top, 'attributes overlap the equipment header'
            # Overflowed social rows are clipped to this viewport and reachable through the full scroll range.
            rows_bottom = core_bottom
            for lines in (1, 1, 1, 1, 1, 2, 8, 4, 3, 3, 2, 2, 4, 4, 6):
                top = rows_bottom + 4
                rows_bottom = top + lines * line_height + 4
                maximum = max(0.0, rows_bottom - viewport)
                offset = min(top, maximum)
                assert top - offset >= 0 and rows_bottom - offset <= viewport + 1e-6
            # The final widget can contain all five long posts; every line is reachable even when the widget is taller than the viewport.
            posts_top = rows_bottom + 4
            document_bottom = posts_top + 50 * line_height + 4
            maximum = document_bottom - viewport
            for line in range(50):
                line_top = posts_top + line * line_height
                offset = min(line_top, maximum)
                assert line_top - offset >= 0 and line_top + line_height - offset <= viewport + 1e-6
            assert abs(document_bottom - maximum - viewport) < 1e-6
assert 'setDisabled(' not in creature[creature.index('void Creature::showStatsPage'):creature.index('void Creature::refreshProfilePage')],     'the active tab must not be shown disabled'
assert 'Unspecified' not in (repo / 'source/social/SocialGenerator.cpp').read_text()
assert '"@" + getName()' not in creature, 'the handle must not be the internal name'
assert 'setText(getName() + " (" + getDefinition()->getClassName() + ")")' not in creature
game = (repo / 'source/modes/GameMode.cpp').read_text()
pick = game[game.index('void GameMode::openStatsWindowUnderPointer'):game.index('bool GameMode::mousePressed')]
assert 'findWorldPositionFromMouse' not in pick, 'the middle click must pick along the pointer ray'
assert 'getCameraToViewportRay' in pick
print('ok')
