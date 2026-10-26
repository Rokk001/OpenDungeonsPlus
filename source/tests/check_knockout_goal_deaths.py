"""Check lethal-knockout death observation source contracts; never executes or compiles C++."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / 'source/entities/Creature.cpp').read_text(encoding='utf-8')


# Extract the actual lethal-knockout transition and reject early or missing death observations.
def check_transition(source):
    start = source.index('// If the counter reaches 0, the creature is dead')
    end = source.index('// Handle creature death', start)
    transition = source[start:end]
    guard = transition.index('if(mKoTurnCounter < 0)')
    still_ko = transition.index('return;', guard)
    death = transition.index('mHp = 0;')
    observation = transition.index('recordScriptEvent(*this, "killed");')
    assert transition.index('mKoTurnCounter = std::min(0.0, mKoTurnCounter + 1.0);') < guard < still_ko < death < observation
    assert transition.count('recordScriptEvent(*this, "killed");') == 1
    # The outer lethal-KO branch excludes an ordinary temporary knockout and already-dead creatures.
    upkeep = source[source.index('void Creature::doUpkeep()'):end]
    assert 'if(mKoTurnCounter < 0)\n    {' in upkeep
    assert upkeep.index('mKoTurnCounter = 0;') < upkeep.index('if(mKoTurnCounter < 0)\n    {')
    assert 'if((mKoTurnCounter != 0) && !isAlive())' in upkeep
    assert 'mKoTurnCounter = 0;' in upkeep


check_transition(SOURCE)
# Missing and premature observations must both fail this contract.
for mutation in (
    SOURCE.replace('        recordScriptEvent(*this, "killed");\n', '', 1),
    SOURCE.replace('        mHp = 0;\n        recordScriptEvent(*this, "killed");',
                   '        recordScriptEvent(*this, "killed");\n        mHp = 0;', 1),
):
    try:
        check_transition(mutation)
    except (AssertionError, ValueError):
        pass
    else:
        raise AssertionError('Missing or premature death observation was accepted')

# The shared observer updates named kill events, spawn history and exact death positions together.
observer = SOURCE[SOURCE.index('void recordScriptEvent(const Creature& creature, const std::string& eventName)\n{'):]
observer = observer[:observer.index('} // namespace')]
for call in ('recordEvent(creature.getName(), eventName)',
             'observeCreatureDeath(creature.getName(), tile->getX(), tile->getY())',
             'observeSpawnDeath(creature.getName(), templeSeat)'):
    assert call in observer
assert 'if(eventName == "killed")' in observer
# Existing direct killing and actual death animation paths remain present.
assert SOURCE.count('recordScriptEvent(*this, "killed");') == 2
assert 'clearDestinations(EntityAnimation::die_anim, false, false);' in SOURCE
print('Lethal-KO death history source contracts and two negative controls passed; C++ and gameplay not executed.')
