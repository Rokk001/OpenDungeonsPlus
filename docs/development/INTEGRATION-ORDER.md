# Merge-Reihenfolge für `integration/all`

Stand: 28.09.2026. Datenbasis: `origin` und `upstream` frisch gefetcht, `origin/main` = `upstream/shaders-improvement` = `21320e9d`. Menge: die 83 offenen PRs laut `gh pr list` (gegen die PR-Liste und die Branch-Spitzen abgeglichen, alle identisch). Die gemergten PRs #109 und #110 sind nicht dabei. Diese Reihenfolge und die Regeln unten sind von Mario freigegeben; `integration/all` wird genau so aufgebaut. Jede Konfliktauflösung steht in der Message des jeweiligen Merge-Commits.

**Kurz:** 83 Merge-Schritte in 11 Gruppen. Im Probelauf mit der Konfliktregel unten haben 43 Schritte Konflikte, 40 laufen ohne Konflikt durch. Der grösste Einzelpunkt ist Schritt 69 (`pr/saved-game-browser-complete`, #218), siehe "Sonderfall #218".

## Die Regeln in einfachen Worten

1. **Chronologisch.** Mario hat immer vom letzten Stand aus weitergearbeitet. Deshalb kommen die Branches in der Reihenfolge, in der ihre Arbeit entstanden ist. Massgeblich ist das Commit-Datum (Committer-Datum) des neuesten eigenen Commits, der **kein** reiner Stil-Commit ist.
   - Nicht mitgezählt werden die Stil-Commits "refactor: spell out variable types instead of auto" (Liste unten). Sie entstanden am 24.09. in einem einzigen Durchgang und sagen nichts über die Entstehung der Arbeit.
   - Ebenfalls nicht mitgezählt werden reine Merge-Commits (z.B. "Merge current upstream base"). Sie holen nur fremde Stände herein. Das betrifft 8 Branches; bei ihnen steht das Merge-Datum zusätzlich in der Tabelle.
   - "Eigen" heisst: steckt weder in upstream noch in einem Vorgänger-Branch.
2. **Vorgänger zuerst (harte Regel).** Steckt Branch A in der Git-Historie von Branch B, kommt A immer vor B. Das hat die Datumsreihenfolge nur an einer Stelle verändert (#205 und #62 haben dieselbe Sekunde).
3. **Gleiches Datum:** dann entscheidet die PR-Nummer.
4. **Jeder Branch ist ein eigener Schritt**, auch die Glieder von Ketten (z.B. Herz-Kette H1 bis H6) und gemeinsame Basen (z.B. `feature/windows-support`, `feature/live-settings`). Begründung: Jeder Branch steht für einen Zeitpunkt in Marios Arbeit. Einzeln gemergt bildet `integration/all` diese Zeitlinie am genauesten ab, und ein Konflikt zeigt sich genau bei dem Feature, das ihn verursacht. Ein Branch, dessen Vorgänger schon drin ist, bringt nur noch seine eigene Änderung mit. Deshalb kommt kein Branch "implizit" über eine Spitze.
5. **Konfliktregel: der spätere Commit gewinnt.** Wo beide Seiten dieselbe Stelle geändert haben (ein "Hunk"), wird für beide Seiten mit `git blame` ermittelt, aus welchem Commit die Zeilen stammen. Die Seite mit dem jüngeren Commit gewinnt, die andere Fassung dieses Hunks entfällt. Alles, was nicht kollidiert, bleibt von beiden Seiten erhalten wie bei einem normalen Merge.
   - Beim Blame werden die Stil-Commits übersprungen (`git blame --ignore-revs-file`, Datei mit den SHAs aus der Liste unten). Entscheidend ist die inhaltliche Zeile.
   - Hat eine Seite die Stelle gelöscht (leere Seite im Hunk), zählt das Datum des jüngsten inhaltlichen Commits dieser Seite an dieser Datei.
   - Löscht eine Seite eine ganze Datei und die andere ändert sie, gewinnt die jüngere der beiden Aktionen.
   - Gleiches Datum: Der gerade gemergte Branch gewinnt, weil er in der Reihenfolge später kommt.
   - Entfernt ein späterer Commit etwas, das ein früherer eingefügt hat, gilt das als gewollte Entscheidung und nicht als Datenverlust (Vorgabe Mario).
6. **Stilregel bleibt: kein `auto`** (CLAUDE.md). Gewinnt inhaltlich eine Seite, die an dieser Stelle noch `auto` enthält, bleibt deren Inhalt, aber die Typen werden so ausgeschrieben wie in den Stil-Commits. Im Probelauf enthielt kein gewinnender Konflikt-Hunk noch `auto`. Im simulierten Endstand stehen nur noch drei `auto` aus upstream (`EventHandler.h`, `Pathfinding.h`, `test_ConsoleInterface.cpp`), die auch #196 nicht ersetzt.
7. **Nach jeder Gruppe** wird kompiliert (Release) und kurz gestartet. `git rerere` wird vor dem ersten Merge eingeschaltet (`git config rerere.enabled true`). Beim ersten Aufbau wurde nicht kompiliert (Builds nur einzeln und durch Mario); stattdessen wurde nach jeder Gruppe statisch geprüft (keine Konfliktmarker, kein neues `auto`, keine doppelten Definitionen oder Includes in Konfliktdateien), und Mario testet den Endstand.
8. **Referenz** für den gebauten und getesteten Stand ist `full-build-h1-h7`. Der Vergleich damit ist ein eigener, späterer Schritt (siehe "Vergleich mit full-build-h1-h7").
9. **Zuschnitt-Commits zählen nicht** (Entscheidung Mario). Ein Commit, der einen PR nur zuschneidet, also Arbeit anderer Features aus dem PR-Branch entfernt, damit der PR klein bleibt, ist keine inhaltliche Entscheidung. Seine Löschungen und Rücknahmen werden nicht übernommen. Einziger solcher Commit: `c28f93de` in #218, siehe "Sonderfall #218".
10. **`full-build-h1-h7` hat bei echten Kollisionen Vorrang** (Regel Mario, gilt für alle Schritte). Ändern beide Seiten dieselben Zeilen, gewinnt die Fassung, die in `full-build-h1-h7` (Marios zuletzt gebauter und getesteter Stand) steht. Erst wenn `full-build-h1-h7` keine der beiden Fassungen enthält, gilt Regel 5 ("späterer inhaltlicher Commit gewinnt"). Beim Vergleich gelten `auto` und ausgeschriebene Typen als gleiche Fassung; ist die Datei in `full-build-h1-h7` umbenannt, wird sie über den Dateinamen gesucht. Enthält `full-build-h1-h7` beide Fassungen oder nur Teile davon, gewinnt die nähere Fassung, und der Fall ist in der Merge-Commit-Message als "unsicher" markiert. Die Stilregel (kein `auto`) gilt weiter.

### Wie die Regeln beim Auflösen angewendet werden

Git fasst benachbarte Änderungen zu einem Konflikt-Hunk zusammen, auch wenn sie sich inhaltlich nicht berühren. Deshalb wird jeder Hunk zuerst zeilengenau betrachtet, bevor die Regeln 10 und 5 greifen:

- **Verschiedene Zeilen:** Ändern die beiden Seiten innerhalb des Hunks verschiedene Zeilen der gemeinsamen Basis, bleiben beide Änderungen erhalten, wie bei einem normalen Merge.
- **Beide fügen an derselben Stelle ein:** Fügen beide Seiten nur neue Zeilen an derselben Stelle ein (z.B. zwei neue Deklarationen, zwei README-Absätze, zwei neue Enum-Werte), hat keine Seite etwas entfernt. Beide Einfügungen bleiben erhalten, die ältere zuerst. Zeilen, die in beiden Einfügungen wörtlich vorkommen (z.B. derselbe Include), stehen nur einmal da. Bei Enum-artigen Listen werden die Kommas angepasst. Ist die ältere Einfügung nur eine frühere Fassung der neueren (mindestens die Hälfte ihrer Zeilen steckt in der neueren), gilt sie als überarbeitet und die neuere gewinnt.
- **Virtuelle Merge-Basis:** Haben integration/all und der Branch mehrere gemeinsame Vorfahren, baut Git eine virtuelle Basis, die selbst Konfliktmarker enthalten kann. Diese Markerzeilen zählen nicht als Basisinhalt. Scheinbare Löschungen, die nur daraus entstehen, werden nicht übernommen.
- **Echte Kollision:** Nur wenn beide Seiten dieselben Basiszeilen ändern, entscheidet Regel 10 und danach Regel 5. Hat eine Seite an einer Stelle gar keine eigene inhaltliche Änderung (die Zeilen stammen nur aus der Basis oder aus Stil-Commits), gewinnt die andere Seite.
- **Nie gesehen:** Würde eine Auflösung Zeilen entfernen, die die gewinnende Seite nie in ihrer Historie hatte, und bräche das offensichtlich etwas (z.B. fehlendes Aufräumen, fehlende Deklaration), bleiben diese Zeilen erhalten. Jeder solche Fall steht einzeln in der Merge-Commit-Message.

Legende Spalte "Probelauf": `B3` = in 3 Hunks gewinnt der Branch, `S2` = in 2 Hunks gewinnt der bisherige Stand von `integration/all`. "entfernt ohne Konflikt" = Git löscht beim Merge Dateien, ohne einen Konflikt zu melden.

## Reihenfolge

### Gruppe 1: Schritte 1 bis 7, Kleine Einzelkorrekturen, Escape-Navigation, Windows-Basis (07.09. früh)

| Nr. | Branch | PR | Sortierdatum und SHA (letzter inhaltlicher Commit) | Spitze des Branches | Grund der Position | Konflikt laut GitHub | Probelauf |
|---|---|---|---|---|---|---|---|
| 1 | `pr/save-request-payload` | #210 | 2026-09-07 00:15 `afa9a7b5` | gleich | direkt auf upstream | nein | kein Konflikt |
| 2 | `pr/quit-dialog-layout` | #211 | 2026-09-07 00:15 `d078dcd3` | gleich | direkt auf upstream | nein | kein Konflikt |
| 3 | `pr/event-message-paths` | #212 | 2026-09-07 00:15 `f44e4927` | gleich | direkt auf upstream | nein | kein Konflikt |
| 4 | `pr/windows-incremental-build` | #213 | 2026-09-07 00:15 `c5cd3fcf` | gleich | direkt auf upstream | nein | kein Konflikt |
| 5 | `pr/escape-navigation` | #214 | 2026-09-07 00:29 `82f4b8c9` | gleich | direkt auf upstream | nein | kein Konflikt |
| 6 | `feature/windows-support` | #204 | 2026-09-07 00:45 `25b82a7a` | gleich | direkt auf upstream | nein | kein Konflikt |
| 7 | `fix/settings-option-duplicates` | #206 | 2026-09-07 00:45 `67a66cf2` | gleich | direkt auf upstream | nein | kein Konflikt |

*Nach Schritt 7: kompilieren (Release) und kurz starten.*

### Gruppe 2: Schritte 8 bis 14, Live-Einstellungen, Skalierung, Schatten und Material, Kamera und Karte (07.09.)

| Nr. | Branch | PR | Sortierdatum und SHA (letzter inhaltlicher Commit) | Spitze des Branches | Grund der Position | Konflikt laut GitHub | Probelauf |
|---|---|---|---|---|---|---|---|
| 8 | `feature/live-settings` | #207 | 2026-09-07 00:46 `e0bf9cc5` (Autor: 2026-09-05 19:51) | gleich | nach Vorgänger #204 | nein | Konflikt in: SettingsWindow.cpp (B1) |
| 9 | `feature/progressive-edge-scrolling` | #208 | 2026-09-07 00:47 `806adbe4` | 2026-09-24 22:34 `bd841779` (Stil-Commit) | direkt auf upstream | nein | kein Konflikt |
| 10 | `feature/gui-scaling` | #209 | 2026-09-07 00:48 `421bb608` | 2026-09-24 22:34 `f39feefa` (Stil-Commit) | nach Vorgänger #207 | nein | kein Konflikt |
| 11 | `fix/dynamic-shadows` | #205 | 2026-09-07 01:11 `88851f8f` (Autor: 2026-09-06 23:59) | gleich | nach Vorgänger #204 | nein | Konflikt in: RenderManager.cpp (B1) |
| 12 | `fix/material-lighting` | #62 | 2026-09-07 01:11 `cb6087f9` | gleich | nach Vorgänger #205; gleiche Sekunde wie #205, #205 ist Vorgänger | nein | kein Konflikt |
| 13 | `feature/camera-controls` | #82 | 2026-09-07 07:36 `2e44fa41` (Autor: 2026-09-07 01:18) | 2026-09-24 22:34 `12411734` (Stil-Commit) | nach Vorgänger #207 | nein | Konflikt in: CameraManager.cpp (B2) |
| 14 | `feature/map-navigation` | #215 | 2026-09-07 07:36 `b96c09e4` (Autor: 2026-09-07 01:35) | 2026-09-24 22:34 `458ab17c` (Stil-Commit) | nach Vorgänger #207 | nein | Konflikt in: GameMode.cpp (B1) |

*Nach Schritt 14: kompilieren (Release) und kurz starten.*

### Gruppe 3: Schritte 15 bis 23, Anzeige-Korrekturen, Raumlicht, Einstellungen, Porträt-Export, Tooltips, Branding (07./08.09.)

| Nr. | Branch | PR | Sortierdatum und SHA (letzter inhaltlicher Commit) | Spitze des Branches | Grund der Position | Konflikt laut GitHub | Probelauf |
|---|---|---|---|---|---|---|---|
| 15 | `pr/initial-creature-overlay-visibility` | #216 | 2026-09-07 23:27 `41e45c79` (Autor: 2026-09-07 21:45) | gleich | direkt auf upstream | nein | kein Konflikt |
| 16 | `feature/room-lighting` | #81 | 2026-09-07 23:31 `18252fd4` (Autor: 2026-09-07 10:27) | gleich | nach Vorgänger #62 | nein | kein Konflikt |
| 17 | `pr/screenshots-all-screens` | #217 | 2026-09-07 23:39 `0e35eb89` (Autor: 2026-09-07 11:26) | gleich | direkt auf upstream | nein | Konflikt in: AbstractApplicationMode.h (B1) |
| 18 | `pr/settings-content-scrolling-complete` | #219 | 2026-09-08 07:51 `03a94e34` | 2026-09-24 22:34 `dc958280` (Stil-Commit) | nach Vorgänger #207 | nein | Konflikt in: CameraManager.cpp (S2) |
| 19 | `pr/creature-portrait-export-complete` | #220 | 2026-09-08 07:51 `f850a8ad` | 2026-09-24 22:33 `31a86b6f` (Stil-Commit) | nach Vorgänger #204 | nein | Konflikt in: README.md (B1) |
| 20 | `pr/tooltip-screen-bounds-complete` | #221 | 2026-09-08 07:51 `366e546e` | gleich | direkt auf upstream | nein | Konflikt in: Gui.cpp (B1) |
| 21 | `pr/startup-pointer-complete` | #222 | 2026-09-08 08:18 `5d899f0d` | gleich | nach Vorgänger #207 | nein | kein Konflikt |
| 22 | `pr/dungeon-ground-underlay-complete` | #223 | 2026-09-08 08:19 `af6231a4` | gleich | direkt auf upstream | nein | kein Konflikt |
| 23 | `pr/application-branding-complete` | #224 | 2026-09-08 08:19 `776fc208` | gleich | nach Vorgänger #204 | nein | kein Konflikt |

*Nach Schritt 23: kompilieren (Release) und kurz starten.*

### Gruppe 4: Schritte 24 bis 30, Kreatur-Auswahl, Menü-Navigation und -Hintergrund, Werkstatt, Fallen, Gelände (08.09.)

| Nr. | Branch | PR | Sortierdatum und SHA (letzter inhaltlicher Commit) | Spitze des Branches | Grund der Position | Konflikt laut GitHub | Probelauf |
|---|---|---|---|---|---|---|---|
| 24 | `pr/creature-population-complete` | #225 | 2026-09-08 08:48 `be121d01` | 2026-09-24 22:33 `fdc2b79f` (Stil-Commit) | nach Vorgänger #207 | nein | Konflikt in: CameraManager.cpp (S2), GameMode.h (B1) |
| 25 | `pr/world-target-selection-complete` | #229 | 2026-09-08 09:20 `8c8770a6` | 2026-09-24 22:32 `3fe522a4` (Stil-Commit) | nach Vorgänger #207 | nein | Konflikt in: CameraManager.cpp (S2), GameMode.cpp (B1), RenderManager.cpp (B1) |
| 26 | `pr/menu-navigation-complete` | #230 | 2026-09-08 10:01 `a6f1f916` | 2026-09-24 22:31 `61dce71b` (Stil-Commit) | nach Vorgänger #207, #224, #214, #221 | ja | Konflikt in: OD.looknfeel (S1), GameMode.cpp (B3), GameMode.h (B1), Gui.cpp (B2) |
| 27 | `pr/static-menu-background-complete` | #231 | 2026-09-08 10:01 `b04544ed` | 2026-09-24 22:31 `2d3e2523` (Stil-Commit) | nach Vorgänger #207, #224, #214, #221 | ja | kein Konflikt |
| 28 | `pr/workshop-production-order-v2` | #154 | 2026-09-08 16:50 `4d5bb2d4` | 2026-09-24 22:31 `d8337f9f` (Stil-Commit) | nach Vorgänger #207, #224, #214, #221 | ja | kein Konflikt |
| 29 | `pr/trap-placement-costs-v2` | #155 | 2026-09-08 16:54 `ff39d095` | 2026-09-24 22:30 `bded72b1` (Stil-Commit) | nach Vorgänger #207, #224, #214, #221 | ja | kein Konflikt |
| 30 | `pr/terrain-context-v2` | #156 | 2026-09-08 16:55 `2441c3a7` | 2026-09-24 22:30 `3d3ad8a7` (Stil-Commit) | nach Vorgänger #207, #224, #214, #221 | ja | kein Konflikt |

*Nach Schritt 30: kompilieren (Release) und kurz starten.*

### Gruppe 5: Schritte 31 bis 35, Werkstatt-Aktionen, Kosten-Tooltips, Kontexthilfe, Hand-Tooltip, Räume durchschalten (08.09.)

| Nr. | Branch | PR | Sortierdatum und SHA (letzter inhaltlicher Commit) | Spitze des Branches | Grund der Position | Konflikt laut GitHub | Probelauf |
|---|---|---|---|---|---|---|---|
| 31 | `pr/workshop-action-order-v2` | #157 | 2026-09-08 16:55 `ef8c015d` | 2026-09-24 22:29 `2a6ff8a8` (Stil-Commit) | nach Vorgänger #207, #224, #214, #221 | ja | kein Konflikt |
| 32 | `pr/action-cost-tooltips-v2` | #158 | 2026-09-08 16:55 `3c2b4a50` | 2026-09-24 22:29 `043f95f6` (Stil-Commit) | nach Vorgänger #207, #224, #214, #221 | ja | kein Konflikt |
| 33 | `pr/context-help-duplication-v2` | #159 | 2026-09-08 16:57 `ddde394a` | 2026-09-24 22:28 `25bcdbc7` (Stil-Commit) | nach Vorgänger #207, #224, #214, #221 | ja | Konflikt in: CreaturePanel.cpp (B1) |
| 34 | `pr/tooltip-hand-alignment-v2` | #160 | 2026-09-08 17:02 `9683a8ce` | 2026-09-24 22:28 `b3d67d69` (Stil-Commit) | nach Vorgänger #207, #224, #214, #221 | ja | kein Konflikt |
| 35 | `pr/room-navigation-cycling` | #161 | 2026-09-08 22:03 `3ef9716e` | 2026-09-24 22:27 `15720918` (Stil-Commit) | nach Vorgänger #207 | nein | Konflikt in: SkillManager.cpp (B1), GameMode.cpp (B1), GameMode.h (B1) |

*Nach Schritt 35: kompilieren (Release) und kurz starten.*

### Gruppe 6: Schritte 36 bis 43, Paket vom 19.09. Nachmittag: Server, Projektile, Release-Build, Menü-Cursor und -Atmosphäre, Besitz-Markierungen, Raumbau

| Nr. | Branch | PR | Sortierdatum und SHA (letzter inhaltlicher Commit) | Spitze des Branches | Grund der Position | Konflikt laut GitHub | Probelauf |
|---|---|---|---|---|---|---|---|
| 36 | `pr/server-shutdown-2026-09` | #163 | 2026-09-19 15:56 `76ca6a12` | gleich | direkt auf upstream | nein | kein Konflikt |
| 37 | `pr/projectile-collision-2026-09` | #164 | 2026-09-19 15:56 `96c505e7` | gleich | direkt auf upstream | nein | kein Konflikt |
| 38 | `pr/release-optimization-2026-09` | #165 | 2026-09-19 15:56 `8bb78d95` | gleich | nach Vorgänger #213 | nein | kein Konflikt |
| 39 | `pr/resource-regeneration-2026-09` | #166 | 2026-09-19 15:56 `6e49e65e` | gleich | nach Vorgänger #205 | nein | kein Konflikt |
| 40 | `pr/menu-cursor-2026-09` | #167 | 2026-09-19 15:56 `1eefc0d3` (Merge-Commit: 2026-09-19 16:21 `450a5d4b`) | 2026-09-24 22:27 `c9cd9fe2` (Stil-Commit) | nach Vorgänger #207, #224, #214, #221 | nein | Konflikt in: OD.looknfeel (B1), CreaturePanel.cpp (S1) |
| 41 | `pr/menu-atmosphere-2026-09` | #168 | 2026-09-19 15:56 `07ad8b70` (Merge-Commit: 2026-09-19 16:21 `3bf855c0`) | 2026-09-24 22:26 `f760c7b0` (Stil-Commit) | nach Vorgänger #207, #224, #214, #221 | nein | Konflikt in: CreaturePanel.cpp (S1) |
| 42 | `pr/ownership-markers-2026-09` | #169 | 2026-09-19 15:56 `e3bad799` | gleich | nach Vorgänger #81 | nein | kein Konflikt |
| 43 | `pr/room-construction-2026-09` | #170 | 2026-09-19 15:56 `0a420b5e` | 2026-09-24 22:26 `e47b8fe1` (Stil-Commit) | nach Vorgänger #207 | nein | Konflikt in: CameraManager.cpp (S2), CreaturePanel.cpp (S1) |

*Nach Schritt 43: kompilieren (Release) und kurz starten.*

### Gruppe 7: Schritte 44 bis 51, Hand-Ablage, Produktion, Fenster, Kampf-, Schlaf- und Fressanimationen, Raum-Objekt-Navigation (19.09.)

| Nr. | Branch | PR | Sortierdatum und SHA (letzter inhaltlicher Commit) | Spitze des Branches | Grund der Position | Konflikt laut GitHub | Probelauf |
|---|---|---|---|---|---|---|---|
| 44 | `pr/hand-drop-2026-09` | #171 | 2026-09-19 16:03 `6c2ec116` (Merge-Commit: 2026-09-19 16:21 `9b8b7691`) | 2026-09-24 22:26 `e0327b38` (Stil-Commit) | nach Vorgänger #207, #224, #214, #221 | nein | Konflikt in: GameMode.h (B1), RenderManager.cpp (B4), RenderManager.h (B1) |
| 45 | `pr/production-queue-2026-09` | #172 | 2026-09-19 16:03 `3a040630` (Merge-Commit: 2026-09-19 16:21 `5d7c2104`) | 2026-09-24 22:25 `a9130e3e` (Stil-Commit) | nach Vorgänger #207, #224, #214, #221 | nein | Konflikt in: README.md (B1), ClientNotification.cpp (B1), ClientNotification.h (B1), ServerNotification.cpp (B1), ServerNotification.h (B1) |
| 46 | `pr/exclusive-windows-2026-09` | #175 | 2026-09-19 16:16 `0c2f08e9` (Merge-Commit: 2026-09-19 16:21 `97d86233`) | 2026-09-24 22:24 `b89a157c` (Stil-Commit) | nach Vorgänger #207, #224, #214, #221 | nein | kein Konflikt |
| 47 | `pr/creature-combat-2026-09` | #176 | 2026-09-19 21:31 `80c42b2e` | 2026-09-24 22:23 `9ac12841` (Stil-Commit) | nach Vorgänger #207, #224, #214, #164, #221 | nein | Konflikt in: README.md (B1), ServerNotification.cpp (B1), ServerNotification.h (B1), RenderManager.cpp (B7), RenderManager.h (B2) |
| 48 | `pr/sleep-animations-2026-09` | #178 | 2026-09-19 21:34 `834183a6` | 2026-09-24 22:23 `717bfcb6` (Stil-Commit) | nach Vorgänger #207, #224, #214, #164, #221 | nein | Konflikt in: RenderManager.cpp (B1) |
| 49 | `pr/room-object-navigation-2026-09` | #179 | 2026-09-19 21:36 `8c48b90f` | 2026-09-24 23:28 `00c0d2cc` (Stil-Commit) | nach Vorgänger #207, #224, #214, #164, #221 | nein | Konflikt in: ClientNotification.cpp (S1), ServerNotification.cpp (B1), ServerNotification.h (S1), RenderManager.cpp (B1) |
| 50 | `pr/dormitory-floor-2026-09` | #180 | 2026-09-19 21:37 `5afa9d0b` | 2026-09-24 23:29 `5f22e9d4` (Stil-Commit) | nach Vorgänger #207, #224, #214, #164, #221 | nein | kein Konflikt |
| 51 | `pr/feeding-animations-2026-09` | #177 | 2026-09-19 21:46 `58439c8a` | 2026-09-24 22:23 `2be95185` (Stil-Commit) | nach Vorgänger #207, #224, #214, #164, #221 | nein | kein Konflikt |

*Nach Schritt 51: kompilieren (Release) und kurz starten.*

### Gruppe 8: Schritte 52 bis 59, Kontext-Hand, Leerlauf-Hand, HUD, Nachrichten, Forschung, Bauvorschau, Korridore (20./21.09.)

| Nr. | Branch | PR | Sortierdatum und SHA (letzter inhaltlicher Commit) | Spitze des Branches | Grund der Position | Konflikt laut GitHub | Probelauf |
|---|---|---|---|---|---|---|---|
| 52 | `pr/contextual-action-hand-complete` | #226 | 2026-09-20 11:11 `6c1902e0` | 2026-09-24 22:33 `a104077c` (Stil-Commit) | nach Vorgänger #207 | nein | Konflikt in: CameraManager.cpp (S2), CreaturePanel.cpp (S1), RenderManager.cpp (B1) |
| 53 | `pr/idle-hand-2026-09` | #182 | 2026-09-20 11:33 `a9170951` | 2026-09-24 23:30 `828749df` (Stil-Commit) | nach Vorgänger #207, #224, #214, #164, #221 | nein | Konflikt in: RenderManager.cpp (B1); 1 Hunk(s) per Datei-Datum |
| 54 | `pr/gameplay-hud-navigation-complete` | #227 | 2026-09-21 10:27 `30423685` (Merge-Commit: 2026-09-21 11:35 `66e77b97`) | 2026-09-24 22:33 `22b35c9c` (Stil-Commit) | nach Vorgänger #207 | nein | Konflikt in: OD.looknfeel (S1), CreaturePanel.cpp (S1) |
| 55 | `pr/incoming-notification-queue-complete` | #228 | 2026-09-21 10:29 `868d0ca0` (Merge-Commit: 2026-09-21 11:37 `bc331529`) | 2026-09-24 22:32 `e7f1f8f7` (Stil-Commit) | nach Vorgänger #207 | nein | Konflikt in: OD.looknfeel (S2), GameMode.cpp (B1), CreaturePanel.cpp (S1) |
| 56 | `pr/research-progression-2026-09` | #174 | 2026-09-21 10:40 `652250d6` | 2026-09-24 22:25 `0028bdd4` (Stil-Commit) | nach Vorgänger #207, #224, #214, #221 | nein | kein Konflikt |
| 57 | `pr/construction-preview-border-2026-09-21` | #183 | 2026-09-21 10:42 `98bdadb0` | 2026-09-24 23:31 `7139c6bf` (Stil-Commit) | nach Vorgänger #207, #224, #214, #164, #221 | nein | kein Konflikt |
| 58 | `pr/diagonal-corridor-navigation-2026-09-21` | #186 | 2026-09-21 10:42 `0609ba49` | 2026-09-24 23:34 `1a0dae41` (Stil-Commit) | nach Vorgänger #207, #224, #214, #164, #221 | nein | kein Konflikt |
| 59 | `pr/room-interaction-spacing-2026-09-21` | #187 | 2026-09-21 10:42 `08a8b647` | 2026-09-24 23:34 `f585217f` (Stil-Commit) | nach Vorgänger #207, #224, #214, #164, #221 | nein | Konflikt in: RoomObjectNavigation.cpp (B2) |

*Nach Schritt 59: kompilieren (Release) und kurz starten.*

### Gruppe 9: Schritte 60 bis 68, Abriss, Grab-Auswahl, Farben, Kreatur-Stufen, Arbeiter-Symbol, Gruft (21.09.)

| Nr. | Branch | PR | Sortierdatum und SHA (letzter inhaltlicher Commit) | Spitze des Branches | Grund der Position | Konflikt laut GitHub | Probelauf |
|---|---|---|---|---|---|---|---|
| 60 | `pr/room-demolition-selection-2026-09-21` | #191 | 2026-09-21 10:50 `f0fdf86d` | 2026-09-24 23:37 `d4953d05` (Stil-Commit) | nach Vorgänger #207, #224, #214, #164, #221 | nein | Konflikt in: RoomObjectNavigation.cpp (S2) |
| 61 | `pr/digging-selection-border-2026-09-21` | #190 | 2026-09-21 10:50 `d9fb1920` | 2026-09-24 23:36 `379730b6` (Stil-Commit) | nach Vorgänger #207, #224, #214, #164, #221 | nein | Konflikt in: RoomObjectNavigation.cpp (S2), GameMode.cpp (B3) |
| 62 | `pr/room-demolition-effect-2026-09-21` | #192 | 2026-09-21 10:50 `b174a211` | 2026-09-24 23:38 `a0cd1cb3` (Stil-Commit) | nach Vorgänger #207, #224, #214, #164, #221 | nein | Konflikt in: RoomObjectNavigation.cpp (S2) |
| 63 | `pr/dungeon-colours-2026-09` | #173 | 2026-09-21 11:07 `c441f638` | 2026-09-24 23:27 `4bdee896` (Stil-Commit) | nach Vorgänger #207, #169 | nein | Konflikt in: README.md (S1), OD.looknfeel (B1/S1), GameMode.cpp (B1/S4), CreaturePanel.cpp (S1); 1 Hunk(s) per Datei-Datum |
| 64 | `pr/creature-level-progression-2026-09-21` | #184 | 2026-09-21 11:09 `507b2c08` | 2026-09-24 23:32 `fbfa9370` (Stil-Commit) | nach Vorgänger #207, #224, #214, #164, #221 | nein | Konflikt in: README.md (B1), RoomObjectNavigation.cpp (S2); 1 Hunk(s) per Datei-Datum |
| 65 | `pr/summon-worker-icon-2026-09-21` | #188 | 2026-09-21 11:11 `c75abc52` | 2026-09-24 23:35 `94690e77` (Stil-Commit) | nach Vorgänger #207, #169 | nein | Konflikt in: CreaturePanel.cpp (S1) |
| 66 | `pr/windows-key-background-2026-09-21` | #189 | 2026-09-21 11:13 `f818b3eb` | 2026-09-24 23:36 `7515f985` (Stil-Commit) | nach Vorgänger #207, #224, #214, #164, #221 | nein | Konflikt in: RoomObjectNavigation.cpp (S2), AbstractApplicationMode.cpp (B3), AbstractApplicationMode.h (B1), EditorMode.cpp (B1) |
| 67 | `pr/crypt-corpse-decay-2026-09-21` | #185 | 2026-09-21 11:15 `2e8035b9` | 2026-09-24 23:33 `84a0765a` (Stil-Commit) | nach Vorgänger #207, #224, #214, #164, #221 | nein | Konflikt in: RoomObjectNavigation.cpp (S2) |
| 68 | `pr/crypt-worker-departure-2026-09-21` | #193 | 2026-09-21 11:15 `4fcdf4d8` | 2026-09-24 23:39 `c3c74c55` (Stil-Commit) | nach Vorgänger #207, #224, #214, #164, #221 | nein | Konflikt in: RoomObjectNavigation.cpp (S2) |

*Nach Schritt 68: kompilieren (Release) und kurz starten.*

### Gruppe 10: Schritte 69 bis 76, Spielstand-Browser (Sonderfall, siehe unten), Herz-Duplikat, Bauhammer, Herz-Kampf, Gesundheit, Einzelkorrekturen, auto-Refactor (21. bis 25.09.)

| Nr. | Branch | PR | Sortierdatum und SHA (letzter inhaltlicher Commit) | Spitze des Branches | Grund der Position | Konflikt laut GitHub | Probelauf |
|---|---|---|---|---|---|---|---|
| 69 | `pr/saved-game-browser-complete` | #218 | 2026-09-21 11:21 `c28f93de` (Merge-Commit: 2026-09-21 11:32 `0d56889e`) | 2026-09-21 11:32 `0d56889e` (Merge current upstream base) | nach Vorgänger #207, #224, #214, #221 | nein | Konflikt in: CMakeLists.txt (B1), MenuMain.layout (B1), ModeGame.layout (B1), OD.looknfeel (B3), ODSkin.scheme (B1), WindowGameOptions.layout (B2), WindowSkillTree.layout (B4), WindowTabRooms.layout (S2), WindowTabSpells.layout (S10), HandTool.material (B1), CameraManager.cpp (B2), Creature.cpp (S4), Creature.h (S2), CreaturePanelData.cpp (B1), SkillManager.cpp (B1), SkillManager.h (B1), MiniMap.cpp (B1), MiniMapDrawnFull.cpp (B1), GameMode.cpp (B32/S2), GameMode.h (B4), InputManager.cpp (B1), Keyboard.cpp (B1), SettingsWindow.cpp (B2), ClientNotification.cpp (B1), ClientNotification.h (B1), ODClient.cpp (B4), ODServer.cpp (B5), ODServer.h (B1), ODSocketClient.cpp (B1), ODSocketClient.h (B3), ServerNotification.cpp (B1), ServerNotification.h (B1), CreaturePanel.cpp (B1), CreaturePortrait.cpp (B1), Gui.cpp (B4), RenderManager.cpp (B9), RenderManager.h (B2), RenderSceneMenu.cpp (B1/S2), TrapDoor.cpp (B3), TrapManager.cpp (B2), ConfigManager.cpp (B1), ConfigManager.h (B1), portrait-export.cpp (B1); Datei gelöscht/geändert: 5 Fall/Fälle; **entfernt ohne Konflikt 102 Datei(en)**; 6 Hunk(s) per Datei-Datum |
| 70 | `pr/heart-duplication-2026-09-22` | #142 | 2026-09-22 12:16 `6d3a557f` | gleich | direkt auf upstream | nein | kein Konflikt |
| 71 | `pr/construction-hammer-2026-09` | #181 | 2026-09-22 12:16 `b7df5011` | 2026-09-24 23:30 `e4c2cea4` (Stil-Commit) | nach Vorgänger #207, #224, #214, #164, #221 | nein | Konflikt in: CameraManager.cpp (S2), CreaturePanelData.cpp (S1), MiniMap.cpp (S1), MiniMapDrawnFull.cpp (S1), RoomObjectNavigation.cpp (S2), GameMode.cpp (S4), Keyboard.cpp (S1), SettingsWindow.cpp (S2), CreaturePanel.cpp (S1), CreaturePortrait.cpp (S1), Gui.cpp (S3), RenderManager.cpp (S1), portrait-export.cpp (S1); Datei gelöscht/geändert: 4 Fall/Fälle |
| 72 | `pr/dungeon-heart-combat-2026-09-22` | #143 | 2026-09-22 12:17 `76743002` | 2026-09-24 23:40 `571eb806` (Stil-Commit) | nach Vorgänger #207, #224, #214, #142, #164, #221 | nein | Konflikt in: CameraManager.cpp (S2), CreaturePanelData.cpp (S1), MiniMap.cpp (S1), MiniMapDrawnFull.cpp (S1), RoomObjectNavigation.cpp (S2), GameMode.cpp (S5), Keyboard.cpp (S1), SettingsWindow.cpp (S2), CreaturePanel.cpp (S1), CreaturePortrait.cpp (S1), Gui.cpp (S3), RenderManager.cpp (S2), RoomManager.cpp (B2), portrait-export.cpp (S1); Datei gelöscht/geändert: 4 Fall/Fälle |
| 73 | `pr/creature-health-and-needs` | #162 | 2026-09-24 21:35 `83f2825c` | 2026-09-24 22:27 `2e64328d` (Stil-Commit) | nach Vorgänger #207 | nein | Konflikt in: Enter-OpenDungeonsPlus.ps1 (B1), configure-windows-prereqs.ps1 (B1), install-base-prereqs.ps1 (B1), install-boost-prereq.ps1 (B1), install-cegui-prereq.ps1 (B1), install-ogre-prereq.ps1 (B1), prepare-windows-runtime.ps1 (B1), CameraManager.cpp (S1), CreaturePanelData.cpp (S1), Keyboard.cpp (S1), CreaturePanel.cpp (S1), CreaturePortrait.cpp (S1), Gui.cpp (S2), portrait-export.cpp (S1); Datei gelöscht/geändert: 11 Fall/Fälle |
| 74 | `fix/middle-click-stats-window` | #194 | 2026-09-24 23:48 `b17ab65c` | gleich | direkt auf upstream | nein | Konflikt in: GameMode.cpp (B1) |
| 75 | `fix/actionable-keeper-messages` | #195 | 2026-09-24 23:58 `a3ac802a` | gleich | direkt auf upstream | nein | kein Konflikt |
| 76 | `refactor/explicit-types-upstream` | #196 | 2026-09-25 08:03 `edc9beff` | gleich | direkt auf upstream | nein | Konflikt in: Seat.cpp (S1) |

*Nach Schritt 76: kompilieren (Release) und kurz starten.*

### Gruppe 11: Schritte 77 bis 83, Niederlage-Sequenz und Herz-Kette H1 bis H6 (26./27.09.)

| Nr. | Branch | PR | Sortierdatum und SHA (letzter inhaltlicher Commit) | Spitze des Branches | Grund der Position | Konflikt laut GitHub | Probelauf |
|---|---|---|---|---|---|---|---|
| 77 | `pr/defeat-sequence-2026-09-25` | #197 | 2026-09-26 09:10 `bc819c9d` | gleich | nach Vorgänger #143 | nein | Konflikt in: GameMode.cpp (B5), GameMode.h (B1), MenuModeMain.cpp (B1), MenuModeMain.h (B1), ODClient.cpp (B1), ODSocketClient.h (B1), ServerNotification.cpp (B1), ServerNotification.h (B1), Gui.cpp (B2), Gui.h (B1), RenderManager.h (B1), RenderSceneMenu.h (B1); 1 Hunk(s) per Datei-Datum |
| 78 | `pr/dungeon-heart-h1` | #198 | 2026-09-27 16:43 `0dbe8cc3` (Autor: 2026-09-26 10:37) | gleich | nach Vorgänger #197 | nein | kein Konflikt |
| 79 | `pr/dungeon-heart-h2` | #199 | 2026-09-27 17:06 `c4b76c6f` (Autor: 2026-09-26 11:31) | gleich | nach Vorgänger #198 | nein | Konflikt in: ModeGame.layout (B3), OD.looknfeel (B2), GameMode.cpp (B2), GameMode.h (B1) |
| 80 | `pr/dungeon-heart-h3` | #200 | 2026-09-27 17:06 `6a0cff96` (Autor: 2026-09-26 17:09) | gleich | nach Vorgänger #199 | nein | kein Konflikt |
| 81 | `pr/dungeon-heart-h4` | #201 | 2026-09-27 17:06 `c7362f1f` (Autor: 2026-09-26 21:11) | gleich | nach Vorgänger #200 | nein | kein Konflikt |
| 82 | `pr/dungeon-heart-h5` | #202 | 2026-09-27 17:06 `15d6da86` (Autor: 2026-09-26 23:13) | gleich | nach Vorgänger #201 | nein | kein Konflikt |
| 83 | `pr/dungeon-heart-h6` | #203 | 2026-09-27 17:06 `3b009896` (Autor: 2026-09-27 10:59) | gleich | nach Vorgänger #202 | nein | kein Konflikt |

*Nach Schritt 83: kompilieren (Release) und kurz starten.*

## Sonderfall #218 (`pr/saved-game-browser-complete`, Schritt 69)

Die Historie von #218 enthält zuerst viele Commits anderer Features und danach den Commit `c28f93de` "Remove unrelated menu prerequisite from loading contribution" (21.09. 11:21). Dieser Commit entfernt diese Features wieder aus dem Branch, damit der PR nur den Spielstand-Browser zeigt. Nur #218 enthält diesen Commit. Sein Baum enthält deshalb auch Dateien seiner eigenen Git-Vorgänger nicht mehr (`feature/windows-support`, `feature/live-settings`, `pr/application-branding-complete`).

Folgen im Probelauf (dort noch nach Regel 5 als gewollte spätere Entscheidung behandelt; überholt durch die Entscheidung unten):

- Schritt 69 hat Konflikte in 43 Dateien (105 Hunks gewinnt #218, 22 der bisherige Stand).
- Zusätzlich entfernt Git beim Merge **ohne Konfliktmeldung 102 Dateien**: `materials/portraits` (33), `materials/textures` (33), `scripts/win32` (11), `source/render` (4), `gui/fonts` (2), `source/game` (2), `tools/portraits` (2), `dist/opendungeons.manifest` (1), `gui/ODHudSurface.imageset` (1), `gui/ODHudSurface.png` (1), `gui/ODMainMenuLogo.imageset` (1), `gui/ODMainMenuLogo.png` (1), `gui/WindowGameEvent.layout` (1), `gui/WindowMap.layout` (1), `gui/WindowSettingsNavigation.layout` (1), `gui/WindowSettingsSubMenu.layout` (1), `gui/WindowUserCameras.layout` (1), `materials/scripts` (1), `meta/gui` (1), `source/camera` (1), `source/entities` (1), `source/modes` (1).
  Darunter: `dist/opendungeons.manifest`, `gui/ODHudSurface.imageset`, `gui/ODHudSurface.png`, `gui/ODMainMenuLogo.imageset`, `gui/ODMainMenuLogo.png`, `gui/WindowGameEvent.layout`, `gui/WindowMap.layout`, `gui/WindowSettingsNavigation.layout`, `gui/WindowSettingsSubMenu.layout`, `gui/WindowUserCameras.layout`, `gui/fonts/MedievalSharp-20.font`, `gui/fonts/MedievalSharp-8.font`, `meta/gui/application-icon.png`, `scripts/win32/Enter-OpenDungeonsPlus.ps1`, `scripts/win32/configure-windows-prereqs.ps1`, `scripts/win32/export-creature-portraits.ps1`, `scripts/win32/install-base-prereqs.ps1`, `scripts/win32/install-boost-prereq.ps1`, `scripts/win32/install-cegui-prereq.ps1`, `scripts/win32/install-ogre-prereq.ps1`, `scripts/win32/patches/cegui-msvc-snprintf.patch`, `scripts/win32/patches/cegui-ogre-clipping.patch`, `scripts/win32/patches/ogre-multiwindow-settings.patch`, `scripts/win32/prepare-windows-runtime.ps1`, `source/camera/CameraInput.h`, `source/entities/CreatureActivity.h`, `source/game/CreaturePanelData.cpp`, `source/game/CreaturePanelData.h`, `source/modes/InputCommand.cpp`, `source/render/CreaturePanel.cpp`, `source/render/CreaturePanel.h`, `source/render/CreaturePortrait.cpp`, `source/render/CreaturePortrait.h`, `tools/portraits/README.md`, `tools/portraits/portrait-export.cpp`.
- Datei gelöscht/geändert in Schritt 69: materials/scripts/HandTool.material: gelöscht (Branch löscht später); source/game/CreaturePanelData.cpp: gelöscht (Branch löscht später); source/render/CreaturePanel.cpp: gelöscht (Branch löscht später); source/render/CreaturePortrait.cpp: gelöscht (Branch löscht später); tools/portraits/portrait-export.cpp: gelöscht (Branch löscht später).
- Damit sind Kreatur-Panel, Kreatur-Porträts samt Export-Werkzeug, Kamera-Eingabe (`CameraInput.h`) und Kreatur-Aktivität (`CreatureActivity.h`) vollständig entfernt: die `.cpp`-Dateien nach Regel 5, die Header ohne Konflikt. Im simulierten Endstand verweist kein Code mehr darauf; ob er kompiliert, zeigt erst der echte Build.
- Im simulierten Endstand fehlen gegenüber der Herz-Spitze H6 unter anderem: `dist/opendungeons.manifest`, `scripts/win32/export-creature-portraits.ps1`, die drei Abhängigkeits-Patches unter `scripts/win32/patches/` (von den Windows-Installationsskripten benutzt), `gui/ODMainMenuLogo.png`, `gui/ODHudSurface.png`, `meta/gui/application-icon.png`, die Fenster `WindowMap.layout`, `WindowUserCameras.layout`, `WindowSettingsNavigation.layout`, `WindowSettingsSubMenu.layout`, `WindowGameEvent.layout` sowie 33 Porträt-Beschreibungen und 33 Texturen.
- Branches, die nach dem 21.09. entstanden sind und diese Dateien noch enthalten, bringen sie beim Merge **nicht** zurück, weil Git die Entfernung als die neuere Änderung sieht. Nach dem jeweiligen Merge fehlen in `integration/all` Dateien, die im Branch vorhanden sind: #181: 102, #143: 102, #162: 80, #197: 95, #198: 95, #199: 95, #200: 95, #201: 95, #202: 95, #203: 95.
- Schritt 73 (#162, 24.09.) holt 7 der 11 Windows-Skripte zurück, weil #162 sie nach dem 21.09. noch geändert hat (Regel "jüngere Aktion gewinnt"). In den Schritten 71, 72 und 73 gewinnt dagegen bei den Kreatur-Panel-Dateien die Löschung aus Schritt 69.

Einordnung: Der Betreff von `c28f93de` beschreibt ein Aufräumen des PR-Inhalts, keine Entscheidung gegen die Features. Die Branches #181, #143, #162, #197 und H1 bis H6 sind später entstanden und enthalten die Dateien noch. Das widerspricht der Annahme "linear vom letzten Stand".

### Entscheidung (Mario, vor dem echten Aufbau)

`c28f93de` ist nur ein Zuschnitt des PRs und keine inhaltliche Entscheidung. **Seine Löschungen werden nicht übernommen** (Regel 9). Die Dateien, die er entfernt oder auf den upstream-Stand zurücksetzt (u.a. `dist/opendungeons.manifest`, `scripts/win32/patches/*`, `export-creature-portraits.ps1`, `tools/portraits/*`, `CreaturePanel.cpp/.h`, Logo, HUD-Oberfläche, Icon, Karten- und Kamera-Fenster, Porträt-Beschreibungen und -Texturen), bleiben in dem Stand, den die übrigen gemergten Branches haben. Alles andere aus #218 wird normal übernommen.

Umsetzung: #218 hat genau drei eigene Commits: `a998e37f` "Restore saved games through a readable in-game browser" (der Spielstand-Browser, 2 Dateien: `source/modes/MenuModeLoad.cpp`, `source/tests/check_load_menu_readability.py`), danach `c28f93de` (Zuschnitt) und `0d56889e` (holt nur upstream `21320e9d` herein, das `integration/all` schon enthält). `a998e37f` sitzt direkt auf `a6f1f916` (Spitze von #230, Schritt 26, also schon in `integration/all`). Ohne den Zuschnitt bringt #218 deshalb nur die Änderung aus `a998e37f` mit. Der Merge-Commit von Schritt 69 hat die echte Spitze von #218 als zweiten Elternteil, sein Inhalt ist aber: Stand vor dem Merge plus `a998e37f`. Details stehen in der Message des Merge-Commits.

Weitere Zuschnitt-Commits dieser Art gibt es in den 83 Branches nicht (geprüft über Betreff und über alle Commits und Merge-Commits, die Dateien löschen oder überwiegend Zeilen entfernen).

Die Sortierposition von #218 (Schritt 69) bleibt wie freigegeben, obwohl ohne `c28f93de` der letzte inhaltliche Commit `a998e37f` (21.09. 10:58) wäre. Da #218 dann nur vier Zeilen in `MenuModeLoad.cpp` und ein neues Testskript mitbringt, ändert die Position am Ergebnis nur dann etwas, wenn ein Branch zwischen Schritt 62 und 69 dieselben Zeilen ändert; das zeigt der Merge.

## Stil-Commits, die für Datum und Blame nicht zählen

Gefunden über den Betreff "spell out variable types instead of auto". 50 Commits; der Commit `571eb806` steckt in 8 Branches (#143 und die Herz-Kette), alle anderen in genau einem. Geprüft am Diff: Jede geänderte Zeile ersetzt nur `auto` durch einen ausgeschriebenen Typ. Zusätzlich gibt es nur diese Abweichungen, alle als Folge des Ersatzes:

- `#include <functional>` in den Dateien, in denen Lambdas jetzt als `std::function<...>` typisiert sind.
- In `source/game/SkillManager.cpp` (16 Commits): Die Lambda `value` hatte ein Default-Argument und ist jetzt `std::function<std::string(double)>`. Der eine Aufruf mit zweitem Argument wurde deshalb ausgeschrieben (`Helper::toString(getResearchValue(type, level, ..., true))`). Gleiches Verhalten.
- `edc9beff` (#196, 25.09.) ergänzt in `EventHandler.cpp` ein `typedef` für den ausgeschriebenen Iterator-Typ. #196 besteht nur aus diesem Commit; für die Sortierung von #196 zählt deshalb sein eigenes Datum.

| SHA | Datum | Branch(es) | Dateien | geänderte Zeilen |
|---|---|---|---|---|
| `717bfcb6` | 2026-09-24 22:23 | #178 | 13 | 106 |
| `2be95185` | 2026-09-24 22:23 | #177 | 13 | 99 |
| `9ac12841` | 2026-09-24 22:23 | #176 | 13 | 78 |
| `b89a157c` | 2026-09-24 22:24 | #175 | 14 | 65 |
| `0028bdd4` | 2026-09-24 22:25 | #174 | 16 | 85 |
| `a9130e3e` | 2026-09-24 22:25 | #172 | 14 | 65 |
| `e0327b38` | 2026-09-24 22:26 | #171 | 13 | 71 |
| `e47b8fe1` | 2026-09-24 22:26 | #170 | 9 | 42 |
| `f760c7b0` | 2026-09-24 22:26 | #168 | 14 | 60 |
| `c9cd9fe2` | 2026-09-24 22:27 | #167 | 13 | 59 |
| `2e64328d` | 2026-09-24 22:27 | #162 | 10 | 50 |
| `15720918` | 2026-09-24 22:27 | #161 | 6 | 12 |
| `b3d67d69` | 2026-09-24 22:28 | #160 | 13 | 63 |
| `25bcdbc7` | 2026-09-24 22:28 | #159 | 13 | 60 |
| `043f95f6` | 2026-09-24 22:29 | #158 | 13 | 59 |
| `2a6ff8a8` | 2026-09-24 22:29 | #157 | 13 | 59 |
| `3d3ad8a7` | 2026-09-24 22:30 | #156 | 13 | 59 |
| `bded72b1` | 2026-09-24 22:30 | #155 | 13 | 59 |
| `d8337f9f` | 2026-09-24 22:31 | #154 | 13 | 59 |
| `2d3e2523` | 2026-09-24 22:31 | #231 | 13 | 59 |
| `61dce71b` | 2026-09-24 22:31 | #230 | 13 | 59 |
| `3fe522a4` | 2026-09-24 22:32 | #229 | 10 | 45 |
| `e7f1f8f7` | 2026-09-24 22:32 | #228 | 12 | 55 |
| `22b35c9c` | 2026-09-24 22:33 | #227 | 12 | 53 |
| `a104077c` | 2026-09-24 22:33 | #226 | 9 | 41 |
| `fdc2b79f` | 2026-09-24 22:33 | #225 | 8 | 40 |
| `31a86b6f` | 2026-09-24 22:33 | #220 | 2 | 29 |
| `dc958280` | 2026-09-24 22:34 | #219 | 2 | 4 |
| `458ab17c` | 2026-09-24 22:34 | #215 | 6 | 11 |
| `12411734` | 2026-09-24 22:34 | #82 | 4 | 5 |
| `f39feefa` | 2026-09-24 22:34 | #209 | 2 | 3 |
| `bd841779` | 2026-09-24 22:34 | #208 | 1 | 1 |
| `4bdee896` | 2026-09-24 23:27 | #173 | 14 | 69 |
| `00c0d2cc` | 2026-09-24 23:28 | #179 | 23 | 231 |
| `5f22e9d4` | 2026-09-24 23:29 | #180 | 23 | 231 |
| `e4c2cea4` | 2026-09-24 23:30 | #181 | 23 | 236 |
| `828749df` | 2026-09-24 23:30 | #182 | 24 | 274 |
| `7139c6bf` | 2026-09-24 23:31 | #183 | 24 | 275 |
| `fbfa9370` | 2026-09-24 23:32 | #184 | 25 | 283 |
| `84a0765a` | 2026-09-24 23:33 | #185 | 24 | 297 |
| `1a0dae41` | 2026-09-24 23:34 | #186 | 23 | 235 |
| `f585217f` | 2026-09-24 23:34 | #187 | 23 | 237 |
| `94690e77` | 2026-09-24 23:35 | #188 | 14 | 72 |
| `7515f985` | 2026-09-24 23:36 | #189 | 24 | 274 |
| `379730b6` | 2026-09-24 23:36 | #190 | 24 | 277 |
| `d4953d05` | 2026-09-24 23:37 | #191 | 24 | 275 |
| `a0cd1cb3` | 2026-09-24 23:38 | #192 | 24 | 275 |
| `c3c74c55` | 2026-09-24 23:39 | #193 | 25 | 299 |
| `571eb806` | 2026-09-24 23:40 | #143, #197, #198, #199, #200, #201, #202, #203 | 25 | 278 |
| `edc9beff` | 2026-09-25 08:03 | #196 | 56 | 184 |

## Weitere Auffälligkeiten

- **Stil-Commits rückwärts:** Die Stil-Commits vom 24.09. liefen in umgekehrter Arbeitsreihenfolge (z.B. #178 um 22:23:02, #177 um 22:23:31, #176 um 22:23:59). Nach dem Datum der Spitze sortiert, würden 36 inhaltliche Abhängigkeiten aus den PR-Texten verletzt, nach dem Sortierdatum oben nur 11.
- **Inhaltliche Abhängigkeiten aus PR-Texten**, die die chronologische Reihenfolge nicht einhält (die Datumsregel hat Vorrang; die Git-Vorgänger sind trotzdem immer erfüllt): #170 braucht #226 (Schritt 43 vor 52), #171 braucht #226 (Schritt 44 vor 52), #173 braucht #162 (Schritt 63 vor 73), #178 braucht #177 (Schritt 48 vor 51), #179 braucht #174 (Schritt 49 vor 56), #182 braucht #181 (Schritt 53 vor 71), #182 braucht #162 (Schritt 53 vor 73), #184 braucht #162 (Schritt 64 vor 73), #229 braucht #226 (Schritt 25 vor 52), #230 braucht #218 (Schritt 26 vor 69), #230 braucht #228 (Schritt 26 vor 55). Grund ist meist, dass der Vorgänger danach noch Nachbesserungen bekam (z.B. #226: zwei Spitzhacken-Commits vom 20.09.).
- **Kein Git-Vorgänger ist später datiert als sein Nachfolger.** Nur #205 und #62 haben dieselbe Sekunde (07.09. 01:11:31); #205 ist Vorgänger von #62 und kommt zuerst.
- **Autor-Datum weicht stark ab** (mehr als eine Stunde) bei: #207, #205, #82, #215, #216, #81, #217, #198, #199, #200, #201, #202, #203. Das sind nachträglich neu aufgesetzte Commits (z.B. Herz-Kette: geschrieben 26./27.09., neu aufgesetzt 27.09. 16:43 bis 17:06). Die Reihenfolge ändert sich dadurch nicht, weil diese Branches in Ketten liegen.
- **Kein Branch steckt schon vollständig in upstream.** 40 Branches bauen auf einem 6 Commits älteren upstream-Stand auf (`be44649f`); das ist unproblematisch.
- **Schon in upstream enthalten:** Der Commit `bd188b46` "Lay the spell buttons out in two rows" steckt in 18 Branches und ist inhaltsgleich mit upstream `bab847a6`. Unproblematisch.
- **Branch-Spitzen sind nicht die Stapel-Basis.** Viele PRs sind laut Beschreibung gestapelt, Git sieht das aber nicht, weil jede Spitze einen eigenen Stil-Commit trägt. Ohne diese Stil-Commits steckt der Vorgänger meist tatsächlich in der Historie des Nachfolgers.

## Abweichungen zur Handoff-Tabelle

- Die direkten Git-Vorgänger (per `git merge-base --is-ancestor` für alle Paare neu bestimmt) stimmen für alle 83 Branches **genau** mit der Tabelle im Handoff überein. 64 Spitzen, 19 Branches stecken in anderen.
- Die Reihenfolge-Regeln des Handoffs (PR-Nummer, Ketten nur über die Spitze, "beide Features erhalten") sind auf Wunsch von Mario ersetzt durch: chronologisch, jeder Branch einzeln, "späterer Commit gewinnt".
- Der Handoff-Testlauf (zufällige Reihenfolge) hatte 53 von 64 Merges mit Konflikt. In der chronologischen Reihenfolge sind es 43 von 83 Schritten. Ein früherer Probelauf nach PR-Nummer (nur Spitzen, 74 Schritte, ohne diese Konfliktregel) hatte 33 Schritte mit neuen Konflikten.
- Neu gegenüber dem Handoff: der Sonderfall #218 (siehe oben) und die Stil-Commits an den Spitzen.

## Vergleich mit `full-build-h1-h7` (späterer Schritt)

`full-build-h1-h7` (Spitze `a1e8abd4`, 27.09. 23:29, lokal und auf origin gleich) hat **keinen gemeinsamen Vorfahren** mit `upstream/shaders-improvement`: seine Wurzel ist `825ef131` (alte Linie, wie `archive/main-2026-09-05`), die von upstream `c1947e3b`. Der Vergleich muss deshalb über die **Dateibäume** laufen, nicht über die Historie:

- geeignet: `git diff --stat integration/all full-build-h1-h7`, `git diff integration/all full-build-h1-h7 -- <pfad>`, `git diff --name-status ...` (vergleicht nur die beiden Stände).
- nicht geeignet: `git log A..B`, `git diff A...B`, `git merge-base`, `git cherry`, `git branch --contains`. Sie brauchen eine gemeinsame Historie und liefern hier nichts Sinnvolles.
- Zu erwarten sind Unterschiede durch Arbeit ohne PR (z.B. H7-Herzmodell, Dokumentation der alten Linie) und durch den Sonderfall #218.

## Konflikt-Hotspots im Probelauf

Dateien mit den meisten Konfliktschritten: `source/modes/GameMode.cpp` (13), `source/render/CreaturePanel.cpp` (13), `source/render/RenderManager.cpp` (11), `source/camera/CameraManager.cpp` (10), `source/gamemap/RoomObjectNavigation.cpp` (10), `source/render/Gui.cpp` (7), `source/modes/GameMode.h` (7), `gui/OD.looknfeel` (7), `README.md` (5), `source/network/ServerNotification.cpp` (5), `source/network/ServerNotification.h` (5), `source/modes/SettingsWindow.cpp` (4).

## Probelauf: Methode

Temporärer Worktree im Scratchpad, detached auf `upstream/shaders-improvement`. Jeder Schritt mit `git merge --no-ff --no-commit`, Konflikte nach Regel 5 automatisch aufgelöst (`git blame --ignore-revs-file` auf beiden Seiten, `merge.conflictStyle=diff3`, `rerere` aus), das Ergebnis als unreferenzierter Commit zur Basis des nächsten Schritts. Kein Branch, kein Push, keine Änderung im Hauptcheckout. Der Worktree wurde danach entfernt. Grenzen: Die Simulation schreibt keine `auto`-Typen aus und kompiliert nicht; "per Datei-Datum" heisst, die Zeilen liessen sich im Blame nicht eindeutig zuordnen und es zählte der jüngste inhaltliche Commit an der Datei.
