## OpenDungeonsPlus

OpenDungeonsPlus is an open source, real time strategy game sharing game elements
with the Dungeon Keeper series and Evil Genius. Players build an underground
dungeon which is inhabited by creatures. Players fight each other for control
of the underground by indirectly commanding their creatures, directly casting
spells in combat, and luring enemies into sinister traps.

The game is developed by a friendly community of developers and artists, and
has now reached a quite playable and enjoyable status after more than 6 years
of development.

### How to play

The control panel groups Creatures, Rooms, Spells and Workshop beside the
circular map at the bottom left. Press G to hide or reveal the panel content.
With Windows OIS input, the pointer starts at navigation when the application or a game opens.
The gameplay panel uses a scaled stone surface with a dark inset for worker statistics.
Rooms, Spells and Workshop use large icons for small groups and compact columns
when more actions are available or the interface scale leaves insufficient space.
Options provides help, research and player information as well as game settings.
In-game Settings opens a category menu for graphics, sound, controls, user cameras
and additional game settings; closing a category returns to that menu, Back
returns to Options, and Continue Game returns to the current session.
Open End Game for the existing main-menu and desktop exit actions; Back returns
to Options, and Continue Game closes the menu without leaving the session.
Select the question-mark button beside the minimap, then click a creature to
open its information. Click the button again or right-click the world to cancel.
Select the removal button beside the minimap, then click an owned room tile,
trap or door to sell it. The button or a world right-click cancels sale mode.
This is the single gameplay sale control; separate removal buttons remain in
the editor only.
Press F10 to toggle Options. Escape closes the frontmost open dialog or list,
or returns from a main-menu submenu to the preceding screen.
Skirmish, Multiplayer and Map Editor open separate menu pages; click the cross
at the bottom right or press Escape to return to the main menu.
Settings opens a category page for graphics, sound, controls and game options;
closing or applying a settings page returns to these categories.
Press Print Screen to save a PNG screenshot from menus, dialogs, gameplay or
the editor; images use the existing timestamped filenames in the configured
user-data directory.
With edge scrolling enabled, the camera also scrolls at screen edges covered by
the fixed HUD. New messages arrive from the right as individual flashing
information tabs; left-click a tab to read it and right-click to dismiss it
after reading. The tick closes the message window, while the cross removes
that message. Notices beyond the visible rail remain queued until space opens.
Save opens the message surface for the server's confirmation or error.

Use the mouse wheel or Home/End for camera zoom; F1/F2/F3 select isometric,
top-down and oblique views, and F4/F6 recall stored views 1/3; all three stored
views remain available through Options. Press F5 to save the game directly.
Press M to open the map: left-click to move there, or right-click, M or Escape
to close it without moving. The detail window follows the pointer.
The magnifier button beside the minimap zooms it in with a left-click and out with
a right-click; clicking the minimap moves the camera immediately.
H focuses the dungeon heart, P cycles owned portals and F focuses the next fight.
The default minimap uses terrain and owner colours, with darker fortified walls
and a dotted heart direction when zoomed out; saved renderer preferences remain available.
The minimap and full map show the current camera view as a thin white outline.
An upright N inside the minimap rim tracks world north as the map rotates.
The four corner controls attach outside the circular map; their curved cutouts
leave the map visible and clickable.

The upper resource strip shows current mana and gold beside round badges;
mana change appears on a smaller line below, and hovering gold shows storage
capacity in the upper context strip.

Hover building, workshop or spell icons to see a short name beside the pointer
and their description and current cost in the upper context strip. Buildings and
traps show gold per tile; spells show mana per cast or creature, including the
current price of the next summoned worker. Detailed creature, resource, minimap
and message help also appears above, with concise local labels. Menus and dialogs
retain their local help without duplicating it in the upper strip.
Local help is placed outside the visible hand and kept inside the screen.

The active HUD category has a colored inset and a gold frame that remain visible
when the pointer moves away or hovers over another category.
The category symbols are a person, house, wand and pickaxe for Creatures, Rooms,
Spells and Workshop respectively.
The narrow controls to their right use paired arrows to hide/show the panel
and an eye for objectives, followed by the message queue.
The Creatures tab shows portraits and counts by type, with Total, Jobs, Fighting
and Moods views and separate worker counts. Use the arrows to browse creature
types, left-click a count to pick up a matching available creature, or right-click
a portrait to move the camera to one of that type.
The population panel uses illustrated portraits where artwork is supplied;
creatures without artwork retain their model preview. Artwork and its generation
records are described in the [portrait asset guide](materials/portraits/README.md).
Hold Ctrl and period while clicking a portrait or count to pick the highest
available level, or Ctrl and comma to pick the lowest; counts retain their filter.

