"""Noncompiling contact arithmetic and lifecycle regressions, tied to production expressions.

These fixtures exercise translated/scaled/turned models and animation phases; source assertions
check scheduling, packet identity, late visibility, save reconstruction, laying and abort wiring.
They do not replace an Ogre runtime visual test.
"""
from pathlib import Path
import math
import re

root = Path(__file__).resolve().parents[2]
creature = (root / 'source/entities/Creature.cpp').read_text()
render = (root / 'source/render/RenderManager.cpp').read_text()
carry = (root / 'source/creatureaction/CreatureActionCarryEntity.cpp').read_text()
crypt = (root / 'source/rooms/RoomCrypt.cpp').read_text()


def body(text, signature):
    """Extract one top-level production function."""
    return text.split(signature, 1)[1].split('\n}\n', 1)[0]


class Vec:
    """Small vector fixture for evaluating the production contact displacement."""
    def __init__(self, *xyz):
        self.xyz = xyz

    def __add__(self, other):
        return Vec(*(a + b for a, b in zip(self.xyz, other.xyz)))

    def __sub__(self, other):
        return Vec(*(a - b for a, b in zip(self.xyz, other.xyz)))

    def _getDerivedPosition(self):
        return self


def world(origin, scale, turn, bone):
    """Fixture equivalent of a node's full world transform, including nonuniform scale."""
    x, y, z = (a * b for a, b in zip(scale, bone))
    return origin + Vec(x * math.cos(turn) - y * math.sin(turn),
                        x * math.sin(turn) + y * math.cos(turn), z)


contact = body(render, 'void RenderManager::rrApplyDragContact(')
expression = re.search(r'contactPosition = ([^;]+);', contact)[1].replace('->', '.')
# Evaluate the exact production expression at four animated phases, two sizes and a right-angle turn.
fixtures = (
    (0, 0.3, (11.25, 7.06, 0.21)), (0, 2.0, (10.4, 7.4, 0.04)),
    (0.25, 0.3, (11.25, 7.135, 0.21)), (0.25, 2.0, (10.4, 7.475, 0.04)),
    (0.5, 0.3, (11.25, 7.21, 0.21)), (0.5, 2.0, (10.4, 7.55, 0.04)),
    (1, 0.3, (11.25, 7.36, 0.21)), (1, 2.0, (10.4, 7.7, 0.04)),
)
for phase, size, expected in fixtures:
    dragged = Vec(9, 4, 0)
    hand = world(Vec(11, 7, 0), (0.3, 0.4, 0.3), math.pi / 2, (phase, -1, 0.8))
    ankle = world(dragged, (size, size / 2, size), -math.pi / 2, (0.2, 1, 0.1))
    moved = eval(expression, {'__builtins__': {}}, dict(bodyNode=dragged, hand=hand, ankle=ankle))
    assert all(abs(a - b) < 1e-10 for a, b in zip(moved.xyz, expected)), (phase, size, moved.xyz)

# Missing worker/mesh/bone must be retried, without dropping identity or dereferencing null rigs.
tether = body(creature, 'void Creature::updateDragTether()')
assert 'worker == nullptr' in tether and 'mDragWorkerName.clear()' not in tether
assert 'hasEntity(bodyName)' in contact and 'hasEntity(workerName)' in contact
bone = body(render, 'static bool dragBonePoint(')
assert 'hasSkeleton()' in bone and 'hasBone(name)' in bone
assert bone.index('_updateAnimation()') < bone.index('_getDerivedPosition()')
assert 'getBoundingBox()' in contact and 'bounds.isNull() || bounds.isInfinite()' in contact
# Laying clears only the live grip; saved carrier, carry lock and decay hold remain until delivery ends.
lay = body(creature, 'void Creature::notifyDragLaying()')
assert 'mDragWorkerName.clear();' in lay and 'mNeedFireRefresh = true;' in lay
assert 'mCorpseCarrierName' not in lay and 'mIsCarried' not in lay and 'mIsBeingDragged' not in lay
start_lay = body(carry, 'void CreatureActionCarryEntity::startLaying(')
assert start_lay.index('notifyDragLaying()') < start_lay.index('setWalkPath(')
assert 'if(mExternalDrag)\n        path.clear();' in start_lay
assert 'if(graveTile == nullptr)' in start_lay and 'if(graveTile != nullptr)' in start_lay
assert 'CORPSE_CARRIER_SAVE_LABEL << mCorpseCarrierName' in creature
assert 'mCorpseCarrierName = appearanceToken.substr' in creature
assert 'carrier->pushAction(Utils::make_unique<CreatureActionCarryEntity>(*carrier, *creature, *this))' in crypt
end = body(creature, 'void Creature::notifyDragEnd()')
assert 'mDragWorkerName.clear();' in end and 'mNeedFireRefresh = true;' in end
release = body(carry, 'CreatureActionCarryEntity::~CreatureActionCarryEntity()')
assert 'mExternalDrag && !mDelivered' in release and 'clearDestinations(EntityAnimation::die_anim' in release
assert 'notifyCorpseDragEnd()' in release and 'notifyDragEnd()' in release
assert 'mDragContactCreatures.erase(curCreature)' in render
assert 'mDragContactPositions.erase(curCreature)' in render
assert 'rrResetDragContacts();' in (root / 'source/render/ODFrameListener.cpp').read_text()
assert 'node->getPosition() == contact.second.second' in render
assert 'dragged.setPosition(' not in contact
assert 'startLaying(*dragged);' in body(carry, 'void CreatureActionCarryEntity::startDrag()')
print('drag contact: 8 world-transform fixtures and lifecycle wiring passed')
