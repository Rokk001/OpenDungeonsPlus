"""Static check: a carry whose cargo was removed, died or was picked up on the way ends without a crash.

CreatureActionCarryEntity::releaseEntity sets the cargo to nullptr, and the destructor of the carry then still
tells the destination building with notifyCarryingStateChanged(carrier, nullptr). Every building override must
therefore test the cargo for nullptr before it reads it (the heart did not, which crashed the game when merged
dig gold vanished while a worker carried it to the heart ring). It does not start a game and compiles nothing."""
from pathlib import Path
import re
import sys

repo = Path(__file__).resolve().parents[2]


def function(text, start):
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def strip_comments(text):
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    return re.sub(r'//[^\n]*', '', text)


failures = []


def check(condition, message):
    if not condition:
        failures.append(message)


# The premise: the released cargo is nullptr and the destructor still hands it to the building
carry = strip_comments((repo / 'source/creatureaction/CreatureActionCarryEntity.cpp').read_text(encoding='utf-8'))
release = function(carry, carry.index('void CreatureActionCarryEntity::releaseEntity('))
check('mEntityToCarry = nullptr;' in release, 'releaseEntity lets the cargo go (mEntityToCarry = nullptr)')
destructor = function(carry, carry.index('CreatureActionCarryEntity::~CreatureActionCarryEntity('))
check('notifyCarryingStateChanged(' in destructor and 'mEntityToCarry)' in destructor,
      'the carry destructor tells the destination building about the (possibly released) cargo')

signature = re.compile(r'void\s+(\w+)::notifyCarryingStateChanged\(\s*Creature\s*\*\s*(\w+)\s*,\s*GameEntity\s*\*\s*(\w+)\s*\)')
found = []
for path in sorted((repo / 'source').rglob('*.cpp')):
    text = strip_comments(path.read_text(encoding='utf-8', errors='replace'))
    for match in signature.finditer(text):
        owner, entity = match.group(1), match.group(3)
        body = function(text, match.start())
        body = body[body.index('{'):]
        name = re.escape(entity)
        use = re.search(r'\b%s\s*->|static_cast<[^>]*>\(\s*%s\s*\)|\*\s*%s\b' % (name, name, name), body)
        if use is None:
            found.append(owner)
            continue
        guard = re.search(r'\b%s\s*[!=]=\s*nullptr|nullptr\s*[!=]=\s*%s\b|!\s*%s\b' % (name, name, name), body)
        check(guard is not None and guard.start() < use.start(),
              '%s::notifyCarryingStateChanged tests %s for nullptr before it reads it (%s)'
              % (owner, entity, path.relative_to(repo).as_posix()))
        found.append(owner)

check('RoomDungeonTemple' in found, 'the heart override of notifyCarryingStateChanged is checked: %s' % found)
check(len(found) >= 10, 'all building overrides of notifyCarryingStateChanged are found: %s' % found)

if failures:
    for failure in failures:
        print('FAIL: ' + failure)
    sys.exit(1)
print('check_carry_released_entity_null: OK (%d overrides)' % len(found))
