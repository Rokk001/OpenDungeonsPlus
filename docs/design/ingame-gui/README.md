# In-game GUI design reference — variant A

Approved visual references for the in-game GUI: quiet black iron, worn charcoal stone, asymmetric edge damage, newly painted dimensional icons and readable serif text.

These images define the visual treatment, not new gameplay, controls or layout geometry. Existing widget names, positions, functions and key bindings remain authoritative. Individual creature profiles belong in Dungeonbook; no extra creature-detail window is introduced. The existing creature overview and its aggregate counts remain.

The HUD reference is `vorschlag-A-hud-korrigiert.png`, supported by the building, spells, traps, creature overview and digging images. Older screenshots behind settings and player-information concepts define their WINDOW treatment only; their historical HUDs do not replace the current HUD.

See [GENERATION-PROMPT.md](GENERATION-PROMPT.md) for verbatim generation prompts, inputs, provenance and reuse instructions. All 21 PNGs are delivered at 1920 × 1200. They are design references, not runtime skin atlases. Asset attribution and GPLv3+ licensing are recorded in the root CREDITS file.

| Image | Screen or window | Existing layout |
|---|---|---|
| [vorschlag-A-hud-korrigiert.png](vorschlag-A-hud-korrigiert.png) | Complete HUD, rooms tab | `gui/ModeGame.layout`; `gui/WindowTabRooms.layout` |
| [vorschlag-A-dungeonbook-final.png](vorschlag-A-dungeonbook-final.png) | Dungeonbook feed | `gui/WindowSocial.layout` |
| [vorschlag-A-optionen-final.png](vorschlag-A-optionen-final.png) | In-game options | `gui/WindowGameOptions.layout` |
| [vorschlag-A-forschungsbaum.png](vorschlag-A-forschungsbaum.png) | Research tree | `gui/WindowSkillTree.layout` |
| [vorschlag-A-dungeonbook-profil.png](vorschlag-A-dungeonbook-profil.png) | Dungeonbook creature profile | `gui/WindowSocial.layout`; `gui/WindowCreatureProfilePage.layout` |
| [vorschlag-A-ziele.png](vorschlag-A-ziele.png) | Objectives checklist | `gui/WindowObjectives.layout` |
| [vorschlag-A-ereignismeldung.png](vorschlag-A-ereignismeldung.png) | Event message | `gui/WindowGameEvent.layout` |
| [vorschlag-A-kreaturenuebersicht.png](vorschlag-A-kreaturenuebersicht.png) | Creature type overview and aggregate counts | `gui/ModeGame.layout`; `gui/WindowTabCreatures.layout` |
| [vorschlag-A-bauen.png](vorschlag-A-bauen.png) | Room construction, cost and size hint | `gui/ModeGame.layout`; `gui/WindowTabRooms.layout` |
| [vorschlag-A-grabauswahl.png](vorschlag-A-grabauswahl.png) | Digging selection and size hint | `gui/ModeGame.layout`; `gui/WindowTabRooms.layout` |
| [vorschlag-A-zauber.png](vorschlag-A-zauber.png) | Spells tab | `gui/ModeGame.layout`; `gui/WindowTabSpells.layout` |
| [vorschlag-A-fallen.png](vorschlag-A-fallen.png) | Traps tab | `gui/ModeGame.layout`; `gui/WindowTabTraps.layout` |
| [vorschlag-A-produktion.png](vorschlag-A-produktion.png) | Trap production and order priority | `gui/WindowProduction.layout` |
| [vorschlag-A-spielerinformationen.png](vorschlag-A-spielerinformationen.png) | Player information and teams | `gui/WindowPlayerSettings.layout` |
| [vorschlag-A-sandbox.png](vorschlag-A-sandbox.png) | Sandbox toolbox and invasions | `gui/WindowSandbox.layout` |
| [vorschlag-A-einstellungen.png](vorschlag-A-einstellungen.png) | Settings navigation | `gui/WindowSettingsNavigation.layout` |
| [vorschlag-A-grafikeinstellungen.png](vorschlag-A-grafikeinstellungen.png) | Video settings | `gui/WindowSettings.layout` |
| [vorschlag-A-toneinstellungen.png](vorschlag-A-toneinstellungen.png) | Audio settings | `gui/WindowSettings.layout` |
| [vorschlag-A-steuerungseinstellungen.png](vorschlag-A-steuerungseinstellungen.png) | Input settings | `gui/WindowSettings.layout` |
| [vorschlag-A-spieleinstellungen.png](vorschlag-A-spieleinstellungen.png) | Game settings | `gui/WindowSettings.layout` |
| [vorschlag-A-neustart-bestaetigung.png](vorschlag-A-neustart-bestaetigung.png) | Restart confirmation and end-game menu | `gui/WindowQuit.layout`; `gui/WindowGameOptions.layout` |
