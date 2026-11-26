#!/usr/bin/env python3
"""Read the operator permission level the SERVER pushes to the client.

Vanilla sends an Entity Event with id = 24 + permissionLevel (24..28) for the
player's own entity when op status is applied. Payload is int entityId + byte
eventId = 5 bytes, a very distinctive shape. This proves the permission is
live in the session, without needing to send any command packet.

Usage: python3 op_level_probe.py Nashville SomeNonOpName
"""
import struct
import sys
import time

sys.path.insert(0, "/tmp")
from mc_client import Client


def probe(name):
    c = Client(name)
    c.login()
    if not c.configure():
        print("[%s] CONFIG_FAIL" % name, flush=True)
        return
    c.sock.settimeout(20)
    events = []
    small = []
    end = time.time() + 14
    while time.time() < end:
        try:
            pid, r = c.recv()
        except Exception:
            continue
        # r.d holds the WHOLE packet including the id varint; r.rest() is the
        # payload after the id. Using len(r.d) mis-sizes every payload.
        data = r.rest()
        if pid == 0x4D:
            c.send(0x16, r.take(8))
            continue
        if pid == 0x20:
            print("[%s] disconnect" % name, flush=True)
            break
        if len(data) == 5:
            eid, ev = struct.unpack(">iB", data)
            small.append((hex(pid), eid, ev))
            if 24 <= ev <= 28:
                events.append((hex(pid), eid, ev - 24))
    print("[%s] OP_LEVEL_EVENTS=%s" % (name, events), flush=True)
    print("[%s] five_byte_packets=%s" % (name, small[:12]), flush=True)


for n in sys.argv[1:]:
    probe(n)
    time.sleep(1)
print("PROBE_DONE", flush=True)