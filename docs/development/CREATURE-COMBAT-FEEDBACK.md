# Creature combat feedback

## Scope

Creature melee combat now cycles through the attack clips already provided by
each model and plays them faster. Successful creature hits add a short impact
reaction. Armed opponents produce a compact spark burst, while applied body
damage produces a restrained blood burst. The blood presentation can be disabled
on the Game page in Settings; sparks and combat rules remain unchanged.

Death clips play slightly faster. The Cultist and Lich models, whose authored
death clips do not finish in a usable lying pose, use the same short model-based
fall and grounded alignment as hand drops. Other creatures retain their authored
death clips.

## Existing path and integration

The combat-only animation request is emitted by the existing creature attack
path. The renderer resolves it to the model's available attack variants without
changing non-combat uses of the original attack animation. The existing melee
damage result and equipped weapons classify the presentation-only impact payload;
health, defense, targeting, timing and sound calculations are unchanged.

Impact notifications are sent only to human players with vision of the target.
The client owns the short-lived particles and target scale reaction and removes
them when they finish, when the creature disappears or when the renderer stops.
The new notification value is appended to preserve existing protocol numbering.

## Verification boundary

The source-path probe passes 19 checks covering combat-only animation selection,
speed changes, server/client notification flow, simultaneous weapon/body effects,
the blood setting, fallback death models and cleanup. The production particle
scripts pass 22 real Ogre resource and live-emission checks; their isolated spark
and blood render was visually inspected. The real Ogre creature lifecycle probe
passes 386 checks across all 33 distinct creature meshes, including rotating
attack variants and grounded Cultist/Lich death falls. The settings layout passes
the existing headless multi-resolution and UI-scale probe.

The Windows Release target compiles successfully, runtime preparation passes and
CTest has no registered tests.
The implementation agent did not launch the game, so final combat timing and
appearance still require the documented manual check.

Version 0.7.1 remains unchanged because no release was requested.
