#!/usr/bin/env python3
"""Checks the configuration values, readers and removed constants of the balance settings.

The table records the delivered settings once; no external plan or compiler is needed.
"""

from pathlib import Path
import math
import re
import sys

ROOT = Path(__file__).resolve().parents[2]

# Item, config file, entity, key, shipped value, original reader anchor.
SETTINGS = [
    (1, 'config/creatureSkills.cfg', 'AuraAlly', 'MinAllies', '2', 'source/creatureskill/CreatureSkillAuraAlly.cpp'),
    (2, 'config/creatureSkills.cfg', 'SkeletonArmy', 'Radius', '2', 'source/creatureskill/CreatureSkillSkeletonArmy.cpp'),
    (3, 'config/global.cfg', '-', 'AngryFleeChancePercent', '20', 'source/creaturebehaviour/CreatureBehaviourAttackEnemy.cpp'),
    (4, 'config/global.cfg', '-', 'BuildingDamageCurve', '1 1.25 1.5 1.75 2 2.25 2.5 3 4 6', 'source/entities/CreatureProgression.h'),
    (5, 'config/global.cfg', '-', 'FleeTiles', '5', 'source/creatureaction/CreatureActionFlee.cpp'),
    (6, 'config/global.cfg', '-', 'HitChanceMax', '95', 'source/entities/DefenceChance.h'),
    (6, 'config/global.cfg', '-', 'HitChanceMin', '5', 'source/entities/DefenceChance.h'),
    (6, 'config/global.cfg', '-', 'HitChanceScale', '200', 'source/entities/DefenceChance.h'),
    (7, 'config/global.cfg', '-', 'NaturalEnemyEngageChance', '0.2079207920792079', 'source/creaturebehaviour/CreatureBehaviourEngageNaturalEnemy.cpp'),
    (8, 'config/global.cfg', '-', 'SkillDeviationPoints', '20', 'source/creatureskill/CreatureSkillTree.cpp'),
    (8, 'config/global.cfg', '-', 'SkillResetMinFollowers', '3', 'source/creatureskill/CreatureSkillTree.cpp'),
    (8, 'config/global.cfg', '-', 'SkillUnfollowedWeight', '3', 'source/creatureskill/CreatureSkillTree.cpp'),
    (9, 'config/global.cfg', '-', 'SkillTier2UnlockRanks', '1', 'source/creatureskill/CreatureSkillTree.cpp'),
    (9, 'config/global.cfg', '-', 'SkillTier3UnlockRanks', '2', 'source/creatureskill/CreatureSkillTree.cpp'),
    (9, 'config/global.cfg', '-', 'SkillTier4MinSpent', '20', 'source/creatureskill/CreatureSkillTree.cpp'),
    (10, 'config/global.cfg', '-', 'SlapJobCooldownFactor', '0.8', 'source/entities/Creature.cpp'),
    (11, 'config/global.cfg', '-', 'SlapMemoryMax', '10', 'source/entities/Creature.cpp'),
    (12, 'config/global.cfg', '-', 'SupportTargetDistanceFactor', '0.5', 'source/entities/Creature.cpp'),
    (13, 'config/global.cfg', '-', 'TargetThreatFactorMax', '2', 'source/entities/Creature.cpp'),
    (13, 'config/global.cfg', '-', 'TargetThreatFactorMin', '0.5', 'source/entities/Creature.cpp'),
    (14, 'config/global.cfg', '-', 'ThreatPercentByLevel', '100 125 150 175 200 225 250 300 400 500', 'source/entities/Creature.cpp'),
    (15, 'config/global.cfg', '-', 'WeakFleeChancePercent', '20', 'source/creaturebehaviour/CreatureBehaviourFleeWhenWeak.cpp'),
    (16, 'config/global.cfg', '-', 'WorkerCarryFirstMaxShare', '0.2', 'source/game/WorkerShare.h'),
    (16, 'config/global.cfg', '-', 'WorkerClaimWallFirstMinShare', '0.8', 'source/game/WorkerShare.h'),
    (17, 'config/global.cfg', '-', 'SandboxHeroLevelMax', '10', 'source/gamemap/SandboxMode.cpp'),
    (18, 'config/global.cfg', '-', 'SandboxHeroLevelMin', '1', 'source/gamemap/SandboxMode.cpp'),
    (19, 'config/global.cfg', '-', 'SandboxHeroesPerWave', '8', 'source/gamemap/SandboxMode.cpp'),
    (20, 'config/global.cfg', '-', 'SandboxWaves', '10', 'source/gamemap/SandboxMode.cpp'),
    (21, 'config/relationships.cfg', '-', 'BrawlStartHealthMarginPercent', '25', 'source/game/CreatureRelationships.cpp'),
    (22, 'config/rooms.cfg', '-', 'RoomSellRefundShare', '0.5', 'source/rooms/RoomManager.cpp'),
    (23, 'config/rooms.cfg', 'Casino', 'CasinoBrokeFightPercent', '50', 'source/rooms/RoomCasino.cpp'),
    (24, 'config/rooms.cfg', 'DungeonHeart', 'DungeonHeartGoldPerTile', '1000', 'source/rooms/RoomDungeonTemple.cpp'),
    (25, 'config/rooms.cfg', 'DungeonHeart', 'HeartRewardWeightGold', '15', 'source/rooms/RoomDungeonTemple.cpp'),
    (25, 'config/rooms.cfg', 'DungeonHeart', 'HeartRewardWeightHealAll', '8', 'source/rooms/RoomDungeonTemple.cpp'),
    (25, 'config/rooms.cfg', 'DungeonHeart', 'HeartRewardWeightKillCreatures', '2', 'source/rooms/RoomDungeonTemple.cpp'),
    (25, 'config/rooms.cfg', 'DungeonHeart', 'HeartRewardWeightLevelUp', '6', 'source/rooms/RoomDungeonTemple.cpp'),
    (25, 'config/rooms.cfg', 'DungeonHeart', 'HeartRewardWeightMakeHappy', '9', 'source/rooms/RoomDungeonTemple.cpp'),
    (25, 'config/rooms.cfg', 'DungeonHeart', 'HeartRewardWeightMakeSafe', '7', 'source/rooms/RoomDungeonTemple.cpp'),
    (25, 'config/rooms.cfg', 'DungeonHeart', 'HeartRewardWeightMakeUnhappy', '4', 'source/rooms/RoomDungeonTemple.cpp'),
    (25, 'config/rooms.cfg', 'DungeonHeart', 'HeartRewardWeightMana', '14', 'source/rooms/RoomDungeonTemple.cpp'),
    (25, 'config/rooms.cfg', 'DungeonHeart', 'HeartRewardWeightReceiveWorkers', '10', 'source/rooms/RoomDungeonTemple.cpp'),
    (25, 'config/rooms.cfg', 'DungeonHeart', 'HeartRewardWeightRevealMap', '12', 'source/rooms/RoomDungeonTemple.cpp'),
    (25, 'config/rooms.cfg', 'DungeonHeart', 'HeartRewardWeightStunWorkers', '6', 'source/rooms/RoomDungeonTemple.cpp'),
    (25, 'config/rooms.cfg', 'DungeonHeart', 'HeartRewardWeightWeakenWalls', '7', 'source/rooms/RoomDungeonTemple.cpp'),
    (26, 'config/rooms.cfg', 'Hatchery', 'HatcheryAdultLostTurns', '30', 'source/entities/ChickenEntity.cpp'),
    (27, 'config/rooms.cfg', 'Hatchery', 'HatcheryCareMaxPercent', '90', 'source/rooms/HatcheryCycle.cpp'),
    (28, 'config/rooms.cfg', 'Hatchery', 'HatcheryStageJitterMaxPercent', '120', 'source/rooms/HatcheryCycle.cpp'),
    (28, 'config/rooms.cfg', 'Hatchery', 'HatcheryStageJitterMinPercent', '80', 'source/rooms/HatcheryCycle.cpp'),
    (29, 'config/rooms.cfg', 'Portal', 'PortalHP', '10', 'source/entities/Building.cpp'),
    (29, 'config/rooms.cfg', 'PortalWave', 'PortalWaveHP', '10', 'source/entities/Building.cpp'),
    (29, 'config/rooms.cfg', 'StoneBridge', 'StoneBridgeHP', '10', 'source/entities/Building.cpp'),
    (29, 'config/rooms.cfg', 'WoodenBridge', 'WoodenBridgeHP', '10', 'source/entities/Building.cpp'),
    (29, 'config/traps.cfg', 'Alarm', 'AlarmHP', '10', 'source/entities/Building.cpp'),
    (29, 'config/traps.cfg', 'Boulder', 'BoulderHP', '10', 'source/entities/Building.cpp'),
    (29, 'config/traps.cfg', 'Cannon', 'CannonHP', '10', 'source/entities/Building.cpp'),
    (29, 'config/traps.cfg', 'Fear', 'FearHP', '10', 'source/entities/Building.cpp'),
    (29, 'config/traps.cfg', 'Fireburst', 'FireburstHP', '10', 'source/entities/Building.cpp'),
    (29, 'config/traps.cfg', 'Freeze', 'FreezeHP', '10', 'source/entities/Building.cpp'),
    (29, 'config/traps.cfg', 'Gas', 'GasHP', '10', 'source/entities/Building.cpp'),
    (29, 'config/traps.cfg', 'Lightning', 'LightningHP', '10', 'source/entities/Building.cpp'),
    (29, 'config/traps.cfg', 'Spike', 'SpikeHP', '10', 'source/entities/Building.cpp'),
    (29, 'config/traps.cfg', 'Trigger', 'TriggerHP', '10', 'source/entities/Building.cpp'),
    (29, 'config/traps.cfg', 'WatchBanner', 'WatchBannerHP', '10', 'source/entities/Building.cpp'),
    (30, 'config/skills.cfg', '-', 'ResearchCostFactorLevel2', '2', 'source/game/Skill.cpp'),
    (30, 'config/skills.cfg', '-', 'ResearchCostFactorLevel3', '4', 'source/game/Skill.cpp'),
    (31, 'config/skills.cfg', '-', 'ResearchLevel2TabShare', '0.5', 'source/game/Seat.cpp'),
    (31, 'config/skills.cfg', '-', 'ResearchLevel3TabShare', '1', 'source/game/Seat.cpp'),
    (32, 'config/spells.cfg', 'SummonWorker', 'SummonWorkerRefundShare', '0.5', 'source/game/Player.cpp'),
    (33, 'config/traps.cfg', '-', 'TrapSellRefundShare', '0.5', 'source/traps/TrapManager.cpp'),
    (34, 'config/traps.cfg', 'Boulder', 'BoulderMaxHits', '10', 'source/entities/MissileBoulder.cpp'),
    (35, 'config/traps.cfg', 'Boulder', 'BoulderWallBreakPercent', '50', 'source/entities/MissileBoulder.cpp'),
    (36, 'config/traps.cfg', 'Lightning', 'LightningWaterDamageFactor', '2', 'source/traps/TrapLightning.cpp'),
    (37, 'config/equipments.cfg', '-', 'BleedTurns', '5', 'source/creatureeffect/CreatureEffectBleed.cpp'),
    (38, 'config/equipments.cfg', '-', 'BulwarkRadius', '2', 'source/entities/Creature.cpp'),
    (38, 'config/equipments.cfg', '-', 'LastStandHealthShare', '0.25', 'source/entities/Creature.cpp'),
    (39, 'config/equipments.cfg', '-', 'ChillFactor', '0.9', 'source/entities/ItemEffects.cpp'),
    (39, 'config/equipments.cfg', '-', 'WeakenFactor', '0.95', 'source/entities/ItemEffects.cpp'),
    (40, 'config/equipments.cfg', '-', 'DexterityPotionCritLarge', '6', 'source/entities/Creature.cpp'),
    (40, 'config/equipments.cfg', '-', 'DexterityPotionCritMedium', '4', 'source/entities/Creature.cpp'),
    (40, 'config/equipments.cfg', '-', 'DexterityPotionCritSmall', '2', 'source/entities/Creature.cpp'),
    (41, 'config/equipments.cfg', '-', 'EquipUpgradeMargin', '0.5', 'source/entities/CreatureEquipmentAI.cpp'),
    (42, 'config/equipments.cfg', '-', 'HeroDropLargeLevel', '20', 'source/game/ItemDrops.cpp'),
    (42, 'config/equipments.cfg', '-', 'HeroDropMediumLevel', '10', 'source/game/ItemDrops.cpp'),
    (43, 'config/equipments.cfg', '-', 'ItemAuraRadius', '2', 'source/gamemap/GameMap.cpp'),
    (44, 'config/equipments.cfg', '-', 'LifespringHpShare', '0.5', 'source/entities/CreaturePotions.cpp'),
    (45, 'config/equipments.cfg', '-', 'LifespringLowHpShare', '0.25', 'source/entities/CreaturePotions.cpp'),
    (46, 'config/equipments.cfg', '-', 'LifespringManaShare', '0.25', 'source/entities/CreaturePotions.cpp'),
    (47, 'config/equipments.cfg', '-', 'MaxItemEffects', '2', 'source/entities/ItemInstance.cpp'),
    (48, 'config/equipments.cfg', '-', 'MendingSeconds', '10', 'source/entities/Creature.cpp'),
    (49, 'config/equipments.cfg', '-', 'PotionManaDrinkShare', '0.3', 'source/entities/CreaturePotions.cpp'),
    (50, 'config/equipments.cfg', '-', 'PotionRegenSeconds', '10', 'source/creatureeffect/CreatureEffectPotion.cpp'),
    (51, 'config/equipments.cfg', '-', 'PotionSlotLevel2', '10', 'source/entities/Creature.cpp'),
    (51, 'config/equipments.cfg', '-', 'PotionSlotLevel3', '20', 'source/entities/Creature.cpp'),
    (52, 'config/equipments.cfg', '-', 'SecondWindHealthShare', '0.5', 'source/entities/Creature.cpp'),
    (53, 'config/rooms.cfg', 'AlchemyLab', 'AlchemyLabBangMaxSeconds', '120', 'source/rooms/RoomAlchemyLab.cpp'),
    (53, 'config/rooms.cfg', 'AlchemyLab', 'AlchemyLabBangMinSeconds', '60', 'source/rooms/RoomAlchemyLab.cpp'),
    (53, 'config/rooms.cfg', 'AlchemyLab', 'AlchemyLabLargeLevel', '20', 'source/rooms/RoomAlchemyLab.cpp'),
    (53, 'config/rooms.cfg', 'AlchemyLab', 'AlchemyLabMediumLevel', '10', 'source/rooms/RoomAlchemyLab.cpp'),
    (54, 'config/rooms.cfg', 'Merchant', 'MerchantEquipMargin', '0.5', 'source/rooms/RoomMerchant.cpp'),
    (54, 'config/rooms.cfg', 'Merchant', 'MerchantReservationTurns', '60', 'source/rooms/RoomMerchant.cpp'),
    (56, 'config/rooms.cfg', 'Merchant', 'MerchantTradeChance', '0.3', 'source/game/CreatureMerchantAI.cpp'),
    (57, 'config/rooms.cfg', 'Tavern', 'TavernDrinkChainHalving', '2', 'source/rooms/RoomTavern.cpp'),
    (57, 'config/rooms.cfg', 'Tavern', 'TavernDuelMaxTurnsFactor', '4', 'source/rooms/RoomTavern.cpp'),
    (57, 'config/rooms.cfg', 'Tavern', 'TavernGamesWithBeer', '3', 'source/rooms/RoomTavern.cpp'),
    (57, 'config/rooms.cfg', 'Tavern', 'TavernGamesWithoutBeer', '2', 'source/rooms/RoomTavern.cpp'),
]


