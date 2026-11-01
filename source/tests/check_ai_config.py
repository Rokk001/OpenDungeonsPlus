"""Check the AI configuration values and documented defaults."""
from pathlib import Path
import re

repo = Path(__file__).resolve().parents[2]
SINGLE = {'AiPollSeconds': '1', 'LookPeriod600': '600', 'ClickBudgetPerMinute': '202.5', 'ClickMinGap': '0.296', 'ClickWindowSeconds': '60', 'ActionLatencyMean': '0.72', 'ActionLatencySd': '0.217', 'PeriodicMinDelay': '5', 'SymptomScanFactor': '0.5', 'ReferenceScanPeriod': '60', 'LookPeriod60': '60', 'LookPeriod120': '120', 'LookFactorBuild': '0.35', 'LookFactorDormitory': '0.25', 'LookFactorTrap': '0.5', 'LookFactorSummon': '0.7', 'LookFactorPlan': '2', 'LookFactorScan': '1', 'FirstPlanSeconds': '600', 'FirstPlanJitterSeconds': '120', 'FightOverSeconds': '10', 'MistakeBaseRoutine': '0.02', 'MistakeBaseRule': '0.09', 'MistakeBaseComplex': '0.16', 'MistakeBaseUnfamiliar': '0.26', 'MistakeBaseRare': '0.55', 'MistakeMin': '0.004', 'MistakeMax': '0.85', 'MistakeTilesDormitory': '9', 'MistakeTilesHatchery': '9', 'MistakeTrapWantDivisor': '2', 'ReserveSlipStartMin': '0.2', 'ReserveSlipStartMax': '0.9', 'RestHpShareSlip': '0.3', 'DigWorkersSlip': '1', 'EarlyDigMultiplier': '0.3', 'SlapMistakePauseSeconds': '120', 'SlapMistakeBaseSeconds': '60', 'SlapMistakeDelayFactor': '2', 'SlapMistakeInterval1': '60', 'SlapMistakeInterval2': '90', 'SlapMistakeInterval3': '120', 'SlapMistakeInterval4': '180', 'SlapMistakeInterval5': '300', 'MinerShareEarly': '0.6', 'MinerShareLate': '0.35', 'MinerShareSwitchMinute': '10', 'MarkedTilesPerWorker': '1', 'SummonManaFactor': '2', 'SummonIncomeMin': '40', 'SummonWorkersMax': '10', 'WalletReserveWindow': '60', 'CreateGoldManaReserve': '0.25', 'GoldShareBuild': '0.85', 'ManaShareSpend': '0.9', 'GoldShareTreasury2': '0.7', 'RoomGoldMargin': '300', 'BedsSpare': '1', 'DormitoryExtensionTiles': '25', 'HatcheryExtensionMinTiles': '9', 'HatcheryExtensionMaxTiles': '25', 'HatcheryTilesPerCreature': '1', 'TavernKeeperPaysFactor': '2', 'MerchantMarginMin': '10', 'MerchantMarginMax': '20', 'LabModeDefault': '1', 'InfirmaryDischargePercent': '100', 'GhostResearchShare': '0.7', 'GhostManaShare': '0.2', 'ReviveManaFactor': '2', 'BridgeMinShortcutTiles': '10', 'PlacementPointsPerWallSpot': '50', 'PlacementHandicapPerTileOffset': '20', 'PlacementFirstSpotTiles': '3', 'PlacementNextSpotTiles': '2', 'ResearchQueueEntries': '2', 'PossessLeaveHpShare': '0.3', 'HealBelow': '0.5', 'HealNeverAbove': '0.7', 'HealCastChance': '0.4', 'HasteFightSeconds': '20', 'EyeCastIntervalMinutes': '5', 'TremorMinTargets': '4', 'InfernoReserveCasts': '2', 'LightningManaReserve': '0.05', 'SpellManaReserve': '0.05', 'CastRecheckSeconds': '5', 'MinRecastSeconds': '3', 'CallToWarMinCreatures': '3', 'TrapTilesPerEntrance': '3', 'GasEveryNthTile': '3', 'TrapGoldMargin': '300', 'CannonManaPerTile': '2500', 'SpikeBehindDoorMinTiles': '3', 'SpikeBehindDoorMaxTiles': '6', 'CannonMaxDoorDistance': '15', 'BoulderCorridorMinTiles': '8', 'AlarmDistanceTiles': '6', 'MaxWaitingForCraft': '2', 'TrapPlanMinRooms': '9', 'PrisonWaitMinutes': '5', 'ExploreTunnelsPerDirection': '1', 'Leveltilesdig': '2', 'HeartDefenceAreaTiles': '5', 'AttackMinMinute': '20', 'AttackMinFighters': '5', 'AttackMinTrapTiles': '2', 'AttackDiggers': '3', 'EarlyDigMinute': '12', 'EarlyDigMinFighters': '3', 'DiggerCapShare': '0.5', 'DigActions': '4', 'DetourSigma': '0.5', 'TunnelProbeSeconds': '5', 'EnemyOutMinCreatures': '3', 'SecondWaveMinutes': '1', 'HeartPossessBelow': '0.6', 'RestHpShare': '0.8', 'AttackMinReady': '3', 'RestSecondsAfterAssault': '45', 'RaidGoldThreshold': '8000', 'RetreatCheckSeconds': '5', 'ContactTimeoutSeconds': '1800', 'ScoutCameraActions': '2', 'ReloadRetrySeconds': '30', 'PoorDefenceShuffleChance': '0.5', 'ChampionExtraSeconds': '30', 'GroupShareMain': '0.55', 'GroupShareRaid': '0.3', 'GroupShareSingle': '0.7', 'GroupShareRaidTactic': '0.4', 'CounterArmyShare': '0.85', 'RaidTargetsSplit': '2', 'RaidTargetsRaid': '3', 'RawHitFactor': '0.9', 'StrengthRatioCap': '3', 'ScorePenaltyBase': '0.6', 'ScorePenaltyAllin': '1.0', 'ScorePenaltySingle': '0.49', 'ScorePenaltySplit': '0.72', 'ScorePenaltyRaid': '0.16', 'ScorePenaltyCounter': '0.72', 'ScorePenaltyCounterFactor': '0.3', 'BonusSplit': '0.2', 'BonusRaidBase': '1.0', 'BonusRaidGold': '0.4', 'BonusRaidGoldDivisor': '3000', 'BonusCounter': '0.7', 'WaitWeight': '1.0', 'TacticExponentClamp': '30', 'AdvFloor': '-4', 'AdvHpFloorShare': '0.1', 'EnemyHpFloorShare': '0.05', 'FightEstimateDamageShare': '0.88', 'EstimateSetupSeconds': '5', 'EstimateRoomTiles': '16', 'EstimateTileHp': '10', 'HeartHealMargin': '1.0', 'HeartBreakFallbackSeconds': '600', 'DoorTimeCap': '60', 'PotentialCastsMax': '40', 'PotentialCastPeriod': '4.5', 'PotentialCastsBase': '1', 'SpellPotentialEff': '0.7', 'TrapEff': '0.45', 'TrapPassSeconds': '4', 'TrapTargetsSpike': '1', 'TrapTargetsCannon': '1', 'TrapTargetsBoulder': '2', 'TrapTargetsGas': '2', 'TrapTargetsLightning': '1', 'TrapTargetsFireburst': '2', 'SpellTargetsLightning': '1', 'SpellTargetsExplosion': '1', 'SpellTargetsTremor': '4', 'SpellTargetsInferno': '2', 'EstimateNoSightingNoise': '0.6', 'EstimateGoldDefault': '5000', 'EstimateReadyFlipRate': '0.08'}
PROBABILITY_KEYS = ['Pi', 'FocusFire', 'MistakeBaseRoutine', 'MistakeBaseRule', 'MistakeBaseComplex', 'MistakeBaseUnfamiliar', 'MistakeBaseRare', 'MistakeMin', 'MistakeMax', 'HealCastChance', 'PoorDefenceShuffleChance', 'RawHitFactor']
ROOMS = [('treasury', 'treasury', '9'), ('dormitory', 'dormitory', '25'), ('hatchery', 'hatchery', '25'), ('tavern', 'tavern', '16'), ('library', 'library', '25'), ('training', 'trainingHall', '25'), ('workshop', 'workshop', '25'), ('casino', 'casino', '16'), ('toilet', 'toilet', '9'), ('treasury2', 'treasury', '25'), ('merchant', 'merchant', '16'), ('guard', 'guardRoom', '9'), ('herbgarden', 'herbGarden', '9'), ('arena', 'arena', '25'), ('prison', 'prison', '16'), ('alchemy', 'alchemyLab', '9'), ('infirmary', 'infirmary', '16'), ('ghostroom', 'ghostRoom', '16'), ('spa', 'spa', '16'), ('crypt', 'crypt', '16'), ('temple', 'temple', '25'), ('torture', 'torture', '16')]
ACTIONS = [('slap', '1', '1.30'), ('pickup', '1', '1.30'), ('drop', '1', '1.30'), ('dig', '1', '2.40'), ('build', '3', '5.00'), ('spell', '3', '3.90'), ('trap', '3', '3.90'), ('setting', '3', '3.90'), ('research', '5', '6.50'), ('research_auto', '2', '2.60'), ('camera', '1', '0.60'), ('minimap', '1', '1.30'), ('sell', '2', '2.60'), ('possess', '3', '3.90'), ('think', '0', '1.35')]
CLASSES = [('A01', 'rule', '1'), ('A02', 'rule', '1'), ('A03', 'routine', '1'), ('A04', 'rule', '1'), ('A05', 'rule', '1'), ('A06', 'routine', '1'), ('A07', 'routine', '1'), ('A08', 'complex', '1'), ('A09', 'rule', '1'), ('B01', 'rule', '1'), ('B02', 'rule', '1'), ('B03', 'rule', '1'), ('B04', 'rule', '1'), ('B05', 'rule', '1'), ('B06', 'rule', '1'), ('B07', 'rule', '1'), ('B08', 'unfamiliar', '1'), ('B09', 'unfamiliar', '1'), ('B10', 'rule', '1'), ('B11', 'unfamiliar', '1'), ('B12', 'rule', '1'), ('B13', 'rule', '1'), ('B14', 'rule', '1'), ('B15', 'unfamiliar', '1'), ('B16', 'rule', '1'), ('B17', 'unfamiliar', '1'), ('B18', 'unfamiliar', '1'), ('B19', 'rule', '1'), ('B20', 'rare', '1'), ('B21', 'rule', '1'), ('B22', 'rule', '1'), ('B23', 'complex', '1'), ('B24', 'unfamiliar', '0.8'), ('C01', 'rule', '1'), ('C02', 'routine', '1.5'), ('C03', 'complex', '1'), ('C04', 'complex', '1'), ('C05', 'rule', '1'), ('C06', 'complex', '1'), ('D01', 'rule', '1'), ('D02', 'rule', '1'), ('D03', 'rule', '1'), ('D04', 'rule', '0.8'), ('D05', 'complex', '1'), ('D06', 'rule', '1'), ('D07', 'rule', '1'), ('D08', 'rule', '1'), ('D09', 'rule', '1'), ('D10', 'rule', '1'), ('D11', 'rule', '1'), ('E01', 'routine', '1'), ('E02', 'complex', '1'), ('E03', 'complex', '1'), ('E04', 'rule', '1'), ('E05', 'complex', '1'), ('E06', 'complex', '1'), ('E07', 'complex', '1'), ('E08', 'complex', '1'), ('E09', 'complex', '1'), ('E10', 'complex', '1'), ('E11', 'complex', '1'), ('E12', 'complex', '1'), ('E13', 'rule', '1'), ('E14', 'rare', '1'), ('E15', 'complex', '1'), ('E16', 'complex', '1'), ('E17', 'rare', '1'), ('E18', 'rare', '1'), ('E19', 'complex', '1'), ('F01', 'rule', '1'), ('F02', 'rule', '1'), ('F03', 'rule', '1'), ('F04', 'rule', '1'), ('F05', 'complex', '1'), ('F06', 'complex', '1'), ('F07', 'complex', '1'), ('F08', 'complex', '1'), ('F09', 'rule', '1'), ('F10', 'complex', '1'), ('F11', 'complex', '1'), ('F12', 'rule', '1'), ('F13', 'rule', '1'), ('F14', 'complex', '1'), ('F15', 'rule', '1'), ('G01', 'rule', '1'), ('G02', 'unfamiliar', '1'), ('G03', 'rule', '1'), ('G04', 'rule', '1'), ('H01', 'rule', '1'), ('H02', 'rule', '1'), ('H03', 'rule', '1'), ('I01', 'rule', '1'), ('I02', 'complex', '1'), ('I03', 'rule', '1'), ('I04', 'complex', '1'), ('I05', 'rule', '1'), ('I06', 'routine', '1'), ('J01', 'routine', '1'), ('J02', 'rule', '1'), ('J03', 'complex', '1'), ('J04', 'complex', '1'), ('J05', 'complex', '1'), ('J06', 'complex', '1'), ('J07', 'complex', '1'), ('J08', 'rule', '1'), ('K01', 'complex', '1'), ('K02', 'complex', '1'), ('K03', 'complex', '1'), ('K04', 'complex', '1'), ('K05', 'rule', '1'), ('K06', 'complex', '1'), ('K07', 'complex', '1'), ('K08', 'complex', '1'), ('K09', 'rule', '1'), ('K10', 'rule', '1'), ('L01', 'routine', '0'), ('L02', 'routine', '0'), ('L03', 'routine', '0'), ('L04', 'routine', '0'), ('E20', 'rule', '1'), ('H04', 'rule', '1')]

