#!/usr/bin/env python3
"""Dump raw configuration-phase packets to identify ids empirically."""
import sys
import time

sys.path.insert(0, "/tmp")
from mc_client import Client

c = Client(sys.argv[1] if len(sys.argv) > 1 else "ProbeAlice")
print("LOGIN_OK", c.login())
c.client_info()
end = time.time() + 20
while time.time() < end:
    try:
        pid, r = c.recv()
    except Exception as exc:
        print("end:", exc)
        break
    print("cfg 0x%02x len=%d" % (pid, len(r.d)))
    print("   hex:", r.d[:80].hex())
    try:
        printable = "".join(chr(b) if 32 <= b < 127 else "." for b in r.d[:120])
        print("   txt:", printable)
    except Exception:
        pass
c.sock.close()
