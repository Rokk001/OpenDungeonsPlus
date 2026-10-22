#!/usr/bin/env python3
# Rewrites the length field of the root chunk in MeshSerializer_v1.8 mesh files.
#
# The files were written with a wrong length in the root chunk (id 0x3000 at offset 24, length as
# uint32 at offset 26) while all sub chunks are valid and end exactly at the end of the file.
# OGRE 14 checks the chunk length and rejects such files. A file is only changed when the chain of
# sub chunks starting at offset 31 ends exactly at the end of the file; otherwise it is reported.
#
# Usage: fix-mesh-root-chunk-length.py [--check] [models directory]

import os
import struct
import sys

HEADER = b"\x00\x10[MeshSerializer_v1.8]\n"
ROOT_ID_OFFSET = 24
ROOT_LENGTH_OFFSET = 26
FIRST_SUB_CHUNK_OFFSET = 31
CHUNK_HEADER_SIZE = 6


def sub_chunks_end_at_file_end(data):
    """Returns True when the chain of sub chunks from offset 31 ends exactly at the end of data."""
    pos = FIRST_SUB_CHUNK_OFFSET
    while pos < len(data):
        if pos + CHUNK_HEADER_SIZE > len(data):
            return False
        length = struct.unpack_from("<I", data, pos + 2)[0]
        if length < CHUNK_HEADER_SIZE or pos + length > len(data):
            return False
        pos += length
    return pos == len(data)


def main():
    args = [a for a in sys.argv[1:] if a != "--check"]
    check_only = "--check" in sys.argv[1:]
    directory = args[0] if args else "models"
    fixed = 0
    already_ok = 0
    skipped = []
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".mesh"):
            continue
        path = os.path.join(directory, name)
        with open(path, "rb") as f:
            data = bytearray(f.read())
        if not data.startswith(HEADER):
            continue
        if struct.unpack_from("<H", data, ROOT_ID_OFFSET)[0] != 0x3000 or not sub_chunks_end_at_file_end(data):
            skipped.append(name)
            continue
        wanted = len(data) - ROOT_ID_OFFSET
        if struct.unpack_from("<I", data, ROOT_LENGTH_OFFSET)[0] == wanted:
            already_ok += 1
            continue
        fixed += 1
        if not check_only:
            struct.pack_into("<I", data, ROOT_LENGTH_OFFSET, wanted)
            with open(path, "wb") as f:
                f.write(data)
    print("fixed=%d already_ok=%d skipped=%d" % (fixed, already_ok, len(skipped)))
    for name in skipped:
        print("not changed (sub chunk chain does not end at the end of the file): " + name)
    return 1 if skipped else 0


if __name__ == "__main__":
    sys.exit(main())
