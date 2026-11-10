from hashlib import sha256
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
MAPPINGS = {
    'AlchemyLabButton': ('alchemy-lab.png', 'RoomCentreIconAlchemyLab/Icon'),
    'ArenaButton': ('arena.png', 'RoomCentreIconArena/Icon'),
    'CasinoButton': ('casino.png', 'RoomCentreIconCasino/Icon'),
    'CryptButton': ('crypt.png', 'RoomCentreIconCrypt/Icon'),
    'DormitoryButton': ('dormitory.png', 'RoomCentreIconDormitory/Icon'),
    'GhostRoomButton': ('ghost-room.png', 'RoomCentreIconGhostRoom/Icon'),
    'GuardRoomButton': ('guard-room.png', 'RoomCentreIconGuardRoom/Icon'),
    'HatcheryButton': ('hatchery.png', 'RoomCentreIconHatchery/Icon'),
    'HerbGardenButton': ('herb-garden.png', 'RoomCentreIconHerbGarden/Icon'),
    'InfirmaryButton': ('infirmary.png', 'RoomCentreIconInfirmary/Icon'),
    'LibraryButton': ('library.png', 'RoomCentreIconLibrary/Icon'),
    'MerchantButton': ('merchant.png', 'RoomCentreIconMerchant/Icon'),
    'PrayerTempleButton': ('prayer-temple.png', 'RoomCentreIconPrayerTemple/Icon'),
    'PrisonButton': ('prison.png', 'RoomCentreIconPrison/Icon'),
    'SpaButton': ('spa.png', 'RoomCentreIconSpa/Icon'),
    'StoneBridgeButton': ('stone-bridge.png', 'RoomCentreIconStoneBridge/Icon'),
    'TavernButton': ('tavern.png', 'RoomCentreIconTavern/Icon'),
    'TempleButton': ('temple.png', 'RoomCentreIconTemple/Icon'),
    'ToiletButton': ('toilet.png', 'RoomCentreIconToilet/Icon'),
    'TortureButton': ('torture-chamber.png', 'RoomCentreIconTortureChamber/Icon'),
    'TrainingHallButton': ('training-hall.png', 'RoomCentreIconTrainingHall/Icon'),
    'TreasuryButton': ('treasury.png', 'RoomCentreIconTreasury/Icon'),
    'WoodenBridgeButton': ('wooden-bridge.png', 'RoomCentreIconWoodenBridge/Icon'),
    'WorkshopButton': ('workshop.png', 'RoomCentreIconWorkshop/Icon'),
}
BUILD_BAR = (
    'DormitoryButton', 'ToiletButton', 'HatcheryButton', 'TavernButton', 'SpaButton', 'LibraryButton',
    'TrainingHallButton', 'TreasuryButton', 'WorkshopButton', 'CasinoButton', 'PrisonButton',
    'WoodenBridgeButton', 'TortureButton', 'StoneBridgeButton', 'CryptButton', 'GhostRoomButton',
    'ArenaButton', 'GuardRoomButton', 'InfirmaryButton', 'PrayerTempleButton', 'MerchantButton',
    'HerbGardenButton', 'AlchemyLabButton',
)
ROOM_CENTRE = (
    'GhostRoomButton', 'MerchantButton', 'TavernButton', 'SpaButton',
    'InfirmaryButton', 'AlchemyLabButton', 'CasinoButton', 'WorkshopButton',
)


