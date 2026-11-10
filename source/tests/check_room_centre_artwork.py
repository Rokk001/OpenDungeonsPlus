"""Check the fixed room manager artwork inventory, native sizes and asset credits."""

from pathlib import Path
import re
import sys

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_ASSETS = 31
ICONS = (
    'alchemy-lab', 'arena', 'casino', 'crypt', 'dormitory', 'ghost-room',
    'guard-room', 'hatchery', 'herb-garden', 'infirmary', 'library', 'merchant',
    'prayer-temple', 'prison', 'spa', 'stone-bridge', 'tavern', 'temple',
    'toilet', 'torture-chamber', 'training-hall', 'treasury', 'wooden-bridge',
    'workshop',
)
ARTWORK = (
    ('spa-bath.png', (118, 118)),
    ('ghost-mana-crystal.png', (52, 45)),
    ('ghost-research-book.png', (39, 33)),
    ('ghost-level-crystal.png', (38, 40)),
    ('ghost-vessel.png', (173, 233)),
    ('casino-smiles.png', (128, 100)),
    ('casino-money.png', (128, 100)),
)


def check_asset(relative, size, credits):
    """Require a readable image at its fixed size and its own complete credit row."""
    path = ROOT / relative
    if not path.is_file():
        raise AssertionError('missing ' + relative)
    with Image.open(path) as picture:
        assert picture.format == 'PNG', relative + ': PNG format'
        assert picture.size == size, '%s: expected %s, got %s' % (relative, size, picture.size)
        picture.load()
    rows = [row for row in credits if row.split() and row.split()[0] == relative]
    assert len(rows) == 1, relative + ': exactly one CREDITS row'
    assert re.fullmatch(
        re.escape(relative) + r'\s+AI-generated with Codex\s+GPLv3\+\s+'
        r'Painted for this project \(\d{4}-\d{2}-\d{2}\)', rows[0]
    ), relative + ': author, licence and source'


def main():
    """Check all 31 required files without hiding missing artwork behind passing icons."""
    credits = (ROOT / 'CREDITS').read_text(encoding='utf-8').splitlines()
    inventory = [('gui/RoomCentreIcons/' + name + '.png',
                  (128, 128) if name == 'ghost-room' else (256, 256)) for name in ICONS]
    inventory.extend(('gui/RoomCentreArtwork/' + name, size) for name, size in ARTWORK)
    assert len(inventory) == EXPECTED_ASSETS, 'complete fixed artwork inventory'
    failed = 0
    for relative, size in inventory:
        try:
            check_asset(relative, size, credits)
            print('PASS ' + relative)
        except (AssertionError, OSError) as error:
            print('FAIL ' + str(error))
            failed += 1
    print('DONE total=%d red=%d' % (EXPECTED_ASSETS, failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