# Read the ordered, comment-free rows of a configuration section.
def section(text, name):
    text = text.split("[" + name + "]", 1)[1].split("[/" + name + "]", 1)[0]
    return [line.split("#", 1)[0].split() for line in text.splitlines() if line.split("#", 1)[0].strip()]

REMOVED_LEVEL_SUFFIXES = (
    "CooldownDefenseMin", "CooldownDefenseMax", "CooldownSaveWoundedMin", "CooldownSaveWoundedMax",
    "CooldownLookingForRoomsMin", "CooldownLookingForRoomsMax", "ReactionPercent",
    "MinHpPercentToFight", "MinFightersToAttack", "MinCreatureLevel", "MaxTrapTiles", "MaxDoors",
)
REMOVED_SHARED = (
    "AttackCooldownMin", "AttackCooldownMax", "AttackRetreatCooldownMin", "AttackRetreatCooldownMax",
    "AttackDigCooldownMin", "AttackDigCooldownMax", "AttackRetreatDivisor", "SpellsCooldownMin",
    "SpellsCooldownMax", "HealMaxHpRatio", "DefenseBannerMinFighters", "TrapsCooldownMin",
    "TrapsCooldownMax", "TrapsGoldReserve", "Scaledcooldown1030Min", "Scaledcooldown1030Max",
    "Totalstorage3000", "RoomSize", "Scaledcooldown70120Min", "Scaledcooldown70120Max",
    "Emptystorage100", "CreateGoldStorageGap", "CreateGoldGoldMax", "Scaledcooldown310Min",
    "Scaledcooldown310Max", "Nbworkers4Or13N1", "Scaledcooldown2060Min", "Scaledcooldown2060Max",
)
removed = [level + suffix for level in ("Easy", "Normal", "Hard") for suffix in REMOVED_LEVEL_SUFFIXES]
removed += list(REMOVED_SHARED)
assert len(removed) == 64
for path in sorted(list((repo / "source/ai").glob("*.h")) + list((repo / "source/ai").glob("*.cpp"))):
    text = path.read_text(encoding="utf-8")
    assert "LEGACY-AI" not in text, f"{path.name}: LEGACY-AI"
    # Normalize identifiers so the former uppercase C++ constants are checked too.
    identifiers = {word.replace("_", "").lower() for word in re.findall(r"\b[A-Za-z_]\w*\b", text)}
    for key in removed:
        assert key.lower() not in identifiers, f"{path.name}: removed key {key}"

