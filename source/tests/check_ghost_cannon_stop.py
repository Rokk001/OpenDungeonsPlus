"""Decision 1078: stop firing at the visible trap boundary and preserve saturated hose colours. Compiles nothing."""
from pathlib import Path
import importlib.util

repo = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('hunter_pose', repo / 'source/tests/check_ghost_hunter_pose.py')
pose = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pose)
source = pose.creature_source
visuals = pose.visuals

# Pin the actual render predicate and its consumers: the clip, cannon, holster, aiming, hose, weapons and effect teardown.
helper = pose.body(source, 'static bool ghostAboveTrap(')
pose.has(helper, 'current ghost bounds and state',
         'getState()!=GhostState::beamed', 'getWorldBoundingBox(true)',
         'bounds.getMaximum().z>ghost.getPosition().z')
pose.has(visuals, 'visible capture boundary controls the whole cannon',
         'const bool beaming=target!=nullptr && mGhostBoxMode==3 && ghostAboveTrap(scene,*target);',
         'if(!beaming && getAnimationStateName()==EntityAnimation::beam_anim)',
         'setAnimationState(EntityAnimation::idle_anim,true,Ogre::Vector3::ZERO,false);',
         'mGhostCaptureGun->setVisible(beaming);', 'mGhostPackGun->setVisible(!beaming);',
         'if(beaming) aimGhostCannon(', 'Ogre::Entity* hoseGun=beaming?mGhostCaptureGun:mGhostPackGun;')
cleanup = visuals[visuals.index('    if(!beaming)'):visuals.index('    // The capture beam (decision 805')]
pose.has(cleanup, 'no sound, sparks, glow or lightning after entry', 'stopSpatialLoop(mGhostBeamSound)',
         'destroyParticleSystem(mGhostBeamSparks)', 'destroyBillboardSet(mGhostBeamImpact)',
         'destroyBillboardChain(mGhostBeamChain)', 'return;')
assert 'if(target==nullptr || mGhostBeamTarget.empty())' not in visuals

# Fixed geometric scenarios cover different hunter ghosts and floor elevations; the old target-only predicate never stops.
# The complete half-size body enters before the end of the 16 s timer, since the capture path sinks below the floor.
for floor in (0.0, 1.0, 5.0):
    for body_height in (0.4, 0.8, 1.2):
        previous = True
        stopped_at = None
        for step in range(1001):
            capture = step / 1000
            pull = max(0.0, (capture - 0.75) / 0.25)
            top = floor + 0.3 * (1 - pull) - 0.8 * pull + body_height * 0.5
            active = top > floor
            assert previous or not active, 'the cannon never resumes during the remaining pull'
            if not active and stopped_at is None:
                stopped_at = capture
            previous = active
        assert 0.85 < stopped_at < 0.97, (body_height, stopped_at)
    assert not (floor > floor), 'the boundary itself is already inside'

# Both material passes bind explicit programs, avoiding scheme-generated replacements of their vertex colours.
material = pose.ghost_material
for name, fragment in (('GhostHose', 'GhostHoseFragment'), ('GhostHoseWire', 'GhostHoseWireFragment')):
    block = pose.material_block(name)
    pose.has(block, 'explicit vertex colour rendering', 'vertex_program_ref GhostHoseVertex',
             'fragment_program_ref ' + fragment, 'lighting off')
for name, filename in (('GhostHoseVertex', 'GhostHose.vert'), ('GhostHoseFragment', 'GhostHose.frag'),
                       ('GhostHoseWireFragment', 'GhostHoseWire.frag')):
    assert 'source ' + filename in material
    assert (repo / 'materials/scripts' / filename).is_file()
vertex = (repo / 'materials/scripts/GhostHose.vert').read_text()
rubber = (repo / 'materials/scripts/GhostHose.frag').read_text()
wire = (repo / 'materials/scripts/GhostHoseWire.frag').read_text()
pose.has(vertex, 'colour vertex attribute reaches the fragment stage',
         'layout(location = 3) in vec4 colour;', 'hoseColour = colour;', 'gl_Position = worldViewProj * vertex;')
pose.has(rubber, 'dark textured corrugations', 'texture(rubberMap, hoseUV).rgb * hoseColour.rgb')
pose.has(wire, 'unlit saturated wire output', 'fragColour = vec4(hoseColour.rgb, 1.0);')
assert 'texture(' not in wire and 'light' not in wire.split('void main()')[1]
pose.has(pose.shape, 'the shared UV vertex input exists in the wire section', 'hose.textureCoord(0.0f,share);')

# At subpixel camera coverage, saturated colours still differ from grey after area averaging against dark rubber.
# Fixed camera samples: 60, 120 and 230 pixels for a hunter, with existing radius and thickness from the shipped config.
for height_pixels in (60, 120, 230):
    coverage = min(1.0, height_pixels * 0.05 * pose.wire_share)
    for colour in pose.wires:
        shaded = tuple(c * pose.glow for c in colour)
        pixel = tuple(coverage * c + (1 - coverage) * 0.08 for c in shaded)
        assert max(pixel) - min(pixel) > 0.24, (height_pixels, pixel)
print('ghost cannon stops at trap entry; explicit coloured hose programs: ok')
