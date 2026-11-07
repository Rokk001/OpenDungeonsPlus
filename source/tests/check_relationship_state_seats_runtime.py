"""Runtime load check with configured seats: a save with [RelationshipState] lines keeps those relationships.

The server only restores saved relationship state after the seats are configured (GameMap::createAllEntities needs
mSeatsConfigured). The plain --serversave start has no client, so nothing configures the seats and the restore never
runs. This check starts the game on a copy of the save in a new, empty app-data folder, connects a test client to it
over the game's own protocol, and drives the same normal path the game client uses for a loaded save whose seats are
fixed (ODClient.cpp, ServerNotificationType::pickNick, ServerMode::ModeGameLoaded):

    hello -> (loadLevel) -> levelOK -> (pickNick) -> setNick -> readyForSeatConfiguration -> seatConfigurationSet

Packet layout, as written by ODPacket (SFML sf::Packet):
  - each message is a frame: uint32 payload size, big-endian, then the payload;
  - int32 (also every enum class value): big-endian; string: uint32 length + UTF-8 bytes; bool: one byte 0/1.
  - hello: int32 type + string "OpenDungeons V <VERSION> / wire-3" (NetworkProtocol::WIRE_SCHEMA_SUFFIX)
  - levelOK: int32 type
  - setNick: int32 type + string nick + 7 bools (the server asked for all seven in pickNick)
  - readyForSeatConfiguration, seatConfigurationSet: int32 type only
The enum values are read from source/network/ClientNotification.h and ServerNotification.h, not hard-coded.

The run passes only when, with the same rules as check_relationship_state_load_headless.py:
  - the game is alive after --seconds, the log has no invalid RelationshipState section, the server reached
    "Server connected and listening", the test client got loadLevel and pickNick and was not rejected,
  - every creature of the save's [RelationshipState] block that is in the level is logged as restored, and the logged
    rage turns, rage seat, brawl opponent, brawl turns and captor names equal the values derived from the save by the
    loader's rules (load.restored_values); creatures that are not in the level are logged as unknown, and
  - for the committed fixture, the logged values also match the fixed expectations (load.FIXTURE_EXPECTED).
  Grief is compared as a record: the logged grief equals the loader's value (restored without applying the mood again).
The original save is never opened for writing; the check works on a copy. It refuses to run while another
opendungeons-plus.exe is running, so a game the owner is playing is never touched.

The hello message carries the build version, so --version is required: it must be the version of the executable
(OD_VERSION = MAJOR.MINOR.PATCH.BUILD_NUMBER, for example 0.7.4.44 for build number 44). It is not guessed or
hard-coded here; a wrong value is refused by the server (wire check in ODServer.cpp).

Without --exe the check runs only the static part: the protocol enum names and the wire suffix must exist in the
sources. The normal runner (check_relationship_state_load_headless.py, no arguments) calls static_protocol_check().

Usage:
  check_relationship_state_seats_runtime.py --exe PATH --version X.Y.Z.N [--save PATH] [--seconds 30] [--port 31231]
  check_relationship_state_seats_runtime.py                       (static part only)
"""
import argparse
import glob
import os
from pathlib import Path
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_relationship_state_load_headless as load  # noqa: E402  (same folder: shared checks and constants)

HERE = Path(__file__).resolve().parent
SRC = HERE.parent
WIRE_SUFFIX = " / wire-3"
PICK_NICK_FLAGS = 7


def enum_values(header, enum_name):
    """Returns the member names of 'enum class <enum_name>' in declaration order (comments removed)."""
    text = (SRC / "network" / header).read_text(encoding="utf-8", errors="replace")
    match = re.search(r"enum class " + enum_name + r"\s*\{(.*?)\};", text, re.S)
    if match is None:
        raise SystemExit("ERROR: enum %s not found in %s" % (enum_name, header))
    body = "\n".join(line.split("//", 1)[0] for line in match.group(1).split("\n"))
    return [name.strip() for name in body.split(",") if name.strip()]


CLIENT_TYPES = enum_values("ClientNotification.h", "ClientNotificationType")
SERVER_TYPES = enum_values("ServerNotification.h", "ServerNotificationType")


def client_type(name):
    return CLIENT_TYPES.index(name)


def static_protocol_check():
    """Returns failures when the messages or the wire suffix used below are not in the sources (no game needed)."""
    failures = []
    for name in ("hello", "levelOK", "setNick", "readyForSeatConfiguration", "seatConfigurationSet"):
        if name not in CLIENT_TYPES:
            failures.append("client message %s is not in ClientNotification.h" % name)
    for name in ("loadLevel", "pickNick", "clientAccepted", "clientRejected"):
        if name not in SERVER_TYPES:
            failures.append("server message %s is not in ServerNotification.h" % name)
    protocol = (SRC / "network" / "ODPacket.h").read_text(encoding="utf-8", errors="replace")
    if 'WIRE_SCHEMA_SUFFIX = "' + WIRE_SUFFIX + '"' not in protocol:
        failures.append("the wire suffix in ODPacket.h is not '%s'" % WIRE_SUFFIX)
    return failures