# Inspect code tokens, excluding numbers inside comments and string literals.
for path in sorted((repo / "source/ai").glob("Ai*.cpp")):
    text = path.read_text(encoding="utf-8")
    code = re.sub(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"', ' ', text, flags=re.S)
    for token in re.finditer(r"(?<![\w.])-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?[fFlL]?(?![\w.])", code):
        value = float(token.group().rstrip("fFlL"))
        if value in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 60):
            continue
        if value == 0.5 and re.match(r"\s*\*\s*\(", code[token.end():]):
            continue  # Arithmetic mean of a minimum and maximum.
        assert value not in {float(number) for number in SINGLE.values()}, f"{path.name}: balance literal {token.group()}"

config = (repo / "config/ai.cfg").read_text(encoding="utf-8")
single = section(config, "KeeperAI")
assert len(single) == len(SINGLE), "single-value key count"
assert {r[0] for r in single} == set(SINGLE), "single-value keys"
for row in single:
    assert len(row) == 2 and float(row[1]) == float(SINGLE[row[0]]), row[0]
    assert re.search(r"^#\s*" + re.escape(row[0]) + r"\s*\([^\n]*default", config, re.M), row[0]
for row in section(config, "KeeperAILevels"):
    assert len(row) == 6 and re.search(r"^#\s*" + re.escape(row[0]) + r"\s*\([^\n]*defaults", config, re.M), row[0]