# These readers use each runtime type's name to select its existing <Name>HP setting.
ROOM_HP_READER = 'getRoomNameFromRoomType(getType()) + "HP"'
TRAP_HP_READER = 'getTrapNameFromTrapType(getType()) + "HP"'

# Exact old decision expressions or removed constant definitions, grouped by item.
OLD_EXPRESSIONS = {
    1: r'allies\.size\(\)\s*<\s*2\b',
    2: r'const int SKELETON_ARMY_RADIUS\s*=',
    3: r'Random::Int\(0,\s*100\)\s*>\s*80\b',
    4: r'static const double anchors\[\]',
    5: r'const int NB_TURN_FLEE_MAX\s*=',
    6: r'static const double (?:HIT_SCALE|MIN_HIT_PERCENT|MAX_HIT_PERCENT)\s*=',
    7: r'Random::Int\(0,\s*100\)\s*<\s*80\b',
    8: r'const uint32_t (?:DEVIATION_POINTS|RESET_MIN_FOLLOWERS|UNFOLLOWED_WEIGHT)\s*=',
    9: r'const uint32_t TIER_(?:TWO_UNLOCK_RANKS|THREE_UNLOCK_RANKS|FOUR_MIN_SPENT)\s*=',
    10: r'static_cast<float>\(val\)\s*\*\s*0\.8f',
    11: r'mSlapTurns\.size\(\)\s*>\s*10\b',
    12: r'const double COMBAT_CLASS_SUPPORT_TARGET_FACTOR\s*=',
    13: r'std::max\(0\.5,\s*std::min\(2\.0,\s*threatFactor\)\)',
    14: r'static const double THREAT_PERCENT_BY_LEVEL\[',
    15: r'Random::Uint\(0,\s*100\)\s*<\s*20\b',
    16: r'const double (?:CARRY_FIRST_MAX_SHARE|CLAIM_WALL_FIRST_MIN_SHARE)\s*=',
    17: r'const uint32_t SandboxMode::MAX_HERO_LEVEL\s*=',
    18: r'const uint32_t SandboxMode::MIN_HERO_LEVEL\s*=',
    19: r'const uint32_t SandboxMode::NB_HEROES_PER_WAVE\s*=',
    20: r'const uint32_t SandboxMode::NB_WAVES\s*=',
    21: r'const int32_t BRAWL_START_HEALTH_MARGIN_PERCENT\s*=',
    22: r'costPerTile\(room->getType\(\)\)\s*/\s*2\b',
    23: r'Random::Uint\(0,\s*100\)\s*<=\s*50\b',
    24: r'const int treasuryTileCapacity\s*=',
    25: r'GiftBoxType::\w+,\s*\d+\s*}',
    26: r'const int32_t NB_TURNS_OUTSIDE_HATCHERY_BEFORE_DIE\s*=',
    27: r'std::min<uint32_t>\(percent,\s*90\)',
    28: r'const uint32_t STAGE_(?:MIN|MAX)_PERCENT\s*=',
    30: r'mNeededSkillPoints\s*\*\s*\(level == 2\s*\?\s*2\s*:\s*4\)',
    31: r'\(nbAllowed\s*\+\s*1\)\s*/\s*2',
    32: r'getNextWorkerPriceForPlayer\(mGameMap, this\)\s*/\s*2',
    33: r'costPerTile\(trap->getType\(\)\)\s*/\s*2\b',
    34: r'10\s*-\s*mNbHits',
    36: r'const double WATER_DAMAGE_FACTOR\s*=',
    37: r'const double BLEED_TURNS\s*=',
    38: r'const double (?:BULWARK_RADIUS|LAST_STAND_HEALTH_SHARE)\s*=',
    39: r'const double (?:CHILL_FACTOR|WEAKEN_FACTOR)\s*=',
    40: r'(?:points\s*\+=|return)\s*[246]\.0\s*;',
    41: r'const double EQUIP_UPGRADE_MARGIN\s*=',
    42: r'const uint32_t (?:MEDIUM|LARGE)_HERO_LEVEL\s*=',
    43: r'const double AURA_RADIUS_SQUARED\s*=\s*4\.0',
    44: r'const double LIFESPRING_HP\s*=',
    45: r'const double LIFESPRING_LOW_HP\s*=',
    46: r'const double LIFESPRING_MANA\s*=',
    47: r'const uint32_t MAX_ITEM_EFFECTS\s*=',
    48: r'const double MENDING_SECONDS\s*=',
    49: r'const double MANA_DRINK_SHARE\s*=',
    50: r'const double REGEN_SECONDS\s*=',
    51: r'const uint32_t (?:SECOND|THIRD)_SLOT_LEVEL\s*=',
    52: r'const double SECOND_WIND_HEALTH_SHARE\s*=',
    53: r'const (?:double BANG_(?:MIN|MAX)_SECONDS|uint32_t (?:LARGE|MEDIUM)_LEVEL)\s*=',
    54: r'const (?:double EQUIP_MARGIN|int64_t RESERVATION_TURNS)\s*=',
    56: r'const double TRADE_CHANCE\s*=',
    57: r'const (?:double DRINK_CHAIN_HALVING|int32_t DUEL_MAX_TURNS_FACTOR|uint32_t NB_GAMES_WITH(?:OUT)?_BEER)\s*=',
}


