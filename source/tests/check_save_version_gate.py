"""Static check: saves written by another build of a supported release load; failures name their cause.

Pure Python, needs no compiler. Mirrors the rule of MapHandler::isSupportedVersionHeader, checks that the
source still uses it at both gates, and runs the rule on a fresh header and on any --save files.
"""
import argparse
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--save", action="append", default=[])
args = parser.parse_args()
failures = []


def check(condition, label):
    if not condition:
        failures.append(label)


handler = (root / "source/gamemap/MapHandler.cpp").read_text(encoding="utf-8")
server = (root / "source/network/ODServer.cpp").read_text(encoding="utf-8")
menu = (root / "source/modes/MenuModeLoad.cpp").read_text(encoding="utf-8")
cmake = (root / "CMakeLists.txt").read_text(encoding="utf-8")
version = ".".join(re.search(r"set\(" + name + r"\s+(\d+)\)", cmake).group(1)
                   for name in ["OD_MAJOR_VERSION", "OD_MINOR_VERSION", "OD_PATCH_LEVEL"])
current = "OpenDungeons_Version:" + version + ".21"
releases = re.findall(r'"(OpenDungeons_Version:[0-9.]+)"', handler[handler.index("bool isSupportedVersionHeader("):])
check(releases == ["OpenDungeons_Version:0.7.1", "OpenDungeons_Version:0.7.2", "OpenDungeons_Version:0.7.4"],
      "supported release list changed: %s" % releases)


def supported(header):
    if header == current:
        return True
    for base in releases:
        if header == base:
            return True
        if header.startswith(base + ".") and header[len(base) + 1:].isdigit():
            return True
    return False


for header in ("OpenDungeons_Version:0.7.4.20", "OpenDungeons_Version:0.7.4.21", "OpenDungeons_Version:0.7.4",
               "OpenDungeons_Version:0.7.1", "OpenDungeons_Version:0.7.2.5"):
    check(supported(header), "must load: " + header)
for header in ("OpenDungeons_Version:0.6.0", "OpenDungeons_Version:0.7.4.", "OpenDungeons_Version:0.7.4.x",
               "OpenDungeons_Version:0.7.40", "OpenDungeons_Version:99.0.0", "invalid"):
    check(not supported(header), "must be rejected: " + header)

# A save is written with the running version string, so a freshly written file passes the gate.
check(supported(current), "fresh header must load")

# Both gates use the shared helper, none keeps the old exact-match chain.
check(handler.count("isSupportedVersionHeader(nextParam)") == 2, "both gates use isSupportedVersionHeader")
check('nextParam != "OpenDungeons_Version:0.7.4"' not in handler, "old exact-match gate removed")
# The exact cause reaches log and menu.
check('setLoadError("Unsupported file version' in handler, "version failure names the file version")
check("MapHandler::getLastLoadError()" in server, "server logs the cause")
check("MapHandler::getLastLoadError()" in menu, "menu shows the cause")

for save in args.save:
    text = Path(save).read_text(encoding="utf-8", errors="replace")
    first = text.split(None, 1)[0]
    check(supported(first), "save header not loadable: %s (%s)" % (save, first))
    check(re.search(r"^\[Info\]$", text, re.M) is not None, "save has no [Info]: " + save)

if failures:
    print("FAILURES:\n" + "\n".join(failures))
    sys.exit(1)
print("check_save_version_gate: OK")
