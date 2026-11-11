"""Static check: the tooltips of the Dungeonbook inventory slots look like the item tooltip of the merchant mockup
W-1-merchant.png variant 3 (owner decision 1026, finding 5): dark box with a violet border, item name large and the
quality in the quality colour, the price after a gold coin, the bonuses as a short left-aligned list. No game and no
compiler needed.

Checked here:
1. gui/OD.looknfeel has the look OD/ItemTooltip with a dark background, a violet border, left aligned top aligned text
   and the named area TextArea, and the XML is well formed.
2. ItemInstance::describeTooltip writes name (large font) and quality in the quality colour, the price after the gold
   coin image, one line per bonus and effect with the values of describe(), and the level.
3. The default tooltip of Gui takes the look while the hovered window has the user string ItemTooltip = 1, and goes
   back to OD/Tooltip otherwise; the coin size follows the scaled by the display font, so it works at every resolution and UI scale.
4. The Dungeonbook slots (Creature::fillItemSlotWindows, boxes of SocialWindow::refreshInventory) use that tooltip; the
   merchant keeps describe() for its columns.
"""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

repo = Path(__file__).resolve().parents[2]
look = (repo / 'gui/OD.looknfeel').read_text()
ET.fromstring(look)
item = (repo / 'source/entities/ItemInstance.cpp').read_text()
header = (repo / 'source/entities/ItemInstance.h').read_text()
gui = (repo / 'source/render/Gui.cpp').read_text()
creature = (repo / 'source/entities/Creature.cpp').read_text()
social = (repo / 'source/render/SocialWindow.cpp').read_text()
icons = (repo / 'gui/ODIcons.imageset').read_text()
fonts = (repo / 'gui/ODSkin.scheme').read_text()


def block(text, start, end='\n}\n'):
    body = text[text.index(start):]
    return body[:body.index(end)]


# 1. The look
widget = block(look, '<WidgetLook name="OD/ItemTooltip">', '</WidgetLook>')
assert '<NamedArea name="TextArea">' in widget
assert re.search(r'name="background".*?Colours[^>]*topLeft="F[0-9A-F]10', widget, re.S) or 'F2100C18' in widget, 'dark box'
border = block(widget, '<ImagerySection name="border">', '</ImagerySection>')
assert 'FFB070FF' in border and border.count('<Image ') == 8, 'violet border on all edges and corners'
label = block(widget, '<ImagerySection name="label">', '</ImagerySection>')
assert '<HorzFormat type="LeftAligned" />' in label and '<VertFormat type="TopAligned" />' in label, 'left aligned list'
assert 'CentreAligned' not in widget
assert widget.count('<StateImagery') == 2, 'Enabled and Disabled'
# the look only uses images that exist
imageset = (repo / 'gui/ODSkin.imageset').read_text()
for name in set(re.findall(r'name="OpenDungeonsSkin/(Tooltip[A-Za-z]+)"', widget)):
    assert 'name="%s"' % name in imageset, name

# 2. The text
text = block(item, 'std::string ItemInstance::describeTooltip(')
assert "[font='MedievalSharp-13']" in text and "[font='MedievalSharp-10']" in text, 'large name, smaller lines'
for font in ('MedievalSharp-13', 'MedievalSharp-10'):
    assert 'name="%s"' % font in fonts, font
assert text.index('getDisplayName(map)') < text.index('qualityName(mQuality)') < text.index('GoldCoin') < text.index('itemNumber(getPrice(map))')
assert "OpenDungeonsIcons/GoldCoin" in text and 'name="GoldCoin"' in icons
assert 'image-size' in text and 'coinSize' in text
assert 'QUALITY_COLOURS' in text, 'name and quality in the quality colour'
assert 'mBonuses' in text and 'mEffects' in text and 'bonusName(bonus.first)' in text and 'getLevelMin(map)' in text
assert text.count(r'<< "\n"') >= 2, 'one line per value'
assert 'describeTooltip(const GameMap* map, const Weapon* heldWeapon, int32_t coinSize) const' in header
# describe() keeps its values for the merchant columns and the context line
assert 'std::string ItemInstance::describe(' in item

# 3. The tooltip window
assert 'const char* const ITEM_TOOLTIP_LOOK = "OD/ItemTooltip";' in gui
assert 'const char* const PLAIN_TOOLTIP_LOOK = "OD/Tooltip";' in gui
moved = block(gui, 'context.setDefaultTooltipType("OD/Tooltip");', 'return true;')
assert 'getUserString(ITEM_TOOLTIP_USER_STRING) == "1"' in moved
assert 'tooltip->setLookNFeel(look);' in moved and 'tooltip->sizeSelf();' in moved
assert 'getFontHeight()' in block(gui, 'void Gui::setItemTooltip(', '\n}\n'), 'coin as high as the scaled by the display line'
assert 'setUserString(ITEM_TOOLTIP_USER_STRING, "1")' in gui
assert 'static void setItemTooltip(' in (repo / 'source/render/Gui.h').read_text()

# 4. The slots
fill = block(creature, 'void Creature::fillItemSlotWindows(', '\n}\n')
assert 'Gui::setItemTooltip(image, *item, creature->getGameMap(), heldWeapon);' in fill
assert 'Gui::setPlainTooltip(image, ""' in fill
assert 'Gui::copyTooltip(slot, slot->getParent());' in block(social, 'void SocialWindow::refreshInventory(', '\n}\n')
assert 'item.describe(mGameMap)' in (repo / 'source/modes/GameModeMerchant.cpp').read_text()

print('item card tooltip 1026: look, text, tooltip switch and slots checked')
