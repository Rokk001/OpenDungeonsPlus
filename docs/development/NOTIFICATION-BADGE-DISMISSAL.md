# Direct notification badge dismissal

The existing badge right-click handler already calls the shared dismissal path,
but that method rejects unread messages. Remove only the read-state restriction
and update the badge hint; left-click reading, message ownership cleanup, queue
animation and dismissal of the selected open message remain unchanged.
An unrelated open message must stay open when another badge is dismissed.

The production-handler probe passes 48 checks for read/unread dismissal,
left/middle-click isolation, exact ownership cleanup, unknown-message no-op,
queue refresh and preservation of another open message.
The isolated installed CEGUI/Ogre fixture passes 2,900 checks, including actual
right-click input on unread badges across five resolutions and four scale passes.
The September 20 Release build succeeds; normal deployment follows the queue.
Manual game acceptance remains with the user.
No save, protocol, dependency or version change is required; this note and the
development index document the changed interaction, without a release entry.
