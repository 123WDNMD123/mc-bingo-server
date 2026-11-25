#!/usr/bin/env python3
"""Stay online as one player, answering keepalives promptly.

Run as a separate PROCESS per player (threads shared the GIL and missed
keepalive deadlines). Prints a heartbeat so the driver can confirm presence.
"""
import sys
import time

sys.path.insert(0, "/tmp")
from mc_client import Client

name = sys.argv[1]
secs = float(sys.argv[2]) if len(sys.argv) > 2 else 120
c = Client(name)
c.login()
print("[%s] CONFIG=%s" % (name, c.configure()), flush=True)
# Timeout must exceed a whole packet read: a short timeout can interrupt a
# frame mid-read and desync the stream, which silently kills keepalives.
c.sock.settimeout(20)
end = time.time() + secs
ka = 0
while time.time() < end:
    try:
        pid, r = c.recv()
    except Exception:
        continue
    if pid == 0x4D:
        c.send(0x16, r.take(8))
        ka += 1
    elif pid == 0x20:
        print("[%s] DISCONNECT %r" % (name, r.d[:100]), flush=True)
        break
print("[%s] END keepalives=%d" % (name, ka), flush=True)
