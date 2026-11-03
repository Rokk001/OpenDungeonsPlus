"""Check that identical event notices show only one message tab. Text check, no game start."""
from pathlib import Path

repo = Path(__file__).resolve().parents[2]
game_mode = (repo / 'source/modes/GameMode.cpp').read_text(encoding='utf-8')

start = game_mode.index('void GameMode::receiveEventShortNotice(EventMessage* event)')
body = game_mode[start:game_mode.index('\n}\n', start)]
# The duplicate scan must come before the tab window is created, and drop the repeated event.
scan = body.index('for(MessageTab& pending : mMessageTabs)')
create = body.index('createWindow("OD/GameTabButton")')
assert scan < create
assert 'pending.message->getMessage() != event->getMessage()' in body[scan:create]
assert 'delete event;' in body[scan:create]
assert 'return;' in body[scan:create]
# Each created tab is destroyed on dismissal and in the destructor.
assert 'destroyWindow(found->window)' in game_mode
assert 'destroyWindow(tab.window)' in game_mode
print('check_message_tab_unique OK')
