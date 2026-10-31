#!/usr/bin/env python3
"""Undead rules: Skeleton and Lich are never knocked out, leave no corpse, blood or ghost, cannot be carried,
taken by the crypt or raised, vanish after DeathVanishSeconds (the Skeleton leaves its bone pile, the Lich fires its
beetle effect at death), and the renderer keeps their own Die clip. Static source and config scan, no compiling."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
UNDEAD = {'Skeleton': ('5.0', '1', None), 'Lich': ('5.0', None, 'LichBeetles')}


# Read one file of the repository.
def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


# Return the body of a C++ function from its signature up to the closing brace at column 0.
def function_body(source, signature):
    start = source.index(signature)
    return source[start:source.index('\n}', start)]


# Return the value of one key in a config block, or None when the block has no such key.
def key_value(block, key):
    match = re.search(r'^\s*' + key + r'\s+(\S+)', block, re.M)
    return match.group(1) if match else None


# Run every undead rule and stop at the first one that is broken.
def main():
    creatures = read('config/creatures.cfg')
    blocks = {}
    for block in re.findall(r'\[Creature\](.*?)\[/Creature\]', creatures, re.S):
        name = key_value(block, 'Name')
        if name is not None:
            blocks[name] = block
    for name, block in blocks.items():
        if name in UNDEAD:
            seconds, pile, effect = UNDEAD[name]
            assert key_value(block, 'Undead') == '1', name + ' must carry Undead 1'
            assert key_value(block, 'DeathVanishSeconds') == seconds, name + ' DeathVanishSeconds must be ' + seconds
            assert key_value(block, 'DeathVanishPile') == pile, name + ' DeathVanishPile must be ' + str(pile)
            assert key_value(block, 'DeathVanishEffect') == effect, name + ' DeathVanishEffect must be ' + str(effect)
        else:
            for key in ('Undead', 'DeathVanishSeconds', 'DeathVanishPile', 'DeathVanishEffect'):
                assert key_value(block, key) in (None, '0'), name + ' must not carry ' + key

    definition_h = read('source/entities/CreatureDefinition.h')
    definition_cpp = read('source/entities/CreatureDefinition.cpp')
    for member, getter, key in (('mUndead', 'isUndead', 'Undead'),
                                ('mDeathVanishSeconds', 'getDeathVanishSeconds', 'DeathVanishSeconds'),
                                ('mDeathVanishPile', 'hasDeathVanishPile', 'DeathVanishPile'),
                                ('mDeathVanishEffect', 'getDeathVanishEffect', 'DeathVanishEffect')):
        assert re.search(r'\b' + getter + r'\s*\(\s*\)\s*const', definition_h), 'CreatureDefinition has no ' + getter
        assert re.search(r'\b' + member + r'\s*;', definition_h), 'CreatureDefinition has no member ' + member
        assert re.search(r'\b' + member + r'\s*\(', definition_cpp), member + ' has no default'
        assert member + '(def.' + member + ')' in definition_cpp, member + ' is not copied'
        assert 'os << c->' + member in definition_cpp and 'is >> c->' + member in definition_cpp, \
            member + ' is not in the packet'
        assert 'nextParam == "' + key + '"' in definition_cpp, key + ' is not parsed'
        assert '"    ' + key + '\\t"' in definition_cpp, key + ' is not written by the editor'
    assert 'mDeathVanishSeconds = Helper::toDouble' in definition_cpp, 'DeathVanishSeconds is not read as a double'

    creature = read('source/entities/Creature.cpp')
    assert re.search(r'else if\(ko && !getDefinition\(\)->isWorker\(\) && !getDefinition\(\)->isUndead\(\)\)',
                     creature), 'takeDamage may knock out an undead creature'
    assert re.search(r'!mIsCarried && !getDefinition\(\)->isUndead\(\)\)\s*\n\s*dirtyTileByCorpse\(\)', creature), \
        'an undead creature dirties its tile by corpse'
    assert re.search(r'!getDefinition\(\)->isUndead\(\)\)\s*\n\s*DirtPileEntity::createOnTile\([^;]*DirtPileKind::blood',
                     creature), 'an undead creature leaves blood'
    assert re.search(r'!getDefinition\(\)->isWorker\(\) && !getDefinition\(\)->isUndead\(\)\)\s*\n\s*\{\s*\n\s*'
                     r'GhostEntity\* ghost = new GhostEntity', creature), 'an undead creature leaves a ghost'
    rip = creature.index('" RIP");')
    death_turn = creature[rip:creature.index('mDeathCounter = 1;', rip)]
    assert re.search(r'Spell::fireSpellEffect\(\*getPositionTile\(\), getDefinition\(\)->getDeathVanishEffect\(\)',
                     death_turn), 'DeathVanishEffect is not fired at death turn 0'
    vanish = re.search(r'mCorpseTurns \+= 1\.0;(.*?)return;', creature, re.S)
    assert vanish, 'the corpse clock is missing'
    vanish = vanish.group(1)
    assert re.search(r'mCorpseTurns >= getDefinition\(\)->getDeathVanishSeconds\(\) \* ODApplication::turnsPerSecond',
                     vanish), 'the body is not removed after DeathVanishSeconds'
    assert re.search(r'hasDeathVanishPile\(\).*?DirtPileEntity::createBones\([^;]*getPosition\(\).*?getLevelScale\(\)', vanish, re.S), \
        'DeathVanishPile does not preserve the skeleton position and scale'
    assert vanish.index('DirtPileEntity::createBones') < vanish.index('removeFromGameMap()'), \
        'the pile must be created before the body is removed'
    dirt = read('source/entities/DirtPileEntity.cpp')
    bones = function_body(dirt, 'DirtPileEntity* DirtPileEntity::createBones(')
    assert 'new DirtPileEntity' in bones and 'DirtPileKind::bones' in bones, 'each skeleton needs its own cleanable entity'
    assert 'bones->setPosition(position)' in bones and 'rotationAngle, scale' in bones, 'skeleton pose is not retained'
    cleaning = read('source/creatureaction/CreatureActionCleanTile.cpp')
    assert cleaning.count('DirtPileKind::bones') >= 2 and 'bones->cleanBy(cleanRate)' in cleaning, \
        'workers must find and clean skeletons'
    for signature in ('EntityCarryType Creature::getEntityCarryType(', 'bool Creature::takeCorpse(',
                      'bool Creature::reviveFromCorpse('):
        assert 'isUndead()' in function_body(creature, signature), signature + ' does not refuse an undead creature'

    crypt = read('source/rooms/RoomCrypt.cpp')
    gates = re.findall(r'getDefinition\(\)->isWorker\(\) \|\| creature->getDefinition\(\)->isUndead\(\)', crypt)
    assert len(gates) >= 3, 'the crypt refuses an undead corpse at ' + str(len(gates)) + ' of 3 gates'

    render = function_body(read('source/render/RenderManager.cpp'), 'void RenderManager::startCreatureDeathVariant(')
    assert re.search(r'if\(creature->getDefinition\(\)->isUndead\(\)\)\s*\n\s*return;', render), \
        'startCreatureDeathVariant tilts the Die clip of an undead creature'

    client = read('source/network/ODClient.cpp')
    assert 'triggerEvent("SpellFx" + family.substr(Spell::SPELL_EFFECT_PREFIX.size())' in client, \
        'the client does not turn spell effect families into SpellFx events'
    assert re.search(r'^\s*Event\s+SpellFxLichBeetles\s*$', read('config/roomAmbienceSpells.cfg'), re.M), \
        'the client has no effect for SpellFxLichBeetles'
    print('undead rules ok')


if __name__ == '__main__':
    main()
