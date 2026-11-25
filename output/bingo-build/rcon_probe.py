#!/usr/bin/env python3
"""RCON probe executed ON the ECS (Python 3.6 compatible).

Reads rcon.password from server.properties without printing it.
"""
import socket
import struct
import sys
import time

pw = None
for line in open("/opt/bingo/server.properties"):
    if line.startswith("rcon.password="):
        pw = line.strip().split("=", 1)[1]
if not pw:
    sys.exit("no rcon password")


def pkt(rid, typ, body):
    d = struct.pack("<ii", rid, typ) + body.encode("utf-8") + b"\x00\x00"
    return struct.pack("<i", len(d)) + d


s = socket.create_connection(("127.0.0.1", 25575), timeout=15)
s.settimeout(4)


def rd():
    hdr = b""
    while len(hdr) < 4:
        chunk = s.recv(4 - len(hdr))
        if not chunk:
            raise IOError("closed")
        hdr += chunk
    n = struct.unpack("<i", hdr)[0]
    b = b""
    while len(b) < n:
        chunk = s.recv(n - len(b))
        if not chunk:
            raise IOError("closed")
        b += chunk
    rid, typ = struct.unpack("<ii", b[:8])
    return rid, typ, b[8:-2].decode("utf-8", "replace")


s.sendall(pkt(1, 3, pw))
authed = False
while True:
    rid, typ, body = rd()
    if typ == 2:
        authed = (rid == 1)
        break
print("AUTH_OK", authed)
if not authed:
    sys.exit("auth failed")


def cmd(c, rid):
    s.sendall(pkt(rid, 2, c))
    time.sleep(1.2)
    parts = []
    while True:
        try:
            r, t, b = rd()
        except socket.timeout:
            break
        if b:
            parts.append(b)
        if r == rid and t == 0:
            break
    return "\n".join(parts)


cmds = sys.argv[1:] or ["list", "bingo", "bingo teams"]
for i, c in enumerate(cmds, start=10):
    print("--- " + c)
    print(cmd(c, i)[:1500])
s.close()
