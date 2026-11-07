"""Decision 727, case floating dead creatures: a dead creature lies on the floor at floor height.

Root cause (found by reading the history): RenderManager::updateCreatureStep computed the step lift for every creature,
also for a dead body that is carried or dragged to its grave. A body that arrived on a coffin (steppable until decision
727) stayed in mSteppingCreatures at the lid height of 0.77 to 0.84 and floated in the graveyard. A dead body now gets no
furniture lift (only the gold of a treasury, which hides the floor, still lifts it), and the per-frame update of the
stepping set drops a lift that a body had when it died on a bed.
No compiler needed."""
from pathlib import Path

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding='utf-8').replace('\r\n', '\n')


def between(text, start, end):
    assert start in text, start
    part = text.split(start, 1)[1]
    assert end in part, end
    return part.split(end, 1)[0]


render = read('source/render/RenderManager.cpp')
step = between(render, 'void RenderManager::updateCreatureStep', 'void RenderManager::cancelCreatureStep')
assert 'const bool canStep = creature->isAlive();' in step
loop = between(step, 'for(RenderedMovableEntity* candidate', 'lift += goldHeight + pourRise;')
assert 'if(!canStep ||' in loop.split('continue;')[0]
# the lift reaches the node, and a creature without lift leaves the stepping set
assert 'node->setPosition(position + Ogre::Vector3(0, 0, lift));' in step
assert 'mSteppingCreatures.erase(creature);' in step
# the per-frame update walks the stepping set: a body that was lifted before its death is lowered on the next frame
assert ('for(std::set<Creature*>::iterator it = mSteppingCreatures.begin(); it != mSteppingCreatures.end();)\n'
        '        updateCreatureStep(*it++);') in render
# the lying pose code (ground poses) is not touched by the step lift
assert 'mCreatureGroundPoses' not in step


# model of the lift of one creature on furniture: the same decision as the code
def lift(alive, steppable_mesh, rise, gold=0.0):
    return (rise if (alive and steppable_mesh) else 0.0) + gold


assert lift(True, True, 0.7) == 0.7      # a living creature still steps onto a bed
assert lift(False, True, 0.7) == 0.0     # a body on a bed lies on the floor
assert lift(False, False, 0.0) == 0.0    # a body on a grave lies on the floor

# the graves cannot lift a living creature either (the other half of the cause)
bounds = read('source/gamemap/RoomObjectBounds.h')
rule = between(bounds, 'inline bool isSteppableMesh(const std::string& name)', '\n}\n')
assert 'Coffin' not in rule
print('ok')
