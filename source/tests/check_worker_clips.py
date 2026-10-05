#!/usr/bin/env python3
"""Pure check (nothing compiled, nothing started): the clips that the worker events of
config/creatureReactions.cfg name exist in both worker skeletons, the older clips are still there, and the events
that decorate a running animation (WhileWorking) do not name a clip because the framework never plays one over them."""
import re
from pathlib import Path

root = Path(__file__).resolve().parents[2]
cfg = (root / 'config' / 'creatureReactions.cfg').read_text(encoding='utf-8')
WORKER_CLIPS = ('PickUp', 'PutDown', 'Toss', 'Pat', 'Hammer', 'Shove', 'Panic', 'Cheer', 'Sweep', 'Sharpen', 'Lean', 'Rest')
OLD_CLIPS = ('Idle', 'Walk', 'Attack1', 'Die', 'Dig', 'Claim', 'Drag')
skeletons = {name: (root / 'models' / (name + '.skeleton')).read_bytes() for name in ('Dwarf1', 'Kobold')}

used = set()
for match in re.finditer(r'\[Event\](.*?)\[/Event\]', cfg, re.S):
    body = match.group(1)
    name = re.search(r'Name\s+(\S+)', body).group(1)
    clips = re.findall(r'^\s*Clip\s+(\S+)', body, re.M)
    if re.search(r'^\s*WhileWorking\s+yes', body, re.M):
        assert not clips, name + ' decorates a running animation, no clip can be played over it'
    for clip in clips:
        if clip in WORKER_CLIPS:
            used.add(clip)
assert used == set(WORKER_CLIPS), sorted(set(WORKER_CLIPS) - used)

for skeleton, data in skeletons.items():
    for clip in WORKER_CLIPS + ('Flee',) + OLD_CLIPS:
        assert clip.encode() in data, skeleton + ' has no ' + clip

print('worker clips: ok')
