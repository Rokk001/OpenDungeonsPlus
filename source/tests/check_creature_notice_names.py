"""Static checks for client profile names in creature notices; no compilation."""
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[2]


# Read production code without launching a compiler or game.
def read(name):
    return (ROOT / name).read_text(encoding="utf-8")


# Restrict checks to the requested function.
def body(text, name):
    text = text[text.index(name):]
    return text[:text.index("\n}\n")]


player = read("source/game/Player.cpp")
notice = body(player, "void Player::notifyCreatureEvent(")
assert "ServerNotificationType::creatureNotice" in notice
assert "creature.getName() << definition->getClassName() << definition->isWorker() << suffix" in notice
assert "SocialProfileCache" not in notice
killed = body(player, "void Player::notifyCreatureKilled(")
assert 'notifyCreatureEvent(creature, " has been killed");' in killed
assert killed.index("mCreatureKilledTime > 0.0f") < killed.index("notifyCreatureEvent(")
creature = read("source/entities/Creature.cpp")
for name, suffix in (("LeftDungeon", " left your dungeon"), ("LeavingDungeon", " is leaving your dungeon"),
                     ("BecameRogue", " is not under your control anymore !"),
                     ("Unhappy", " is unhappy !"), ("Furious", " is furious !")):
    function = body(creature, "void Creature::fireChatMsg" + name + "()")
    assert 'notifyCreatureEvent(*this, "' + suffix + '");' in function
    assert "getName()" not in function
    assert "getHasLost()" in function and "getIsHuman()" in function
client = read("source/network/ODClient.cpp")
notice = client.split("case ServerNotificationType::creatureNotice:", 1)[1].split("case ServerNotificationType::chatServer:", 1)[0]
assert "packetReceived >> creatureName >> className >> worker >> suffix" in notice
assert "SocialProfileCache::getSingleton().getProfile(" in notice
assert "creatureName, className, worker).getFullName()" in notice
assert "name + suffix" in notice and "EventShortNoticeType::aboutCreatures" in notice
assert "getCreature(" not in notice, "notice must still resolve after the client entity disappears"
assert "cache.getProfile(getName(), definition->getClassName(), definition->isWorker())" in creature
header = read("source/network/ServerNotification.h")
assert re.search(r"campaignVictory,\s*//![^\n]*\n\s*creatureNotice\s*}", header)
assert 'return "creatureNotice";' in read("source/network/ServerNotification.cpp")
print("Creature notice names use the same client profile as the creature card: static PASS")
print("Existing text, severity and death throttling retained; runtime verification pending")