def server_type_name(value):
    return SERVER_TYPES[value] if 0 <= value < len(SERVER_TYPES) else "unknown(%d)" % value


def frame(payload):
    return struct.pack(">I", len(payload)) + payload


def pack_int(value):
    return struct.pack(">i", value)


def pack_string(text):
    data = text.encode("utf-8")
    return struct.pack(">I", len(data)) + data


def pack_bool(value):
    return b"\x01" if value else b"\x00"


def recv_exact(sock, size):
    data = b""
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise ConnectionError("the server closed the connection")
        data += chunk
    return data


def recv_frame(sock):
    """Returns the payload of the next server message (blocking, subject to the socket timeout)."""
    (size,) = struct.unpack(">I", recv_exact(sock, 4))
    return recv_exact(sock, size)


def server_message_type(payload):
    return struct.unpack(">i", payload[:4])[0]


def wait_for_type(sock, wanted, received, deadline):
    """Reads messages until one has the wanted server type. Returns its payload, or None on deadline."""
    while time.time() < deadline:
        try:
            payload = recv_frame(sock)
        except socket.timeout:
            continue
        kind = server_message_type(payload)
        received.append(server_type_name(kind))
        if kind == SERVER_TYPES.index(wanted):
            return payload
    return None


def connect(port, deadline, process):
    while time.time() < deadline and process.poll() is None:
        try:
            sock = socket.create_connection(("127.0.0.1", port), timeout=2)
            sock.settimeout(2)
            return sock
        except OSError:
            time.sleep(0.5)
    return None


def drive_seats(sock, version, nick, seconds, received):
    """Runs the normal loaded-save handshake. Returns a list of failures and the time the window ends."""
    failures = []
    deadline = time.time() + seconds
    hello = pack_int(client_type("hello")) + pack_string("OpenDungeons V " + version + WIRE_SUFFIX)
    sock.sendall(frame(hello))

    if wait_for_type(sock, "loadLevel", received, time.time() + 30) is None:
        return ["no loadLevel from the server after hello"], deadline
    sock.sendall(frame(pack_int(client_type("levelOK"))))

    if wait_for_type(sock, "pickNick", received, time.time() + 30) is None:
        return ["no pickNick from the server after levelOK"], deadline
    set_nick = pack_int(client_type("setNick")) + pack_string(nick) + b"".join(
        pack_bool(True) for _ in range(PICK_NICK_FLAGS))
    sock.sendall(frame(set_nick))
    sock.sendall(frame(pack_int(client_type("readyForSeatConfiguration"))))
    sock.sendall(frame(pack_int(client_type("seatConfigurationSet"))))

    # Keep the connection open while the server loads the save; record what it sends back.
    while time.time() < deadline:
        try:
            payload = recv_frame(sock)
        except socket.timeout:
            continue
        except ConnectionError:
            failures.append("the server closed the test client connection before the window ended")
            break
        received.append(server_type_name(server_message_type(payload)))
    if "clientRejected" in received:
        failures.append("the server rejected the test client (clientRejected): seats were not configured")
    return failures, deadline


def logged_restore(log, name):
    """The values of the first 'Restored relationship state' log line of the creature, or None when there is none."""
    for line in log.splitlines():
        match = load.RESTORED_LINE.search(line)
        if match is None or match.group("name") != name:
            continue
        captors = match.group("captors")
        return {
            "grief": int(match.group("grief")),
            "rageTurns": int(match.group("rage")),
            "rageSeat": int(match.group("seat")),
            "brawlOpponent": match.group("opponent"),
            "brawlTurns": int(match.group("brawl")),
            "captors": captors.split("|") if captors else [],
            "captorCount": int(match.group("count")),
        }
    return None


