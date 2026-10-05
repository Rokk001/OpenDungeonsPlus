#!/usr/bin/env python3
# Checks the hatchery animal sounds: the files exist, have a CREDITS entry, and the server plays every family.
from pathlib import Path

root = Path(__file__).resolve().parents[2]
credits = (root / 'CREDITS').read_text()
room = (root / 'source/rooms/RoomHatchery.cpp').read_text() if (root / 'source/rooms/RoomHatchery.cpp').exists() else ''

families = ('Crow', 'Protest', 'Cluck', 'FoodCall', 'Peep', 'EggCrack')
for family in families:
    folder = root / 'sounds/Spatial/Rooms/Hatchery' / family
    files = sorted(folder.glob('*.ogg'))
    assert len(files) >= 2, family
    for ogg in files:
        assert ogg.stat().st_size > 1000, ogg
        assert ogg.stat().st_size < 60000, ogg
        assert 'sounds/Spatial/Rooms/Hatchery/%s/%s' % (family, ogg.name) in credits, ogg.name
assert 'tools/hatchery/gen_hatchery_sounds.py' in credits
assert (root / 'tools/hatchery/gen_hatchery_sounds.py').exists()

# The server plays them through the room sound message (family "Rooms/Hatchery/<Family>")
for family in families:
    assert '"Hatchery/%s"' % family in room, family
# the rooster in the keeper's hand protests with a family of his own, not with the hen cackle
assert 'fireRoomSound(tile, "Hatchery/Protest")' in room
print('hatchery sounds ok')
