"""Static check: a carry whose cargo was let go on the way ends without error logs.

When dig gold merges into a pile on the tile, the worker still carries the emptied object until the next upkeep
removes it. CreatureActionCarryEntity::releaseEntity then lets the cargo go (mEntityToCarry = nullptr) and already
empties the carry node of the worker. The carry must then end quietly (D4): action() must not hand the nullptr
cargo to handleCarryEntity (which logs CreatureActionCarryEntity.cpp "creature=..." as an error) and the destructor
must not call Creature::releaseCarriedEntity a second time (which logs Creature.cpp "name=..." as an error).
It does not start a game and compiles nothing."""
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


carry = strip_comments((repo / 'source/creatureaction/CreatureActionCarryEntity.cpp').read_text(encoding='utf-8'))

# The premise: releaseEntity lets the cargo go and empties the carry node of the worker
release = function(carry, carry.index('void CreatureActionCarryEntity::releaseEntity('))
check('mEntityToCarry = nullptr;' in release, 'releaseEntity lets the cargo go (mEntityToCarry = nullptr)')
check('mCreature.releaseCarriedEntity();' in release, 'releaseEntity empties the carry node of the worker')

# action(): a released (nullptr) cargo is not handed to handleCarryEntity
action = function(carry, carry.index('std::function<bool()> CreatureActionCarryEntity::action('))
generic = action.find('&CreatureActionCarryEntity::handleCarryEntity')
check(generic >= 0, 'action() still binds handleCarryEntity for ordinary cargo')
before = action[:generic] if generic >= 0 else action
null_branch = re.search(r'if\s*\(([^;{]*\bmEntityToCarry\s*==\s*nullptr[^;{]*)\)\s*return\s+([^;]*);', before)
check(null_branch is not None and '&&' not in null_branch.group(1),
      'action() has a branch for mEntityToCarry == nullptr before the handleCarryEntity bind')
if null_branch is not None:
    target = re.search(r'&CreatureActionCarryEntity::(\w+)', null_branch.group(2))
    check(target is not None and target.group(1) != 'handleCarryEntity',
          'the nullptr cargo branch of action() binds a handler other than handleCarryEntity')
    if target is not None and target.group(1) != 'handleCarryEntity':
        handler = function(carry, carry.index('bool CreatureActionCarryEntity::%s(' % target.group(1)))
        quiet = re.search(r'if\s*\([^{]*\bmEntityToCarry\s*==\s*nullptr[^{]*\)\s*\{([^}]*)\}', handler)
        check(quiet is not None, '%s tests mEntityToCarry for nullptr' % target.group(1))
        if quiet is not None:
            check('popAction()' in quiet.group(1), '%s ends the carry for a nullptr cargo' % target.group(1))
            check('OD_LOG_ERR' not in quiet.group(1), '%s logs no error for a nullptr cargo' % target.group(1))
            check(handler.find('handleCarryEntity(') < 0 or quiet.start() < handler.find('handleCarryEntity('),
                  '%s tests the nullptr cargo before it calls handleCarryEntity' % target.group(1))

# Destructor: no second releaseCarriedEntity once releaseEntity has let the cargo go
destructor = function(carry, carry.index('CreatureActionCarryEntity::~CreatureActionCarryEntity('))
calls = [m.start() for m in re.finditer(r'mCreature\.releaseCarriedEntity\(\)', destructor)]
check(len(calls) == 1, 'the carry destructor empties the carry node once: %d calls' % len(calls))
for pos in calls:
    head = destructor[:pos]
    guard = None
    for m in re.finditer(r'if\s*\(([^;{]*)\)\s*(\{)?', head):
        guard = m
    guarded = False
    if guard is not None:
        tail = head[guard.end():]
        inside = (tail.count('{') - tail.count('}') + (1 if guard.group(2) else 0)) > 0 if guard.group(2) \
            else ';' not in tail
        guarded = inside and re.search(r'\bmEntityToCarry\s*!=\s*nullptr', guard.group(1)) is not None
    check(guarded, 'the carry destructor calls releaseCarriedEntity only while mEntityToCarry != nullptr')

if failures:
    for failure in failures:
        print('FAIL: ' + failure)
    sys.exit(1)
print('check_carry_released_cargo_no_error: OK')
