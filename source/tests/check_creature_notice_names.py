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
notice = body(player, "void Player::notifyCreatureEvent(Creature& creature, const std::string& suffix, EventShortNoticeType noticeType)")
assert "ServerNotificationType::chatServer" in notice
assert "<< suffix << noticeType << creature.getName() << definition->getClassName() << definition->isWorker()" in notice
assert "SocialProfileCache" not in notice
short = body(player, "void Player::notifyCreatureEvent(Creature& creature, const std::string& suffix)")
assert "notifyCreatureEvent(creature, suffix, EventShortNoticeType::aboutCreatures);" in short
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
fee = body(creature, "void Creature::fireChatMsgTookFee(int goldTaken)")
assert "getPlayer()->notifyCreatureEvent(*this, suffix);" in fee
assert "getName()" not in fee and "chatServer" not in fee
assert '" took its fee: "' in fee and '" from its fee"' in fee
for kind, suffix in (("Bed", " cannot find room for a bed. Build or enlarge a Dormitory."),
                     ("Food", " cannot find food. Build a Hatchery.")):
    supply = body(player, "void Player::notifyCreatureCannotFind" + kind + "(")
    assert 'notifyCreatureEvent(creature, "' + suffix + '", EventShortNoticeType::genericGameInfo);' in supply
    assert "creature.getName()" not in supply
    assert "mCreatureCannotFind" + kind + " <= 0.0f" in supply
    assert "SoundRelativeKeeperStatements::CreatureNo" + kind in supply
assert "enum class EventShortNoticeType : int32_t;" in read("source/game/Player.h")

client = read("source/network/ODClient.cpp")
notice = client.split("case ServerNotificationType::chatServer:", 1)[1].split("case ServerNotificationType::newMap:", 1)[0]
assert "packetReceived >> evtMsg >> type" in notice
assert "if(!packetReceived.endOfPacket())" in notice
assert "packetReceived >> creatureName >> className >> worker" in notice
assert "SocialProfileCache::getSingleton().getProfile(" in notice
assert "creatureName, className, worker).getFullName() + evtMsg" in notice
assert "getCreature(" not in notice, "notice must still resolve after the client entity disappears"
# The creature card resolves its title with the same cache key and arguments
assert "cache.getProfile(getName(), definition->getClassName(), definition->isWorker())" in creature
# No new notification value: the enum order checks stay untouched
assert "creatureNotice" not in read("source/network/ServerNotification.h")

# No server notice may still put an internal creature name into its text
for path in sorted((ROOT / "source").rglob("*.cpp")):
    # Log statements are not shown to the player
    text = re.sub(r"OD_LOG_\w+\([^;]*;", "", path.read_text(encoding="utf-8", errors="replace"))
    for match in re.finditer(r"ServerNotificationType::chatServer", text):
        window = text[max(0, match.start() - 600):match.end() + 600]
        assert not re.search(r"getName\(\)\s*\+\s*\"", window), "internal creature name in a notice: %s" % path
print("Death, problem, departure, fee, food and bed notices use the profile name of the creature card: static PASS")
print("Existing text, category, cooldowns and voice retained; runtime verification pending")
