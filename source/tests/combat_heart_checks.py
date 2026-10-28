"""Shared source checks and configured-health stubs for optional heart probes."""

import re


def check_heart_configuration(repo):
    """Verify configured health and its unchanged independent building damage path."""
    rooms = (repo / 'config/rooms.cfg').read_text()
    values = re.findall(r'^\s*DungeonHeartHP\s+(\S+)', rooms, re.M)
    assert len(values) == 1 and float(values[0]) == 15100.0, 'configured heart health'
    source = (repo / 'source/rooms/RoomDungeonTemple.cpp').read_text()
    assert '#include "utils/ConfigManager.h"' in source, 'heart configuration requires its complete declaration'
    assert 'getRoomConfigDoubleOrDefault("DungeonHeartHP", 15100.0)' in source
    # The heal rate and the research of the heart health and healing come from the configuration and skills.cfg
    values = re.findall(r'^\s*DungeonHeartHealPerSecond\s+(\S+)', rooms, re.M)
    assert len(values) == 1 and float(values[0]) == 3.775, 'configured heart healing'
    assert 'getRoomConfigDouble("DungeonHeartHealPerSecond")' in source
    assert 'HEART_HEAL_PER_SECOND' not in source
    assert 'ResearchEffect::HeartHP' in source and 'ResearchEffect::HeartHeal' in source
    assert 'const double RoomDungeonTemple::HEART_MAX_HP' not in source
    assert 'physicalDamage - getPhysicalDefense()' in source
    assert 'magicalDamage - getMagicalDefense()' in source
    assert 'elementDamage - getElementDefense()' in source
    assert 'attacker == nullptr || !canAttackHeart(' in source
    assert 'HeartHealthShare' in source and 'HeartHealth10000' in source and 'getHeartMaxHP()' in source
    building = (repo / 'source/entities/Building.cpp').read_text()
    # The tile hit points of portals, bridges and traps are config keys of 10, no literal is left in Building.cpp
    assert 'DEFAULT_TILE_HP' not in building
    rooms = (repo / 'config/rooms.cfg').read_text()
    assert re.search(r'^\s*PortalHP\s+10(?:\.0)?\s*$', rooms, re.M)


def configure_heart_probe(probe):
    """Supply the production configuration getter to the optional compiled fixture."""
    getter = '''
 // Return the checked default health without loading unrelated game configuration.
 double getRoomConfigDoubleOrDefault(const std::string&, double fallback) const { return fallback; }
 // Return the configured heal rate (the only room value the heart reads with this getter).
 double getRoomConfigDouble(const std::string& key) const { return key == "DungeonHeartHealPerSecond" ? 3.775 : 0.0; }
'''
    # The research of the heart: the fixture skill manager applies a factor per effect (1 = no research); the skill
    # type arguments of the production code are replaced by a plain number because the fixtures declare no skill types
    research = '''
#include <string>
namespace ResearchEffect { static const std::string HeartHP = "HeartHP"; static const std::string HeartHeal = "HeartHeal"; }
// Factors of the fixture research, set by the checks.
static double gResearchHeartHP = 1.0;
static double gResearchHeartHeal = 1.0;
struct SkillManager {
 template<class SeatType, class SkillArg>
 static double getResearchValue(SeatType, SkillArg, double base, const std::string& effect)
 { return base * (effect == ResearchEffect::HeartHP ? gResearchHeartHP : (effect == ResearchEffect::HeartHeal ? gResearchHeartHeal : 1.0)); }
};
'''
    probe = probe.replace('SkillType::keeperHeartFortitude', '0').replace('SkillType::keeperHeartMending', '0')
    if 'struct ConfigManager {' in probe:
        return probe.replace('struct ConfigManager {', research + 'struct ConfigManager {' + getter, 1)
    return research + '''struct ConfigManager {
 // Provide the configuration singleton used by the extracted production getter.
 static ConfigManager& getSingleton() { static ConfigManager config; return config; }
''' + getter + '};\n' + probe
