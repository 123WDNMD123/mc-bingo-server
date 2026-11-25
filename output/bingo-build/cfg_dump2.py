#!/usr/bin/env python3
"""Observe configuration phase WITHOUT sending client information first."""
import sys
import time

sys.path.insert(0, "/tmp")
from mc_client import Client, vi, sv

c = Client(sys.argv[1] if len(sys.argv) > 1 else "ProbeBob")
print("LOGIN_OK", c.login())
c.sock.settimeout(2.0)
end = time.time() + 30
while time.time() < end:
    try:
        pid, r = c.recv()
    except Exception as exc:
        print("read end:", type(exc).__name__)
        continue
    txt = "".join(chr(b) if 32 <= b < 127 else "." for b in r.d[:100])
    print("cfg 0x%02x len=%d | %s" % (pid, len(r.d), txt))
    if pid == 0x05:
        # ping: echo 4-byte payload back
        c.send(0x05, r.rest())
        print("   -> pong sent")
    elif pid == 0x0E:
        c.send(0x07, vi(0))
        print("   -> known packs: none")
    elif pid == 0x03:
        c.send(0x03)
        print("   -> finish ack, PLAY")
        break
c.sock.close()
