"""Wiring check (decision 724): MenuModeConfigureSeats::initSettingPages can be built any number of times. The windows it
creates live on the gui sheet, which outlives the mode, so a second skirmish must not hit CEGUI::AlreadyExistsException
(LabelAdventurer). The windows are destroyed before they are created and when the mode is destroyed (no compiler needed)."""
from pathlib import Path

repo = Path(__file__).resolve().parents[2]
text = (repo / 'source/modes/MenuModeConfigureSeats.cpp').read_text(encoding='utf-8')
header = (repo / 'source/modes/MenuModeConfigureSeats.h').read_text(encoding='utf-8')
assert 'void destroySettingPages();' in header

destroy = text.split('void MenuModeConfigureSeats::destroySettingPages()')[1].split('void MenuModeConfigureSeats::initSettingPages()')[0]
for name in ('"Label" +', '"Limit" +', '"ItemLabel" +', '"ItemButton" +'):
    assert name in destroy, name
assert 'isWindowPresent' in destroy and 'destroyWindow' in destroy

init = text.split('void MenuModeConfigureSeats::initSettingPages()')[1].split('bool MenuModeConfigureSeats::openGameSettings')[0]
assert init.index('destroySettingPages();') < init.index('createWindow'), 'destroy must come before creating'

dtor = text.split('MenuModeConfigureSeats::~MenuModeConfigureSeats()')[1].split('void MenuModeConfigureSeats::initSettingCombos')[0]
assert 'destroySettingPages();' in dtor
print('ok')