assert section(config, "RoomPlan") == [[name, tiles] for name, _, tiles in ROOMS]
assert [(r[0], int(r[1]), float(r[2])) for r in section(config, "Actions")] == [(n, int(c), float(t)) for n, c, t in ACTIONS]
assert [(r[0], r[1], float(r[2])) for r in section(config, "RowClasses")] == [(n, c, float(m)) for n, c, m in CLASSES]
levels = {r[0]: r[1:] for r in section(config, "KeeperAILevels")}
assert levels["EnemyManaEstimate"] == ["own", "own", "own", "own", "observed"]
for index in range(5):
    assert abs(sum(float(levels["TacticPrior" + name][index]) for name in ("Allin", "Single", "Split", "Raid", "Counter")) - 1) < 1e-9
for name in ("Rho", "Pi", "ClickShare", "AttackAdvantage", "FocusFire", "RetreatThreshold"):
    values = list(map(float, levels[name]))
    assert values == sorted(values), name
for name in ("ScanPeriod", "MistakeMultiplier", "EstimateNoise", "TacticTemperature", "TunnelDetour"):
    values = list(map(float, levels[name]))
    assert values == sorted(values, reverse=True), name
assert [float(a) * float(b) for a, b in zip(levels["Rho"], levels["Pi"])] == sorted(float(a) * float(b) for a, b in zip(levels["Rho"], levels["Pi"]))
for name in PROBABILITY_KEYS:
    matches = [row[1:] for group in (section(config, "KeeperAILevels"), single) for row in group if row[0] == name]
    assert len(matches) == 1 and all(0 < float(v) < 1 for v in matches[0]), name
