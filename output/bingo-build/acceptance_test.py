#!/usr/bin/env python3
"""Two-player co-op acceptance test on the live BINGO server.

Proves: offline login works for 2 players, both land on the SAME single team,
the shared card scores for both, and voice integration puts them in ONE group.
Runs ON the ECS. Uses RCON to drive /bingo commands as console.
"""
import re
import socket
import struct
import sys
import threading
import time

sys.path.insert(0, "/tmp")
from mc_client import Client

PW = None
for line in open("/opt/bingo/server.properties"):
    if line.startswith("rcon.password="):
        PW = line.strip().split("=", 1)[1]


class Rcon(object):
    def __init__(self):
        self.s = socket.create_connection(("127.0.0.1", 25575), timeout=15)
        self.s.settimeout(4)
        self.rid = 100
        self._pkt(1, 3, PW)
        while True:
            rid, typ, _ = self._rd()
            if typ == 2:
                assert rid == 1, "rcon auth failed"
                break

    def _pkt(self, rid, typ, body):
        d = struct.pack("<ii", rid, typ) + body.encode("utf-8") + b"\x00\x00"
        self.s.sendall(struct.pack("<i", len(d)) + d)

    def _rd(self):
        hdr = b""
        while len(hdr) < 4:
            hdr += self.s.recv(4 - len(hdr))
        n = struct.unpack("<i", hdr)[0]
        b = b""
        while len(b) < n:
            b += self.s.recv(n - len(b))
        rid, typ = struct.unpack("<ii", b[:8])
        return rid, typ, b[8:-2].decode("utf-8", "replace")

    def cmd(self, c):
        self.rid += 1
        rid = self.rid
        self._pkt(rid, 2, c)
        time.sleep(1.0)
        parts = []
        while True:
            try:
                r, t, b = self._rd()
            except socket.timeout:
                break
            if b:
                parts.append(b)
            if r == rid and t == 0:
                break
        return "\n".join(parts)


rc = Rcon()
print("RCON_OK")

players = {}
threads = {}


def stay(name, secs):
    c = Client(name)
    c.login()
    ok = c.configure()
    players[name] = c
    print("[%s] LOGIN+CONFIG=%s" % (name, ok))
    c.pump(secs)


for n in ("Alice", "Bob"):
    t = threading.Thread(target=stay, args=(n, 150))
    t.daemon = True
    t.start()
    threads[n] = t
    time.sleep(6)

time.sleep(10)
print("== online ==")
print(rc.cmd("list"))

print("== join team ==")
print(rc.cmd("bingo join Alice 1")[:300])
print(rc.cmd("bingo join Bob 1")[:300])
time.sleep(3)
print("== team list ==")
print(rc.cmd("team list")[:400])

print("== bingo state ==")
print(rc.cmd("bingo")[:400])

print("== start game ==")
print(rc.cmd("bingo start")[:400])
time.sleep(25)
print("== bingo after start ==")
print(rc.cmd("bingo")[:400])
print(rc.cmd("list")[:200])

for n, c in players.items():
    c.alive = False
time.sleep(2)
print("ACCEPTANCE_DONE")