def main():
    """Check all 24 room icon mappings and the in-game/editor presentation points."""
    assert len(MAPPINGS) == 24, 'fixed inventory contains 24 room icons'
    icon_root = ROOT / 'gui' / 'RoomCentreIcons'
    icon_names = {path.name for path in icon_root.glob('*.png')}
    assert icon_names == {value[0] for value in MAPPINGS.values()}, 'all 24 chosen A1 files are mapped once'

    scheme = ET.parse(ROOT / 'gui' / 'ODSkin.scheme').getroot()
    imagesets = {node.get('name'): node.get('filename') for node in scheme.findall('Imageset')}
    distinct_pixels = set()
    for button, (filename, image_ref) in MAPPINGS.items():
        imageset_name, image_name = image_ref.split('/', 1)
        assert imageset_name in imagesets, button + ': imageset registered in ODSkin.scheme'
        imageset_path = ROOT / 'gui' / imagesets[imageset_name]
        imageset = ET.parse(imageset_path).getroot()
        assert imageset.get('imagefile') == 'RoomCentreIcons/' + filename, button + ': selected A1 PNG is the source'
        image = imageset.find("Image[@name='" + image_name + "']")
        assert image is not None, button + ': mapped CEGUI image exists'
        picture_path = icon_root / filename
        with Image.open(picture_path) as picture:
            picture.load()
            digest = sha256(picture.convert('RGBA').tobytes()).hexdigest()
            if button != 'TempleButton':
                assert digest not in distinct_pixels, button + ': distinct in-game icon pixels'
                distinct_pixels.add(digest)
        print('PASS mapping ' + button + ' -> ' + filename + ' -> ' + image_ref)
    assert len(distinct_pixels) == 23, '23 in-game build bar icons are pixel-distinct'

    gui_source = (ROOT / 'source' / 'render' / 'Gui.cpp').read_text(encoding='utf-8')
    arrange = re.search(r'void Gui::arrangeRoomButtons\(CEGUI::Window\* rooms\)(.*?)\n\}', gui_source, re.S)
    assert arrange is not None, 'in-game room build bar arrangement exists'
    arranged_buttons = [button for button in re.findall(r'"([A-Za-z]+Button)"', arrange.group(1))
        if button != 'DestroyRoomButton']
    assert arranged_buttons == list(BUILD_BAR), 'build bar contains exactly the 23 mapped room buttons'

    rooms = ET.parse(ROOT / 'gui' / 'WindowTabRooms.layout').getroot()
    room_buttons = {node.get('name'): node for node in rooms.iter('Window') if node.get('name') in MAPPINGS}
    assert len(room_buttons) == 24, 'all 23 build buttons and editor TempleButton exist'
    for button in BUILD_BAR:
        assert room_buttons[button].find("Property[@name='NormalImage']").get('value') == MAPPINGS[button][1], \
            button + ': in-game build bar uses the selected icon'
    assert room_buttons['TempleButton'].find("Property[@name='NormalImage']").get('value') == MAPPINGS['TempleButton'][1], \
        'editor TempleButton uses the selected temple icon'
    editor = (ROOT / 'source' / 'modes' / 'EditorMode.cpp').read_text(encoding='utf-8')
    assert 'getChild(Gui::BUTTON_TEMPLE)->show()' in editor, 'TempleButton is shown in the editor'

    research = ET.parse(ROOT / 'gui' / 'WindowSkillTree.layout').getroot()
    research_buttons = {node.get('name'): node for node in research.iter('Window') if node.get('name') in MAPPINGS}
    assert len(research_buttons) == 23, 'research tree contains all 23 in-game room buttons'
    for button in BUILD_BAR:
        assert research_buttons[button].find("Property[@name='ButtonImage']").get('value') == MAPPINGS[button][1], \
            button + ': research tree uses the selected icon'

    manager = (ROOT / 'source' / 'modes' / 'GameModeRoomManager.cpp').read_text(encoding='utf-8')
    icon_array = re.search(r'ROOM_ICONS\[\]\s*=\s*\{(.*?)\};', manager, re.S)
    assert icon_array is not None, 'room centre list icon mapping exists'
    centre_refs = re.findall(r'"([^"]+)"', icon_array.group(1))
    expected_refs = [MAPPINGS[button][1] for button in ROOM_CENTRE]
    assert centre_refs == expected_refs, 'room centre list uses the matching selected icon for all eight rows'
    assert 'setProperty("Image", ROOM_ICONS[index])' in manager, 'room centre rows display their mapped icon'
    traps = (ROOT / 'gui' / 'WindowTabTraps.layout').read_text(encoding='utf-8')
    assert "image='" + MAPPINGS['WorkshopButton'][1] + "'" in traps, 'workshop room icon use in traps tab is replaced'

    print('DONE mappings=24 build-bar=23 distinct=23 editor-temple=PASS room-centre=8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
