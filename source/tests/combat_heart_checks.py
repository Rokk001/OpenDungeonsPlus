"""Shared source checks and configured-health stubs for optional heart probes."""

import re


def check_heart_configuration(repo):
    """Verify configured health and its unchanged independent building damage path."""
    rooms = (repo / 'config/rooms.cfg').read_text()
    values = re.findall(r'^\s*DungeonHeartHP\s+(\S+)', rooms, re.M)
    assert len(values) == 1 and float(values[0]) == 10000.0, 'configured heart health'
    source = (repo / 'source/rooms/RoomDungeonTemple.cpp').read_text()
    assert 'getRoomConfigDoubleOrDefault("DungeonHeartHP", 10000.0)' in source
    assert 'const double RoomDungeonTemple::HEART_MAX_HP' not in source
    assert 'physicalDamage - getPhysicalDefense()' in source
    assert 'magicalDamage - getMagicalDefense()' in source
    assert 'elementDamage - getElementDefense()' in source
    assert 'attacker == nullptr || !canAttackHeart(' in source
    assert 'HeartHealth10000' in source and 'getHeartMaxHP()' in source
    building = (repo / 'source/entities/Building.cpp').read_text()
    assert re.search(r'Building::DEFAULT_TILE_HP\s*=\s*10\.0', building)


def configure_heart_probe(probe):
    """Supply the production configuration getter to the optional compiled fixture."""
    getter = '''
 // Return the checked default health without loading unrelated game configuration.
 double getRoomConfigDoubleOrDefault(const std::string&, double fallback) const { return fallback; }
'''
    if 'struct ConfigManager {' in probe:
        return probe.replace('struct ConfigManager {', 'struct ConfigManager {' + getter, 1)
    return '''#include <string>
struct ConfigManager {
 // Provide the configuration singleton used by the extracted production getter.
 static ConfigManager& getSingleton() { static ConfigManager config; return config; }
''' + getter + '};\n' + probe