def runtime_check(exe, save, seconds, entries, existing, is_fixture, port, version):
    """Starts the game with a test client on a copy of the save. Returns (failures, received) or None when skipped."""
    if load.game_running():
        print("SKIPPED: an opendungeons-plus.exe process is running; this check does not touch it")
        return None
    before = load.sha256(save)
    appdata = Path(tempfile.mkdtemp(prefix="relstate-seats-"))
    (appdata / "saves").mkdir()
    shutil.copyfile(save, appdata / "saves" / save.name)

    process = subprocess.Popen([str(exe), "--appData", str(appdata), "--port", str(port),
                                "--serversave", save.name],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               cwd=str(exe.parent))  # the game reads ./config and ./assets from its own folder
    failures = []
    received = []
    sock = connect(port, time.time() + 60, process)
    if sock is None:
        failures.append("the test client could not connect to port %d" % port)
    else:
        try:
            handshake_failures, _ = drive_seats(sock, version, "RelStateProbe", seconds, received)
            failures += handshake_failures
        except (OSError, ConnectionError, struct.error) as error:
            failures.append("the test client failed: %s" % error)
        finally:
            sock.close()

    exited = process.poll() is not None
    if not exited:
        process.kill()  # our own process, started above
        process.wait()

    log = ""
    for path in glob.glob(os.path.join(str(appdata), "**", "*.log"), recursive=True):
        log += Path(path).read_text(encoding="utf-8", errors="replace")

    if exited:
        failures.append("the game exited with code %d before %d s" % (process.returncode, seconds))
    if load.BAD_SECTION in log:
        failures.append("the log reports an invalid RelationshipState section")
    if load.LISTENING not in log:
        failures.append("the server did not reach '%s'" % load.LISTENING)
    for entry in entries:
        name = entry["name"]
        if name not in existing:
            if (load.UNKNOWN % name) not in log:
                failures.append("the log does not report %s as an unknown creature" % name)
            continue
        if (load.UNKNOWN % name) in log:
            failures.append("the log reports %s as an unknown creature" % name)
        logged = logged_restore(log, name)
        if logged is None:
            failures.append("no restore line for %s in the log" % name)
            continue
        expected = load.restored_values(entry, existing)
        failures += ["%s: restored %s is %r, expected %r" % (name, key, logged[key], expected[key])
                     for key in ("grief", "rageTurns", "rageSeat", "brawlOpponent", "captors")
                     if logged[key] != expected[key]]
        if logged["captorCount"] != len(expected["captors"]):
            failures.append("%s: restored captor count is %d, expected %d"
                            % (name, logged["captorCount"], len(expected["captors"])))
        if expected["brawlOpponent"] and not (1 <= logged["brawlTurns"] <= expected["brawlTurnsAtMost"]):
            failures.append("%s: restored brawlTurns is %d, expected 1..%d"
                            % (name, logged["brawlTurns"], expected["brawlTurnsAtMost"]))
        if not expected["brawlOpponent"] and logged["brawlTurns"] != 0:
            failures.append("%s: restored brawlTurns is %d, expected 0" % (name, logged["brawlTurns"]))
        if is_fixture:
            fixed = load.FIXTURE_EXPECTED[name]
            failures += ["%s: restored %s is %r, the fixed expectation is %r" % (name, key, logged[key], fixed[key])
                         for key in fixed if logged[key] != fixed[key]]
    if load.sha256(save) != before:
        failures.append("the original save changed")
    restored = [line.strip() for line in log.splitlines() if "Restored relationship state" in line]
    shutil.rmtree(appdata, ignore_errors=True)
    return failures, received, restored


DEFAULT_PORT = 31231


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--exe", default=None, help="the game executable; without it only the static part runs")
    parser.add_argument("--save", default=str(load.FIXTURE),
                        help="the save with RelationshipState lines naming existing creatures")
    parser.add_argument("--seconds", type=int, default=30, help="how long the server must stay alive")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help="network port for this run (not the default, so an open game is not used)")
    parser.add_argument("--version", default=None,
                        help="the build version of the executable, required with --exe (for example 0.7.4.44)")
    args = parser.parse_args()

    failures = static_protocol_check()
    for failure in failures:
        print("FAILED static: " + failure)
    if failures:
        return 1
    if args.exe is None:
        print("relationship state seats protocol static check: OK; runtime not run (no --exe)")
        return 0
    if args.version is None:
        print("ERROR: --version is required with --exe (the build version, for example 0.7.4.44)")
        return 2
    return run_with_exe(args.exe, args.save, args.seconds, args.port, args.version)


def exe_embeds_version(exe, version):
    """True when the executable stores the version as a NUL-terminated string (the OD_VERSION literal)."""
    return (version + "\0").encode("ascii") in exe.read_bytes()


def run_with_exe(exe_arg, save_arg, seconds, port, version):
    save = Path(save_arg)
    if not save.is_file():
        print("ERROR: the save does not exist: %s" % save)
        return 2
    exe = Path(exe_arg).resolve()
    if not exe.is_file():
        print("ERROR: the executable does not exist: %s" % exe)
        return 2
    if os.name != "nt":
        print("ERROR: the runtime part runs the Windows game and the tasklist check; it does not run on this system")
        return 2
    if not exe_embeds_version(exe, version):
        # The server refuses a hello whose version differs from the executable and closes the socket, which the
        # check would otherwise report only as "the server closed the connection".
        print("ERROR: --version %s is not the version of %s (the executable has no NUL-terminated %s string); "
              "use the OD_VERSION of this build, for example 0.7.4.44 for build number 44" % (version, exe, version))
        return 2

    is_fixture = save.resolve() == load.FIXTURE.resolve()
    failures, entries, existing = load.static_check(save, is_fixture)
    for failure in failures:
        print("FAILED static: " + failure)
    if failures:
        return 1

    result = runtime_check(exe, save, seconds, entries, existing, is_fixture, port, version)
    if result is None:
        return 2
    runtime, received, restored = result
    print("server messages received by the test client: %s" % ", ".join(sorted(set(received))))
    for line in restored:
        print("log: " + line)
    for failure in runtime:
        print("FAILED runtime: " + failure)
    if runtime:
        return 1
    print("relationship state load with configured seats: OK (%d creatures restored, listening, alive for %d s)"
          % (len(entries), seconds))
    return 0


if __name__ == "__main__":
    sys.exit(main())