keeper = (repo / "source/ai/KeeperAI.cpp").read_text(encoding="utf-8")
room_match = re.search(r"wantedBuildings\s*=\s*\{(.*?)\}", keeper, re.S)
assert room_match and re.findall(r"RoomType::(\w+)", room_match.group(1)) == [room for _, room, _ in ROOMS]
keys_match = re.search(r"wantedBuildingKeys\s*=\s*\{(.*?)\}", keeper, re.S)
tiles_match = re.search(r"wantedBuildingTiles\s*=\s*\{(.*?)\}", keeper, re.S)
assert keys_match and re.findall(r'"([^"]+)"', keys_match.group(1)) == [name for name, _, _ in ROOMS]
assert tiles_match and re.findall(r"\b\d+\b", tiles_match.group(1)) == [tiles for _, _, tiles in ROOMS]

# Compare every compiled default table with the corresponding file rows.
defaults = (repo / "source/utils/ConfigManager.cpp").read_text(encoding="utf-8")
# Read the string rows from one compiled default table.
def default_rows(name):
    match = re.search(r"\b" + name + r"\s*\[\]\[\d+\]\s*=\s*\{(.*?)\n\};", defaults, re.S)
    assert match, name
    return [re.findall(r'"([^"\\]*)"', row) for row in re.findall(r"\{([^{}]*)\}", match.group(1))]

