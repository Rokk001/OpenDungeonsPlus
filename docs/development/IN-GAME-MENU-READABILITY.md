# In-game menu readability

The September 20 screenshot shows the saved-game browser, not the loading
progress screen. Its shared menu-page look deliberately draws no background
over the main-menu artwork, but was also reused over the detailed dungeon.

Reuse the existing dark in-game settings look only when opening the browser
from gameplay, and restore the transparent menu look on main-menu entry.
Keep its sibling loading/error text above the new backdrop. Save/load logic,
pause restoration, controls, text and menu artwork remain unchanged.

Audit: the other selection pages are main-menu modes; in-game settings already
use the dark settings look, and save/confirmation dialogs use framed windows.
No other in-game transparent selection page was found.

The installed CEGUI probe passes 20 checks, including repeated in-game/main-menu
switching, retained saved items, full-viewport coverage and loading text above
the backdrop. Release compilation and user appearance acceptance are pending.
