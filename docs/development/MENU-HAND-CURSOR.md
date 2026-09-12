# Hand cursor on return to the main menu

The game and menu share the same overlay hand. F9 can hide it during gameplay;
neither game-renderer teardown nor menu entry restores that visibility, while
the CEGUI cursor image is intentionally empty. Returning through F10 therefore
retains an invisible pointer when gameplay left the hand hidden.

Restore the existing hand visibility once on menu reset, using its current
visibility query and toggle, without changing the in-game F9 behavior, accepted
hand animations or menu atmosphere. Repeated menu entry must not toggle a
visible hand off. This is the identified reproducible retained-state case;
the user's intermittent scenario still needs their gameplay retest.

The old menu entry fails the repeated hidden-to-menu regression; the corrected
entry passes 60 checks. The actual Ogre hand/creature probe passes all 2,453
checks, including restored hand visibility, repeated entry and held-model
parenting. Release compilation and runtime preparation pass; no game was run.
