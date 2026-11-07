"""X1, decisions 826, 827, 829, 830(a): the crypt findings of the owner check. No compiler needed.

Root causes (found by reading the code):
1  Graves and statues danced: roomAmbienceWakeClips.cfg looped the clip Sleep on all coffins and statues When Always, and
   roomAmbienceCare.cfg wobbled both coffins (CryptBonesRattle). They stand still now and move only with the clip Wake
   when a creature is raised (CryptRaised).
2  The brown, ragged, flat shapes that moved on the floor between the graves were the model effect CryptGraveMound
   (GraveMound.mesh, Pulse motion, every 6th crypt tile, no grave there). The effect is removed.
3  The crypt built the seated KnightStatue on the left and right spots (toilet look): KnightStatue2 stands everywhere now.
4  A delivered body was dragged to the tile beside the grave and lay there next to or across the coffin; it is now pulled
   on into its grave tile (RoomCrypt::getReservedGrave) and is never lifted (decision 727).
5  Skeletons at crypt graves: CryptRaised and the revival light fired for any creature that appeared on a crypt tile, and
   Raise Dead could take a body that lay on a crypt tile. The event is only raised for CryptSpawnClass (Lich), the revival
   light follows that event, a body on a crypt tile cannot be taken for Raise Dead, and the lich stretches on rising.
"""
from pathlib import Path
import re

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding='utf-8').replace('\r\n', '\n')


def effect_names(text):
    return set(re.findall(r'^\s*Name\s+(\S+)', text, re.M))


def effect(text, name):
    start = text.index('Name        ' + name + '\n')
    return text[start:text.index('[/Effect]', start)]


clips = read('config/roomAmbienceWakeClips.cfg')
care = read('config/roomAmbienceCare.cfg')
crypt = read('source/rooms/RoomCrypt.cpp')
rooms = read('config/rooms.cfg')

# 1 nothing of the crypt moves by itself
assert 'CryptSleepClip' not in effect_names(clips)
assert 'CryptBonesRattle' not in effect_names(care)
for text in (clips, care):
    for name in effect_names(text):
        body = effect(text, name)
        if re.search(r'Match\s+.*(Coffin|KnightStatue)', body):
            assert 'Kind        Motion' not in body, name
            assert not ('Kind        Clip' in body and 'When        Always' in body), name
wake = effect(clips, 'CryptWakeClip')
assert 'Event       CryptRaised' in wake and 'Clips       Wake' in wake and 'Loop' not in wake

# 2 no moving mound models on the crypt floor
assert 'CryptGraveMound' not in effect_names(care)
assert 'GraveMound' not in care

# 3 only the standing statue
stat = set(re.findall(r'new BuildingObject\(getGameMap\(\), \*this, "(Knight[A-Za-z0-9]*Statue[A-Za-z0-9]*|KnightStatue[A-Za-z0-9]*)"', crypt))
assert stat == {'KnightStatue2'}, stat
assert crypt.count('"KnightStatue2"') == 4

# 4 the body is laid into its grave
header = read('source/rooms/RoomCrypt.h')
assert 'getReservedGrave' in header and 'RoomCrypt::getReservedGrave' in crypt
carry = read('source/creatureaction/CreatureActionCarryEntity.cpp')
lay = carry[carry.index('void CreatureActionCarryEntity::startLaying'):carry.index('bool CreatureActionCarryEntity::stopDragging')]
assert 'getCryptGrave(dragged)' in lay and 'graveTile->getX()' in lay
assert 'getReservedGrave(dragged, mTileDest)' in carry
assert 'getCryptGrave(*dragged)' in carry
render = read('source/render/RenderManager.cpp')
step = render[render.index('void RenderManager::updateCreatureStep'):render.index('void RenderManager::cancelCreatureStep')]
assert 'const bool canStep = creature->isAlive();' in step

# 5 only liches rise from the graves
assert re.search(r'CryptSpawnClass\s+Lich', rooms) and re.search(r'PrisonSpawnClass\s+Skeleton', rooms)
ambience = read('source/render/RoomAmbience.cpp')
raised = ambience[ambience.index('A creature of the class the crypt raises'):ambience.index('change.mEvent = "CryptRaised";')]
assert 'getClassName()' in raised and '"CryptSpawnClass"' in raised
assert 'Event       CryptRaised' in effect(care, 'CryptRevivalLight')
assert 'CreatureArrived' not in effect(care, 'CryptRevivalLight')
take = read('source/entities/Creature.cpp')
take = take[take.index('bool Creature::takeCorpse()'):take.index('bool Creature::reviveFromCorpse')]
assert 'RoomType::crypt' in take and take.index('RoomType::crypt') < take.index('mDeathCounter = std::numeric_limits')
lich = effect(clips, 'CryptRaiseLichClip')
assert 'Kind        CreatureClip' in lich and 'Event       CryptRaised' in lich
assert b'Stretch' in (repo / 'models/lich.skeleton').read_bytes()
print('ok')
