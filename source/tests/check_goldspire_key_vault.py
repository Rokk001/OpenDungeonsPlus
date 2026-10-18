"""Check the approved vault geometry and key route without compiling or starting a game."""
from pathlib import Path
import re
import check_campaign_playability as campaign

root = Path(__file__).resolve().parents[2]
text = (root / "levels/campaign/Goldspire.level").read_text(encoding="utf-8")
level = campaign.parse_level(text)
walls = {(x, y) for x in range(49, 56) for y in range(28, 32)
         if x in (49, 55) or y in (28, 31)} - {(49, 30)}
assert len(walls) == 17
assert all(level["tiles"][tile][:2] == (3, 100.0) for tile in walls)
vault = next(room for room in level["rooms"] if room[1] == "Treasury6")
assert vault[2] == 2 and set(vault[3]) == {(x, y) for x in range(50, 55) for y in (29, 30)}
assert len(vault[3]) == 10
assert level["seats"][2]["gold"] == "0"
# The original ten-tile treasury has no per-tile gold data or separate stored gold entities.
room = next(block for block in re.findall(r"\[Room\](.*?)\[/Room\]", text, re.S)
            if "Treasury6" in block)
assert len(campaign.lines(room)) == 11
assert not campaign.lines(campaign.section(text, "TreasuryObject"))
assert ("AlaricPenn", 2, (48, 30)) in level["creatures"]
assert re.search(r"4\s+PennVaultDoor\s+2\s+1\s+49\s+30\s+1\s+1 KeyLock 1", text)
assert "Action\tstonedrop\tAlaricPenn\ttreasurer-key\t1\t48\t30" in text
assert "Cond\tdeliveredstone\ttreasurer-key\nAction\tkeydoor\tPennVaultDoor\topen" in text
assert "Name\tmainWarden\nMode\trepeat\t0\nCond\ttrigger\tpennVaultOpened" in text
# Model only the existing progression openings; the proposed vault door stays blocked.
closed = dict(level, tiles=dict(level["tiles"]))
for x1, y1, x2, y2 in ((47, 56, 49, 56), (11, 52, 12, 67), (80, 58, 81, 72)):
    for x in range(x1, x2 + 1):
        for y in range(y1, y2 + 1):
            closed["tiles"][x, y] = (1, 0.0, None)
closed["tiles"][49, 30] = (3, 100.0, None)
area, _ = campaign.reachable(closed)
assert (48, 30) in area and not any(tile in area for tile in vault[3])
opened = dict(closed, tiles=dict(closed["tiles"]))
opened["tiles"][49, 30] = (1, 0.0, None)
area, _ = campaign.reachable(opened)
assert all(tile in area for tile in vault[3])
assert level["tiles"][48, 30][1] == 0
# Ordinary slapping, fighting, capture and enemy path exceptions must not bypass the key.
door = (root / "source/traps/TrapDoor.cpp").read_text(encoding="utf-8")
header = (root / "source/traps/TrapDoor.h").read_text(encoding="utf-8")
assert "if(mKeyLocked)\n        return 0.0;" in door
assert "if(mKeyLocked || mDoorType == TrapType::doorBarricade)" in door
assert "return !mKeyLocked && Trap::isClaimable(seat);" in door
assert "if(!mKeyLocked)\n        Trap::claimForSeat" in door
assert "return !mKeyLocked && (!isActivated(tile)" in header
assert 'os << " KeyLock 1"' in door and 'marker != "KeyLock"' in door
assert "mKeyLocked ? ANIMATION_CLOSE : ANIMATION_OPEN" in door
# Reuse the physical transport save and interruption contract, never an invisible carrier token.
stone = (root / "source/entities/MissileStone.cpp").read_text(encoding="utf-8")
assert "MissionTransport" in stone and "mDelivered" in stone and "mCarried = false" in stone
assert "notifyEntityCarryOff" in stone and "isWorker" in stone
assert not campaign.grouped_goal_errors(text, "Goldspire")
print("Goldspire vault: geometry, initial gold, closed/open routes, exact key, victory gate and saved lock checked")
