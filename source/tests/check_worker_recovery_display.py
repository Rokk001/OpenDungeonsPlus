"""Interpret worker recovery reporting and guard the real action paths; no compilation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
source = (ROOT / 'source/entities/Creature.cpp').read_text(encoding='utf-8')


# Read one complete production function without executing native code.
def function(text, signature):
    block = text[text.index(signature):]
    return block[:block.index('\n}\n')]


# Evaluate the four production reporting statements so changed values fail the numeric checks.
def report(text, state):
    block = function(text, 'void Creature::recordWorkerStepRecovery()')
    for raw in block.split('{', 1)[1].splitlines():
        line = raw.strip().rstrip(';')
        if not line:
            continue
        if line.startswith('++'):
            state[line[2:]] += 1
        else:
            name, value = line.split(' = ')
            state[name] = eval(value.replace('true', 'True'), {'__builtins__': {}}, state)


state = {'mAttackRecoverySerial': 5}
for step in range(3):
    report(source, state)
    assert state == {'mAttackRecoverySerial': 6 + step, 'mAttackRecoveryDuration': 1,
                     'mAttackRecoveryTurns': 1, 'mNeedFireRefresh': True}
    state['mAttackRecoveryTurns'] -= 1
    assert state['mAttackRecoveryTurns'] == 0
bad = source.replace('mAttackRecoveryDuration = 1;', 'mAttackRecoveryDuration = 2;')
changed = {'mAttackRecoverySerial': 0}
report(bad, changed)
assert changed['mAttackRecoveryTurns'] != 1
upkeep = function(source, 'void Creature::doUpkeep()')
assert 'loopBack = func();' in upkeep and 'while (loopBack && loops < 20);' in upkeep
assert upkeep.count('mAttackRecoveryTurns = std::max(0.0, mAttackRecoveryTurns - 1.0);') == 1
call = 'creature.recordWorkerStepRecovery();'
dig = (ROOT / 'source/creatureaction/CreatureActionDigTile.cpp').read_text()
assert dig.count(call) == 1
assert 'if(amountDug > 0.0 && tileDig.getFullness() > 0.0)\n        ' + call in dig
assert dig.index('tileDig.digOut(creature.getDigRate())') < dig.index(call)
assert dig.index('if(isTreasuryAvailable)') < dig.index(call)
for stem, steps in [('CreatureActionClaimGroundTile', 2), ('CreatureActionClaimWallTile', 1)]:
    text = (ROOT / ('source/creatureaction/' + stem + '.cpp')).read_text()
    assert text.count(call) == steps
    for part in text.split(call)[:-1]:
        assert 'creature.receiveExp(' in part
    assert 'return false;' in text[text.rindex(call):]
fixture = (ROOT / 'source/tests/check_creature_progress.py').read_text()
assert 'each worker step restarts the existing ring' in fixture
assert 'worker recovery freezes while paused' in fixture
print('Worker dig/claim intervals: interpreted reporting and source guards PASS; runtime not tested')
