#!/usr/bin/env python3
"""Final co-op acceptance: 2 offline players, auto same team, shared card,
one voice group, game start. Runs ON the ECS.
"""
import socket
import struct
import sys
import threading
import time

sys.path.insert(0, "/tmp")
from mc_client import Client

PW = [l.strip().split("=", 1)[1] for l in open("/opt/bingo/server.properties")
      if l.startswith("rcon.password=")][0]


class Rcon(object):
    def __init__(self):
        self.s = socket.create_connection(("127.0.0.1", 25575), timeout=15)
        self.s.settimeout(4)
        self.rid = 500
        self._p(1, 3, PW)
        while True:
            rid, typ, _ = self._r()
            if typ == 2:
                assert rid == 1
                break

    def _p(self, rid, typ, body):
        d = struct.pack("<ii", rid, typ) + body.encode("utf-8") + b"\x00\x00"
        self.s.sendall(struct.pack("<i", len(d)) + d)

    def _r(self):
        h = b""
        while len(h) < 4:
            h += self.s.recv(4 - len(h))
        n = struct.unpack("<i", h)[0]
        b = b""
        while len(b) < n:
            b += self.s.recv(n - len(b))
        rid, typ = struct.unpack("<ii", b[:8])
        return rid, typ, b[8:-2].decode("utf-8", "replace")

    def cmd(self, c):
        self.rid += 1
        rid = self.rid
        self._p(rid, 2, c)
        time.sleep(1.0)
        out = []
        while True:
            try:
                r, t, b = self._r()
            except socket.timeout:
                break
            if b:
                out.append(b)
            if r == rid and t == 0:
                break
        return " | ".join(out)


rc = Rcon()
clients = []


def run(name, secs):
    c = Client(name)
    c.login()
    ok = c.configure()
    clients.append(c)
    print("[%s] online=%s" % (name, ok))
    c.pump(secs)


ts = []
for n in ("CoopOne", "CoopTwo"):
    t = threading.Thread(target=run, args=(n, 120))
    t.daemon = True
    t.start()
    ts.append(t)
    time.sleep(8)

time.sleep(14)
print("PLAYERS:", rc.cmd("list"))
print("TEAMS:", rc.cmd("team list"))
print("BINGO:", rc.cmd("bingo"))
print("START:", rc.cmd("bingo start"))
time.sleep(30)
print("TEAMS_AFTER:", rc.cmd("team list"))
print("PLAYERS_AFTER:", rc.cmd("list"))
print("BINGO_AFTER:", rc.cmd("bingo"))
for c in clients:
    c.alive = False
time.sleep(2)
print("COOP_VERIFY_DONE")
