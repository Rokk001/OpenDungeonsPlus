"""Static check: a client tile that looks claimed but has no known owner does not crash Tile::isClaimedForSeat.

On the client Tile::isClaimed() decides by the tile visual, but the server sends the tile owner only for some
visuals (Seat::exportTileToPacket; not at all with hideSeatId), and Tile::updateFromPacket sets the seat to nullptr
when it gets none. A merchant, herb garden or alchemy lab tile is such a tile: a worker reinforcing a wall next to
one ran WorkerReactions::showClaim -> isClaimedForSeat -> getSeat()->canOwnedTileBeClaimedBy and crashed the game
(load test of TestItemsPotions.level). isClaimedForSeat must therefore test the owner for nullptr before it uses it.
It does not start a game and compiles nothing."""
from pathlib import Path
import re
import sys

repo = Path(__file__).resolve().parents[2]


def function(text, start):
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def strip_comments(text):
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    return re.sub(r'//[^\n]*', '', text)


failures = []


def check(condition, message):
    if not condition:
        failures.append(message)


tile = strip_comments((repo / 'source/entities/Tile.cpp').read_text(encoding='utf-8'))
seat = strip_comments((repo / 'source/game/Seat.cpp').read_text(encoding='utf-8'))

# The premise: the client tile can be claimed by its visual while its seat is nullptr
claimed = function(tile, tile.index('bool Tile::isClaimed()'))
client_part = claimed[:claimed.index('getSeat()')] if 'getSeat()' in claimed else claimed
client_claimed = set(re.findall(r'TileVisual::(\w+)', client_part))
check('getIsOnServerMap()' in claimed and 'claimedGround' in client_claimed,
      'Tile::isClaimed decides by the tile visual on the client')
update = function(tile, tile.index('void Tile::updateFromPacket('))
check(re.search(r'seatId\s*==\s*-1\s*\)\s*\{?\s*setSeat\(\s*nullptr\s*\)', update) is not None,
      'Tile::updateFromPacket sets the seat to nullptr when the server sends no owner (seatId -1)')
export = function(seat, seat.index('void Seat::exportTileToPacket('))
check('hideSeatId' in export and 'tileSeatId = -1' in export.replace('int tileSeatId', 'tileSeatId'),
      'Seat::exportTileToPacket sends seatId -1 for hidden owners and for unlisted visuals')
switch = export[export.index('switch(tileState.mTileVisual)'):export.index('default:')]
sent = set(re.findall(r'TileVisual::(\w+)', switch))
unknown_owner = sorted(client_claimed - sent)

# The fix: isClaimedForSeat tests the owner before it calls a method on it
body = function(tile, tile.index('bool Tile::isClaimedForSeat('))
body = body[body.index('{'):]
check('getSeat()->' not in body.replace(' ', ''),
      'Tile::isClaimedForSeat does not call a method on getSeat() without a nullptr test')
use = re.search(r'(\w+)\s*->\s*canOwnedTileBeClaimedBy\(', body)
check(use is not None, 'Tile::isClaimedForSeat asks the owner canOwnedTileBeClaimedBy')
if use is not None:
    owner = re.escape(use.group(1))
    assigned = re.search(r'\b%s\s*=\s*getSeat\(\)' % owner, body)
    guard = re.search(r'\b%s\s*==\s*nullptr|nullptr\s*==\s*%s\b|!\s*%s\b' % (owner, owner, owner), body)
    check(assigned is not None and assigned.start() < use.start(),
          'Tile::isClaimedForSeat takes the owner from getSeat()')
    check(guard is not None and guard.start() < use.start(),
          'Tile::isClaimedForSeat returns false for a tile without a known owner before it reads the owner')

if failures:
    for failure in failures:
        print('FAIL: ' + failure)
    sys.exit(1)
print('check_tile_claimed_unknown_owner: OK (client visuals without owner: %s)' % ', '.join(unknown_owner or ['none']))
