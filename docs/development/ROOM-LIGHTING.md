# Room lighting and colour readability

Work branch: `fix/room-lighting`, from complete fork checkpoint `65506edf`.
The shared checkout and its normal index remain untouched, following the
existing isolated-commit workflow; preserve all parallel and local work.

## Existing path and diagnosed gaps

The user authorized completing room illumination and a brighter, more colourful
world, preserving the accepted shadow correction. The renderer already provides
map lights with colour, attenuation and flicker; room creation does not supply
any. The user's reviewed save contains no map lights, leaving the cursor as its
only direct world light. Custom materials read only light zero, so additional
lights cannot accumulate as they do in Ogre-generated materials. Most custom
world shaders also halve the scene's ambient colour, unlike the generated path.

Extend the existing rendering path instead of adding a fullscreen colour filter
or replacing existing textures. First verify and correct multiple-light
accumulation and ambient consistency, retaining depth shadows and falloff; then
attach room illumination to existing visible room geometry, with lifetime and
visibility controlled by the existing client rendering path. Check the actual
result against the retained visual evidence before selecting light parameters.
The private comparison record and all reference names remain under
`docs/internal/`; exact original renderer constants must not be claimed without
evidence.

Camera controls and map navigation are separate subsequent work branches;
the user resolved shortcut conflicts in favour of the reference commands, with
existing functions retained through their menus. Do not include those changes
in this lighting contribution and do not push without new authorization.

## Verification

Custom world shaders now accumulate the existing pass's lights (up to Ogre's
default eight), applying attenuation to each direct contribution and the existing
single shadow map only to its first shadow-casting light. The scene ambient
value reaches visible terrain without the former extra halving; creature
ambient factors and the fog material's dimming remain intact.

Visible room tiles share one non-shadow-casting point light per three-by-three
patch, including partial patches and small rooms. Its location follows the
visible tiles' centroid at height three, with six-tile range, the existing cursor
falloff coefficients and the map-light warm colour scaled by patch density.
These are local rendering parameters tuned for readable textures, not claimed
original executable constants. Tile refresh, sale, visibility updates and tile
destruction control creation/removal; no room state, packets or save format change.
Lights live beneath the existing light scene node, retaining minimap suppression.

The initial real-render comparison failed seven custom material cases: each
surface consumed only one of two overlapping coloured lights, whereas the
generated-material control passed. The correction passes all eight overlap and
additivity cases. Ten further room checks pass: lifecycle, edge patches,
duplicate prevention, cursor-independent illumination, furnished-room shadow
toggle/restoration, vision loss, sale and complete light/node cleanup.
The scene contains 121 room tiles with 16 lights; 151,947 pixels brighten without
white clipping. The lifecycle test uses the production renderer method and real
Ogre lights with small Tile/GameMap storage adapters; the game build validates
their actual API and the real visibility/update call sites were inspected.

All 60 ambient/falloff checks, 73 receiver cases, 146 settings checks and actual
instanced-fog/vertical-wall renders pass. The furnished comparison also includes
nine bookshelves and a Wizard. Sources and evidence are retained under
`build/windows/make-room-light-probe.py`, `room-light-*.log/png`,
`room-coverage-*.log` and `room-surface-*.log`; the original seven-failure control
is `room-light-before.log`.

Windows Release compilation and runtime preparation pass in
`room-lighting-build.log` and `room-lighting-runtime.log`. The prepared executable
is dated September 6, 2026 at 19:38:14, SHA-256
`26b63a78da44873fe3eb27c9dd843bb2305db2084bee434052a7da143ec0b187`.
No game was launched by the assistant. On September 6, the user confirmed that
the lighting appearance is good. Linux runtime and the individual build/sell,
shadow-toggle and hidden-terrain lifecycle scenarios remain unreported.

Version remains 0.7.1: this development work does not define a release.
The README and development index describe the new room illumination; there is
no changelog. No push or upstream PR is authorized for this new contribution.
