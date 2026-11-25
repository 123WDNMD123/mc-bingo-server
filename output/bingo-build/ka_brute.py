#!/usr/bin/env python3
"""Find the correct serverbound keepalive id by parallel elimination.

Each candidate id gets its own connection/process; after 45s we ask the server
which players are still online. The survivor's id is the real keepalive.
"""
import sys
import time

sys.path.insert(0, "/tmp")
from mc_client import Client

kid = int(sys.argv[1], 16)
name = "KA%02X" % kid
c = Client(name)
c.login()
c.configure()
c.sock.settimeout(20)
end = time.time() + 50
n = 0
while time.time() < end:
    try:
        pid, r = c.recv()
    except Exception:
        continue
    if pid == 0x4D:
        c.send(kid, r.take(8))
        n += 1
    elif pid == 0x20:
        break
print("%s sent=%d" % (name, n), flush=True)
