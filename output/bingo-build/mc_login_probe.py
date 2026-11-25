#!/usr/bin/env python3
"""Minimal offline-mode Minecraft client used to verify real player login.

Runs ON the ECS against 127.0.0.1:25565. Dumps the login + configuration
exchange so packet ids can be discovered empirically (protocol 777 / 26.3).
"""
import socket
import struct
import sys
import time
import uuid
import zlib

THRESHOLD = -1  # set when server sends Set Compression


def vi(n):
    out = b""
    while True:
        b = n & 0x7F
        n >>= 7
        out += bytes([b | (0x80 if n else 0)])
        if not n:
            return out


def read_vi(sock):
    n = 0
    sh = 0
    while True:
        b = sock.recv(1)
        if not b:
            raise IOError("eof")
        b = b[0]
        n |= (b & 0x7F) << sh
        sh += 7
        if not b & 0x80:
            return n


def read_n(sock, n):
    buf = b""
    while len(buf) < n:
        c = sock.recv(n - len(buf))
        if not c:
            raise IOError("eof")
        buf += c
    return buf


def s(text):
    b = text.encode("utf-8")
    return vi(len(b)) + b


def pkt(pid, payload=b""):
    body = vi(pid) + payload
    if THRESHOLD < 0:
        return vi(len(body)) + body
    if len(body) >= THRESHOLD:
        comp = zlib.compress(body)
        inner = vi(len(body)) + comp
    else:
        inner = vi(0) + body
    return vi(len(inner)) + inner


class Reader(object):
    def __init__(self, data):
        self.d = data
        self.i = 0

    def vi(self):
        n = 0
        sh = 0
        while True:
            b = self.d[self.i]
            self.i += 1
            n |= (b & 0x7F) << sh
            sh += 7
            if not b & 0x80:
                return n

    def string(self):
        n = self.vi()
        v = self.d[self.i:self.i + n].decode("utf-8", "replace")
        self.i += n
        return v

    def rest(self):
        return self.d[self.i:]


HOST = "127.0.0.1"
PORT = 25565
NAME = sys.argv[1] if len(sys.argv) > 1 else "ProbeAlice"

sock = socket.create_connection((HOST, PORT), timeout=20)
sock.settimeout(8)

hs = vi(777) + s(HOST) + struct.pack(">H", PORT) + vi(2)
sock.sendall(pkt(0x00, hs))
# Login Start: name + uuid (1.20.5+)
uid = uuid.uuid3(uuid.NAMESPACE_DNS, "OfflinePlayer:" + NAME)
sock.sendall(pkt(0x00, s(NAME) + uid.bytes))


def recv_pkt():
    ln = read_vi(sock)
    data = read_n(sock, ln)
    if THRESHOLD >= 0:
        r0 = Reader(data)
        dlen = r0.vi()
        rest = r0.rest()
        data = zlib.decompress(rest) if dlen else rest
    r = Reader(data)
    pid = r.vi()
    return pid, r


print("== login phase ==")
for _ in range(10):
    pid, r = recv_pkt()
    print("login pkt 0x%02x len=%d" % (pid, len(r.d)))
    if pid == 0x03:  # set compression
        THRESHOLD = r.vi()
        print("COMPRESSION_THRESHOLD", THRESHOLD)
        continue
    if pid == 0x00:  # disconnect
        print("DISCONNECT_RAW", r.d[:300])
        sys.exit(1)
    if pid == 0x02:  # login success
        print("LOGIN_SUCCESS head", r.d[:40].hex())
        break

sock.sendall(pkt(0x03))  # login acknowledged
print("== configuration phase ==")
seen = []
deadline = time.time() + 25
while time.time() < deadline:
    try:
        pid, r = recv_pkt()
    except socket.timeout:
        break
    seen.append(pid)
    print("cfg pkt 0x%02x len=%d head=%s" % (pid, len(r.d), r.d[:24].hex()))
print("CFG_IDS", [hex(x) for x in seen])
sock.close()
