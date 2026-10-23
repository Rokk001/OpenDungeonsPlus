"""Shared helper of the compiled check probes: a stand-in for the ConfigManager that CreatureProgression.h includes."""
from pathlib import Path
import re


def global_cfg_number(root, key):
    """Return the numeric value of a key of config/global.cfg (the probes use the shipped values)."""
    match = re.search(r'^\s*' + re.escape(key) + r'\s+([-\d.eE]+)', (root / 'config/global.cfg').read_text(), re.M)
    assert match, key
    return float(match[1])


def config_manager_stub(root):
    """Return C++ source that defines a minimal ConfigManager (and its include guard) with the growth keys of global.cfg.

    The real header needs Ogre and Boost; the probes only need the four getters used by CreatureProgression.h.
    """
    return '''
#define CONFIGMANAGER_H
#include <algorithm>
class ConfigManager {
public:
 static ConfigManager& getSingleton(){static ConfigManager instance;return instance;}
 double getCreatureDamageGrowth() const {return %r;}
 double getCreatureDamageExponent() const {return %r;}
 double getCreatureHpGrowthPerLevel() const {return %r;}
 double getCooldownReductionPerLevel() const {return std::max(0.0,std::min(1.0,%r));}
};
''' % (global_cfg_number(root, 'CreatureDamageGrowth'), global_cfg_number(root, 'CreatureDamageExponent'),
       global_cfg_number(root, 'CreatureHpGrowthPerLevel'), global_cfg_number(root, 'CooldownReductionPerLevel'))