The hand points at pickup targets and interface controls, and holds a pickaxe
over diggable walls, which are outlined on hover.
Confirming or removing digging marks plays one short downward tool strike.
It shows the selected action icon or a prohibition sign for an invalid
target; the top strip describes the current target. Right-click cancels an active
action, drops a held object or slaps an eligible creature with an empty hand.
Hold Ctrl and turn the mouse wheel to change the order of held objects.
The first displayed object is the next one to drop.
The selected held creature is gripped between finger and thumb; square portraits
beside the hand show held creatures in order, with four portraits per row.
Each miniature uses a square crop of the creature's population-panel portrait.

Visible rooms have local lighting independent of the cursor, while overlapping
lights and the ambient-light setting preserve the colours of terrain and creatures.

Future versions will have an in-game tutorial, but for now, you can use the
following resources to learn the basic gameplay concepts:

- In-game help screen, available through Options
- Video tutorial (version 0.5.0): https://www.youtube.com/watch?v=P4MClQUdb0E
- Wiki page: https://github.com/OpenDungeons/OpenDungeons/wiki/Gameplay

You can play singleplayer levels using the Skirmish menu, or host/join a
multiplayer game by using the corresponding menus.

### Be part of the community

As free software aficionados, we value community-based development and
welcome any willing contributor regardless of their skills. Giving us
feedback about the gameplay, or reporting bugs on our tracker, is already
a very relevant way of contributing to the development of this game,
so please get in touch!

You will find us on the following channels:
- Snapcraft: https://snapcraft.io/opendungeons-plus
- Discord (Scroll down and click "Links"): https://flathub.org/apps/io.github.tomluchowski.OpenDungeonsPlus 
- OpenDungeons (upstream code):
  - Forum: http://forum.freegamedev.net/viewforum.php?f=15
  - GitHub: https://github.com/tomluchowski/OpenDungeonsPlus
  - IRC: #opendungeons channel on Freenode

### Build instructions

For this fork's local Windows setup, see the maintained
[development environment](docs/development/WINDOWS-DEV-SETUP.md) and
[configure/build commands](docs/development/BUILDING.md), including verified status.
Diagnosed Windows compiler and linker failures are recorded in the
[build fixes and validation notes](docs/development/WINDOWS-BUILD-FIXES.md).
Direct Windows startup and its verification are covered in the
[startup fixes](docs/development/WINDOWS-STARTUP-FIXES.md).

If you retrieve the source code of OpenDungeonsPlus and want to have a go at
building it yourself, have a look at platform-specific build instructions
on our wiki: https://github.com/OpenDungeons/OpenDungeons/wiki/Compile

In a few words, to build OpenDungeonsPlus, you need the following libraries:

- OGRE SDK (1.9.x)
- Boost (same version that OGRE was linked against)
- CEGUI SDK (0.8.x)
- SFML (2.x)
- OIS

You will also need a recent CMake version (2.8 or newer) and a compiler
that supports C++11 features reasonably well, i.e.:

- Linux: GCC 4.8+
- Windows: MSVS 2013 Express or MinGW 4.8+

On an UNIX system, you can then run:
```
mkdir build && cd build
cmake ..
make -jX    // X is the number of CPU cores that you want to allocate  
```
And run the *opendungeons* output binary.

### Contributing code

For creature asset work, the [portrait export tool](tools/portraits/README.md)
builds a standalone preview from the game's renderer and exports the configured
creatures to PNG files.

If you want to contribute code, you should take a look at our coding
guidelines: https://github.com/OpenDungeons/OpenDungeons/wiki/Code-Guidelines

It contains a rather deep introduction on how we name, indent, structure and
extend our code. It also has some performance optimisation tips.

Keep each pull request focused on one coherent, independently reviewable
product change. Include documentation only when it is required to use, build or
review that change. Do not include internal planning notes, agent instructions,
local environment records or unrelated documentation commits in an upstream
pull request.

#### Repository organisation

**Data files**
```
config/          - Several game config files
dist/            - Icons and linux desktop entry file.
gui/             - CEGUI files + corresponding Gui images
levels/          - Game levels
licenses/        - License files used for game data and code
materials/       - Materials (models texturing scripts and textures)
models/          - Model files
music/           - Music files
particles/       - Particle effects scripts
scripts/         - Various packaging and CI scripts
sounds/          - Game Sounds
AUTHORS          - List of past and current contributors
CREDITS          - Detailed listing of licenses and credits for our assets
LICENSE.md       - General information about the code and assets licenses
README.md        - The file you are currently reading
RELEASE-NOTES.md - What's new in OpenDungeonsPlus
```

**Code files**
```
cmake/           - Helper files for CMake
 |- config/      - Variable input files for the CMake script
 |- modules/     - Addon scripts for CMake to find dependencies
sources/         - All our own .cpp and .h files of the game
tools/           - Some developers shell scripts
.gitignore       - The files and folders that are ignored by git locally
CMakeLists.txt   - CMake script for generating the Makefile and IDE projects
```
