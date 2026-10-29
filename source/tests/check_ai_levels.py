"""Check AI level values, order, factory cases and damage calculation."""
from pathlib import Path
import re

repo = Path(__file__).resolve().parents[2]
EXPECTED = {'Rho': ['12', '15', '20', '25.433', '30'], 'Pi': ['0.4', '0.55', '0.75', '0.909', '0.99'], 'ScanPeriod': ['120', '80', '45', '24.834', '10'], 'ClickShare': ['0.3', '0.42', '0.6', '0.806', '1.0'], 'MistakeMultiplier': ['4.555556', '3.444444', '2.333333', '1.944444', '0.555556'], 'EstimateNoise': ['0.206', '0.164', '0.132', '0.106', '0.049'], 'TacticTemperature': ['2.0', '0.7', '0.45', '0.4', '0.35'], 'AttackAdvantage': ['-1.2', '-1.15', '-1.1', '-1.05', '-1.0'], 'FocusFire': ['0.62', '0.698', '0.758', '0.807', '0.914'], 'RetreatThreshold': ['0.603', '0.661', '0.706', '0.743', '0.823'], 'TunnelDetour': ['0.215', '0.176', '0.146', '0.122', '0.068'], 'TacticPriorAllin': ['0.34', '0.33', '0.32', '0.31', '0.3'], 'TacticPriorSingle': ['0.58', '0.465', '0.35', '0.23', '0.12'], 'TacticPriorSplit': ['0.04', '0.12', '0.2', '0.25', '0.3'], 'TacticPriorRaid': ['0.01', '0.015', '0.02', '0.025', '0.03'], 'TacticPriorCounter': ['0.03', '0.07', '0.11', '0.185', '0.25'], 'EnemyManaEstimate': ['own', 'own', 'own', 'own', 'observed']}

config = (repo / "config/ai.cfg").read_text(encoding="utf-8")
section = config.split("[KeeperAILevels]", 1)[1].split("[/KeeperAILevels]", 1)[0]
rows = {}
for line in section.splitlines():
    fields = line.split("#", 1)[0].split()
    if fields:
        assert fields[0] not in rows, f"duplicate {fields[0]}"
        rows[fields[0]] = fields[1:]
assert set(rows) == set(EXPECTED), "level keys differ"
for key, expected in EXPECTED.items():
    assert len(rows[key]) == 5, key
    if key == "EnemyManaEstimate":
        assert rows[key] == expected, key
    else:
        assert [float(v) for v in rows[key]] == [float(v) for v in expected], key
for key in ("Rho", "Pi", "ClickShare", "AttackAdvantage", "FocusFire", "RetreatThreshold"):
    values = [float(v) for v in rows[key]]
    assert values == sorted(values), key
for key in ("ScanPeriod", "MistakeMultiplier", "EstimateNoise", "TacticTemperature", "TunnelDetour"):
    values = [float(v) for v in rows[key]]
    assert values == sorted(values, reverse=True), key
for i in range(5):
    assert abs(sum(float(rows["TacticPrior" + suffix][i]) for suffix in ("Allin", "Single", "Split", "Raid", "Counter")) - 1) < 1e-9
noticed_cycles = [float(rho) * float(pi) for rho, pi in zip(rows["Rho"], rows["Pi"])]
assert noticed_cycles == sorted(noticed_cycles), "Rho x Pi"
factory = (repo / "source/ai/AIFactory.cpp").read_text(encoding="utf-8")
for level in ("easy", "medium", "normal", "hard", "hell"):
    assert re.search(r"case\s+KeeperAIType::" + level + r"\s*:", factory), level
assert "## Not built" in (repo / "docs/development/AI-LEVELS.md").read_text(encoding="utf-8")
print("OK")
