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
  - every creature named in the save's [RelationshipState] block is logged as restored, with no unknown creature, and
  - for the committed fixture, the restored values match the fixed expectations.
The original save is never opened for writing; the check works on a copy. It refuses to run while another
opendungeons-plus.exe is running, so a game the owner is playing is never touched.

Usage:
  check_relationship_state_seats_runtime.py --exe PATH [--save PATH] [--seconds 30] [--port 31231] [--version 0.7.4.44]
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


def runtime_check(exe, save, seconds, names, is_fixture, port, version):
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
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
    for name in names:
        if (load.RESTORED % name) not in log:
            failures.append("no restore line for %s in the log" % name)
        if (load.UNKNOWN % name) in log:
            failures.append("the log reports %s as an unknown creature" % name)
    if is_fixture:
        for name, expected in load.FIXTURE_EXPECTED.items():
            if ((load.RESTORED % name) + expected) not in log:
                failures.append("restored values of %s differ from '%s'" % (name, expected))
    if load.sha256(save) != before:
        failures.append("the original save changed")
    restored = [line.strip() for line in log.splitlines() if "Restored relationship state" in line]
    shutil.rmtree(appdata, ignore_errors=True)
    return failures, received, restored


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--exe", required=True, help="the game executable")
    parser.add_argument("--save", default=str(load.FIXTURE),
                        help="the save with RelationshipState lines naming existing creatures")
    parser.add_argument("--seconds", type=int, default=30, help="how long the server must stay alive")
    parser.add_argument("--port", type=int, default=31231,
                        help="network port for this run (not the default, so an open game is not used)")
    parser.add_argument("--version", default="0.7.4.44",
                        help="the build version of the executable (ODApplication::VERSION, CMake OD_VERSION)")
    args = parser.parse_args()

    save = Path(args.save)
    if not save.is_file():
        print("ERROR: the save does not exist: %s" % save)
        return 2
    exe = Path(args.exe)
    if not exe.is_file():
        print("ERROR: the executable does not exist: %s" % exe)
        return 2
    if os.name != "nt":
        print("ERROR: the runtime part runs the Windows game and the tasklist check; it does not run on this system")
        return 2

    is_fixture = save.resolve() == load.FIXTURE.resolve()
    failures, names = load.static_check(save, is_fixture)
    for failure in failures:
        print("FAILED static: " + failure)
    if failures:
        return 1

    result = runtime_check(exe, save, args.seconds, names, is_fixture, args.port, args.version)
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
          % (len(names), args.seconds))
    return 0


if __name__ == "__main__":
    sys.exit(main())
