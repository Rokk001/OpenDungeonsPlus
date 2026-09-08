# Community exit page

Work branch: `feature/community-exit-page`, from the complete fork checkpoint
`b61fef61`.

The existing main-menu Quit action already opens `AdvertMode`, which loads
`gui/Advertisment.layout`. The page already contains the community message and
Discord invite, so a separate exit flow is unnecessary. Its full-screen root is
currently subscribed to quit on every click, while the text link both quits and
launches `xdg-open`; this makes the actions visually unclear and leaves the link
unsupported on Windows.

Keep the existing mode, background artwork, invite URL and exit behavior. Replace
the loose text rows with a centred, skinned community panel and two explicit
buttons: one opens Discord and exits, and one only exits. Remove the full-screen
click-to-close subscription and use the existing button styling. Launch the
fixed invite URL through the platform's standard command on Windows, macOS and
other supported desktop systems.

## Implementation and verification

`gui/Advertisment.layout` now presents the existing artwork behind a centred
community panel using the installed menu skin. The title and invitation remain
readable without clipping, and the Discord and Close buttons have separate,
non-overlapping hit targets. Only those buttons act: Discord opens the existing
invite before exit, while Close exits without opening a browser.

The real Ogre/CEGUI render probe passes 150 checks across 800x600, 1280x720,
1920x1080, 3440x1440 and 3840x2160 at 80, 100 and 120 percent UI scaling. It
loads the production layout, fonts, skin and background, verifies text fit,
viewport bounds and both hit targets, and renders
`build/reference-audit/community-exit-page.png`. Reproduce it with
`build/windows/build-community-exit-preview.ps1`.

The Windows Release build and runtime preparation pass. The executable is dated
2026-09-08 22:54:32, is 4,490,752 bytes and has SHA-256
`8F84BD5703D825E8F9D1327EFFE3768E5EBE3DC228E2E35DB4B411A080913773`.
The user confirmed the completed page and both actions in game on September 8,
2026. The automated probe does not launch external applications.

Version 0.7.1 remains unchanged because no release was requested. The existing
README Discord reference remains accurate, and this unreleased interface change
does not require a release-note entry.
