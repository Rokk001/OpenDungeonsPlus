# Room demolition effect

## Existing path and scoped change

The gameplay sale handler removes eligible room tiles, credits the existing
refund and sends refreshed tiles to each human client with vision; no visual
effect is requested. Room construction already has a bounded per-tile particle
burst, gameplay-only client dispatch and render-time/scene-teardown cleanup.

Reuse that presentation message after the demolition tile refresh, carrying
only the successfully removed tiles visible to that recipient. Reuse the
existing particle asset and renderer lifetime unchanged rather than introduce
another protocol message or infer demolition from ambiguous tile snapshots.
Single-tile and rectangular room sales share this path; failed removals,
ineligible tiles, unseen tiles, editor operations and map loading must not
trigger it. Refunds, room updates, sounds and selection stay unchanged.

No release/version change is requested; controls and gameplay rules do not
change, so the root README and release changelog need no update.

## Verification

The compiled production sale-handler fixture reproduces ten missing-effect
failures before the change and passes all 62 checks afterwards, including exact
per-recipient tile lists, refresh-before-effect order, single/multi-tile sales,
partial/no vision, failed/duplicate/foreign/unsellable requests and editor
exclusion. The accepted selection/refund regression passes all 42 checks.
Networking and map endpoints are controlled substitutes, not a multiplayer run.

The existing construction dispatch/lifecycle source probe passes 12 checks, and
the installed Ogre particle probe passes ten checks against the unchanged assets.
An isolated hidden-window rendering displays nine tile bursts with 324 live
particles; its generated preview was inspected. No game was launched; actual
in-game demolition appearance remains for the user to accept. Release/deployment
evidence is recorded in BUILDING.md.
