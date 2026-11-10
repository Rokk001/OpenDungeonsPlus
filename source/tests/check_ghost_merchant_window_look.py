"""Ghost and merchant page look, shared frame and all nested text at every required scale.

The merchant empty state is eighteen empty slots. R6 replaces the old explanation
panels and history row with pictures, short labels and item confirmation.
"""
from pathlib import Path
import xml.etree.ElementTree as ET
from check_room_manager_pages import props, windows, fit_page

ROOT=Path(__file__).resolve().parents[2]
manager=ET.parse(ROOT/'gui/WindowRoomManager.layout').getroot().find('Window')
book=ET.parse(ROOT/'gui/WindowSocial.layout').getroot().find('Window')
for key,value in props(book).items():
    if (key.startswith('Frame') and key.endswith('Image')) or key=='TitlebarFont':
        assert props(manager)[key]==value,'shared Dungeonbook '+key
assert props(manager.find('AutoWindow'))==props(book.find('AutoWindow')),'shared Dungeonbook title band'
for name in ('Ghost','Merchant'):
    root=ET.parse(ROOT/('gui/RoomManager'+name+'Page.layout')).getroot().find('Window')
    assert root.get('type')=='DefaultWindow' and root.find('AutoWindow') is None
    page=windows(root)
    assert 'CloseButton' not in page,'common close control'
    for path,node in page.items():
        q=props(node)
        if node.get('type') in ('OD/Button','OD/Checkbox','OD/StaticText','OD/MultiColumnList'):
            assert q.get('Font','').startswith('MedievalSharp-'),(name,path,'game font')
        if node.get('type')=='OD/StaticText':
            assert q.get('TextColours')=='FFF2C860',(name,path,'gold labels')
        assert node.get('type')!='OD/GameTabButton',(name,path,'no HUD tab in room page')
        assert len(q.get('TooltipText',''))<=100,(name,path,'tooltip bounds')
    assert not {'HistoryText','HistoryPanel','EmptyText','GhostExplainText'} & set(page)
    fit_page(name,page,windows(manager))
merchant=(ROOT/'source/modes/GameModeMerchant.cpp').read_text()
assert 'std::max<std::size_t>(18, ((items.size() + 5) / 6) * 6)' in merchant,'eighteen empty slots, six columns'
assert 'cell->setDisabled(true)' in merchant,'empty slots are not goods'
assert 'cell->setTooltipText(items[index].second.describe(mGameMap))' in merchant,'full item tooltip'
assert 'positionSelf()' in merchant,'tooltip at the pointer'
assert 'refreshMerchantSelection();' in merchant,'treasury enabled state refreshed'
shared=(ROOT/'source/modes/GameModeRoomManager.cpp').read_text()
assert 'CEGUI::FrameWindow::EventCloseClicked' in shared and '&GameMode::closeRoomManager' in shared
print('PASS ghost and merchant shared frame, fonts, gold labels, empty slots and 100 screen/scale cases')