# Reads a tracked source or config as text.
def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


# Compares scalar or curve values without discarding fractions.
def numbers_equal(actual, expected):
    try:
        left = [float(value) for value in actual.split()]
        right = [float(value) for value in expected.split()]
        return len(left) == len(right) and all(
            math.isclose(a, b, rel_tol=0.0, abs_tol=1e-9) for a, b in zip(left, right))
    except ValueError:
        return False


# Checks every table entry, its configuration reader and the original removed expression.
def main():
    problems = []
    manager = read("source/utils/ConfigManager.cpp")
    manager_header = read("source/utils/ConfigManager.h")
    tree = read("source/creatureskill/CreatureSkillTree.cpp")
    for item, config_file, entity, key, expected, source_file in SETTINGS:
        config = read(config_file)
        source = read(source_file)
        if item in (1, 2):
            kind = "AURA_ALLY_StrengthChange" if item == 1 else "SKELARMY"
            blocks = re.findall(r'\[(?:Skill|TierFour)\](.*?)\[/(?:Skill|TierFour)\]', config, re.S)
            values = [re.search(r'^\s*' + re.escape(key) + r'\s+([^\n]+)', block, re.M)
                      for block in blocks if re.search(r'^Kind\s+' + kind + r'\s*$', block, re.M)]
            if not values or any(match is None or not numbers_equal(match.group(1), expected) for match in values):
                problems.append(f"M{item}: {entity} {key} is absent or differs from {expected}")
            if f'key == "{key}"' not in tree or f'm{key}' not in source:
                problems.append(f"M{item}: {key} does not reach the runtime skill")
        else:
            match = re.search(r'^\s*' + re.escape(key) + r'\s+([^\n]+)', config, re.M)
            if match is None or not numbers_equal(match.group(1), expected):
                problems.append(f"M{item}: {key} is absent or differs from {expected}")
            if item == 29:
                reader = read("source/rooms/Room.cpp" if config_file.endswith("rooms.cfg") else "source/traps/Trap.cpp")
                if (ROOM_HP_READER if config_file.endswith("rooms.cfg") else TRAP_HP_READER) not in reader:
                    problems.append(f"M29: no type-specific HP reader for {key}")
            elif config_file == "config/global.cfg":
                readers = source + (read("source/gamemap/SandboxMode.h") if item in (17, 18, 19, 20) else "")
                if f'get{key}()' not in readers or f'm{key}' not in manager_header or f'nextParam == "{key}"' not in manager:
                    problems.append(f"M{item}: {key} getter/parser is missing")
                default = re.search(r'\bm' + key + r'\(([^\n]+)\),', manager)
                if default is None or not numbers_equal(default.group(1).strip('{}').replace(',', ' '), expected):
                    problems.append(f"M{item}: {key} constructor fallback differs from shipped value")
            elif item == 21:
                if f'"{key}", &settings.m{key}' not in source or f'settings.m{key}' not in source:
                    problems.append(f"M21: relationship margin is not loaded/used")
            else:
                reader = re.search(r'get(?:Room|Trap|Spell|Equipment|Research)ConfigDoubleOrDefault\("' + re.escape(key) + r'",\s*([\d.eE+-]+)\)', source)
                if reader is None or not numbers_equal(reader.group(1), expected):
                    problems.append(f"M{item}: {key} reader or shipped fallback is missing")
                if config_file.endswith(("equipments.cfg", "skills.cfg")) and f'nextParam == "{key}"' not in manager:
                    problems.append(f"M{item}: {key} is not parsed from its numeric settings block")
        expression = OLD_EXPRESSIONS.get(item)
        # Critical point constants are scoped to the potion method, not unrelated return values.
        if item == 40:
            source = source.split('double Creature::getPotionCritChance() const', 1)[1].split('\n}', 1)[0]
        if expression and re.search(expression, source):
            problems.append(f"M{item}: original hard-coded expression remains in {source_file}")
    if 'Building::DEFAULT_TILE_HP = 10.0' in read("source/entities/Building.cpp"):
        problems.append("M29: fixed building health still defines the gameplay value")
    if 'getTileHP() / burnTurns' not in read("source/rooms/RoomBridgeWooden.cpp"):
        problems.append("M29: wooden bridge burning ignores configured tile health")
    # M35 replaces only the wall-break draw; the independent direction draw stays unchanged.
    boulder = read("source/entities/MissileBoulder.cpp").split('bool MissileBoulder::wallHitNextDirection', 1)[1]
    first_draw = boulder.split('if(Random::', 1)[1].split('\n', 1)[0]
    if 'BoulderWallBreakPercent' not in first_draw:
        problems.append("M35: wall-break decision still uses a hard-coded chance")
    # M55 was already configurable; its separate legacy default remains intentional.
    if 'MerchantMarginDefault' not in read("source/game/Seat.cpp"):
        problems.append("M55: existing merchant margin reader is missing")
    if problems:
        print('\n'.join(problems))
        return 1
    print(f"Balance config keys: {len(SETTINGS)} settings, M1-M57 checked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
