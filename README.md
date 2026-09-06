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
Options provides help, research and player information as well as game settings.
Select the question-mark button beside the minimap, then click a creature to
open its information. Click the button again or right-click the world to cancel.
Select the currency button beside the minimap, then click an owned room tile,
trap or door to sell it. The button or a world right-click cancels sale mode.
Press F10 to toggle Options. Escape closes the frontmost open dialog or list,
or returns from a main-menu submenu to the preceding screen.
With edge scrolling enabled, the camera also scrolls at screen edges covered by
the fixed HUD. New messages flash the Messages button; left-click it to read
them and right-click to dismiss read messages. Save opens the message surface
for the server's confirmation or error.

Use the mouse wheel or Home/End for camera zoom; F1/F2/F3 select isometric,
top-down and oblique views, and F4-F6 recall views stored through Options.
Press M to open the map: left-click to move there, or right-click, M or Escape
to close it without moving. The detail window follows the pointer.
The +/- button beside the minimap zooms it in with a left-click and out with
a right-click; clicking the minimap moves the camera immediately.
H focuses the dungeon heart, P cycles owned portals and F focuses the next fight.
The default minimap uses terrain and owner colours, with darker fortified walls
and a dotted heart direction when zoomed out; saved renderer preferences remain available.

The Creatures tab shows portraits and counts by type, with Total, Jobs, Fighting
and Moods views and separate worker counts. Use the arrows to browse creature
types, left-click a count to pick up a matching available creature, or right-click
a portrait to move the camera to one of that type.
Hold Ctrl and period while clicking a portrait or count to pick the highest
available level, or Ctrl and comma to pick the lowest; counts retain their filter.

The hand points at pickup targets and interface controls, and holds a pickaxe
over diggable walls, which are outlined on hover.
It shows the selected action icon or a prohibition sign for an invalid
target; the top strip describes the current target. Right-click cancels an active
action, drops a held object or slaps an eligible creature with an empty hand.
Hold Ctrl and turn the mouse wheel to change the order of held objects.
The first displayed object is the next one to drop.
The selected held creature is gripped between finger and thumb; square portraits
beside the hand show held creatures in order, with four portraits per row.

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

If you want to contribute code, you should take a look at our coding
guidelines: https://github.com/OpenDungeons/OpenDungeons/wiki/Code-Guidelines

It contains a rather deep introduction on how we name, indent, structure and
extend our code. It also has some performance optimisation tips.

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
