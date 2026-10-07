"""Wiring checks for the gold dust over the heart and portal of other keepers (text only, no compiler needed).
Server: only the wealth tier goes out, only to the seats that see the tile. Client: only while the tile is in view."""
from pathlib import Path
import re

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding='utf-8')


wealth = read('source/rooms/KeeperWealth.h')
event_h = read('source/network/CosmeticEvent.h')
event_cpp = read('source/network/CosmeticEvent.cpp')
room = read('source/rooms/Room.cpp')
temple = read('source/rooms/RoomDungeonTemple.cpp')
portal = read('source/rooms/RoomPortal.cpp')
client = read('source/network/ODClient.cpp')
render = read('source/render/RenderManager.cpp')
rules = read('source/render/TreasuryCreatureRules.h')

# Event number: appended after the casino result, known to isKnownType and named
assert re.search(r'roomTakeover = 14,.*?casinoResult = 15,.*?keeperWealth = 16,', event_h, re.S)
assert 'CosmeticEventType::keeperWealth)' in event_cpp and 'return "keeperWealth";' in event_cpp

# One rule for "rich" on both sides; the tier is small, the amount is not part of the event
assert 'inline int tier(int gold, int goldMax)' in wealth
assert 'KeeperWealth::tier(gold, goldMax) > 0' in rules

# Server: tier only, only to the seats that see the tile, never to the owner, not at all while not rich
send = room[room.index('void Room::announceKeeperWealth'):]
send = send[:send.index('\n}\n')]
assert 'CosmeticEventType::keeperWealth' in send
assert 'event.mValue2 = tier;' in send
assert 'getGold()' in send and send.count('getGold()') == 1 and 'KeeperWealth::tier(' in send
assert 'event.mValue = getSeat()->getId();' in send
assert 'getTotalGold' not in send and 'mText' not in send and 'mValue = getSeat()->getGold' not in send
assert 'tile->getSeatsWithVision()' in send
assert 'getSeatsWithVision' in send and 'getSeats()' not in send and 'getPlayers' not in send
assert 'seat == getSeat()' in send and 'getIsHuman()' in send
assert 'if(tier <= 0)' in send and 'return;' in send.split('if(tier <= 0)')[1][:40]
assert 'announceKeeperWealth(getHeartTile());' in temple
assert 'announceKeeperWealth(getCentralTile());' in portal

# Client: the event is handled in game mode, the dust needs a tile in view of the local keeper (fog), own buildings
# keep using the own gold
handler = client[client.index('case ServerNotificationType::cosmeticEvent:'):]
handler = handler[:handler.index('case ServerNotificationType::seatTeam:')]
assert 'CosmeticEventType::keeperWealth' in handler and 'noteKeeperWealth(event.mObject, event.mValue, event.mValue2)' in handler
note = render[render.index('void RenderManager::noteKeeperWealth'):]
note = note[:note.index('\n}\n')]
assert 'getSeat()->getId() == seatId' in note and 'KeeperWealth::announceLifetime' in note
dust = render[render.index('void RenderManager::startForeignWealthDust'):]
dust = dust[:dust.index('\n}\n')]
assert 'getLocalPlayerHasVision()' in dust and dust.index('getLocalPlayerHasVision()') < dust.index('createTreasuryEffect(')
assert 'TreasuryEffectKind::dust' in dust and '"TreasuryHeartDust"' in dust and '"TreasuryGoldDust"' in dust
assert 'getGold' not in dust
upd = render[render.index('void RenderManager::updateTreasuryDust'):]
upd = upd[:upd.index('std::vector<TreasuryGoldMesh::FullPile> piles;')]
assert upd.index('mForeignWealth') < upd.index('mTreasuryDustTimer += ')
assert 'startForeignWealthDust();' in upd
assert 'mForeignWealth.clear();' in render
print('check_foreign_gold_dust ok')
