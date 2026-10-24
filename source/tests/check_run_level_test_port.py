"""The level load test can give the game its own server port, so parallel instances do not collide.

No compiler, no game: run-level-test.py is loaded, subprocess.Popen is replaced by a recorder, and the
command lines of the menu test and of a level run are checked with and without --port."""
from pathlib import Path
import importlib.util
import subprocess
import sys

root = Path(__file__).resolve().parents[2]

spec = importlib.util.spec_from_file_location('run_level_test', str(root / 'scripts' / 'run-level-test.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

commands = []


class RecordedProcess(object):
    """Stands in for the game process: records nothing more than that it ran and ended with code 3."""
    returncode = 3

    def communicate(self, timeout=None):
        return '', None


def record(command, **kwargs):
    commands.append(list(command))
    return RecordedProcess()


original = subprocess.Popen
subprocess.Popen = record
try:
    module.run_menu_test('game.exe', 1)
    module.run_menu_test('game.exe', 1, 31301)
    module.run_level_with_frame_time('game.exe', 'a.level', 1)
    module.run_level_with_frame_time('game.exe', 'a.level', 1, 31302)
finally:
    subprocess.Popen = original

assert len(commands) == 4, commands
assert '--port' not in commands[0] and '--port' not in commands[2], 'no port requested, none may be passed'
assert commands[1][-2:] == ['--port', '31301'], commands[1]
assert commands[3][-2:] == ['--port', '31302'], commands[3]
assert module.port_arguments(None) == [] and module.port_arguments(5) == ['--port', '5']

# The command line option exists and the game knows --port
assert '--port' in (root / 'scripts' / 'run-level-test.py').read_text(encoding='utf-8')
assert '("port"' in (root / 'source' / 'utils' / 'ResourceManager.cpp').read_text(encoding='utf-8'), 'game has no --port'
print('ok')
