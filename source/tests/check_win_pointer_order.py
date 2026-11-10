"""Run the pointer ordering check against actual Win32 and CEGUI behavior."""
import pathlib
import runpy

runpy.run_path(str(pathlib.Path(__file__).with_name('check_win_pointer_runtime.py')), run_name='__main__')