for table, name in (("AI_LEVEL_DEFAULTS", "KeeperAILevels"),
                    ("AI_CONFIG_DEFAULTS", "KeeperAI"),
                    ("AI_ACTION_DEFAULTS", "Actions"),
                    ("AI_ROW_CLASS_DEFAULTS", "RowClasses")):
    compiled = default_rows(table)
    configured = section(config, name)
    assert len(compiled) == len(configured), table
    for actual, expected in zip(compiled, configured):
        assert len(actual) == len(expected), table
        for a, b in zip(actual, expected):
            try:
                assert float(a) == float(b), (table, actual, expected)
            except ValueError:
                assert a == b, (table, actual, expected)

# Remove C++ comments while preserving strings used as configuration keys.
def without_comments(text):
    return re.sub(r'''"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|//[^\n]*|/\*.*?\*/''',
                  lambda match: ' ' if match.group().startswith(('/',)) else match.group(), text, flags=re.S)

# Check that level fields and single keys are referenced by AI decision code.
decision_code = "\n".join(without_comments(p.read_text(encoding="utf-8")) for p in sorted((repo / "source/ai").glob("*.cpp")))
decision_code += without_comments((repo / "source/entities/Creature.cpp").read_text(encoding="utf-8"))
field_map = dict(re.findall(r'if\(key == "(\w+)"\) return &settings\.(\w+(?:\[\d+\])?);', defaults))
war = without_comments((repo / "source/ai/AiWar.cpp").read_text(encoding="utf-8"))
trap_table = re.search(r'TRAP_KINDS\[\d+\]\s*=\s*\{(.*?)\};', war, re.S)
trap_prefixes = set(re.findall(r'\{TrapType::\w+,\s*"(\w+)"', trap_table.group(1))) if trap_table else set()
for name in levels:
    if name == "EnemyManaEstimate":
        field = "enemyManaEstimate"
    else:
        assert name in field_map, name
        field = field_map[name].split("[")[0]
    assert re.search(r"\." + re.escape(field) + r"\b", decision_code), name
for name in SINGLE:
    direct = re.search(r'\b(?:getAiConfigDouble|getAiConfigInt32|aiKey|key)\s*\(\s*"' + re.escape(name) + r'"', decision_code)
    conditional = re.search(r'\bkey\s*\(\s*\([^()]*\)\s*\?\s*"(?:' + re.escape(name) + r'|\w+)"\s*:\s*"(?:' + re.escape(name) + r'|\w+)"\s*\)', decision_code)
    conditional = conditional and re.search(r'"' + re.escape(name) + r'"', conditional.group())
    class_lookup = name.startswith("MistakeBase") and re.search(
        r'\bclassKey\s*\([^)]*\)\s*\{[^}]*return\s+"' + re.escape(name) + r'"', decision_code, re.S)
    trap_lookup = (name.startswith("TrapTargets") and name[len("TrapTargets"):] in trap_prefixes and
                   re.search(r'\bkey\s*\(\s*"TrapTargets"\s*\+\s*prefix\s*\)', war))
    assert direct or conditional or class_lookup or trap_lookup, f"AI key not read by a decision: {name}"
print("OK")
