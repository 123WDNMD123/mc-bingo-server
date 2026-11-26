#!/usr/bin/env python3
"""Offline-mode Minecraft 26.3 client (protocol 777) for acceptance testing.

Handles login -> compression -> configuration -> play, keeps the connection
alive with keepalives, and can run chat commands. Used to prove real player
login, co-op team assignment and voice group behaviour on the BINGO server.

Python 3.6 compatible (runs on the ECS).
"""
import hashlib
import socket
import struct
import sys
import threading
import time
import uuid
import zlib


def offline_uuid(name):
    """Java's UUID.nameUUIDFromBytes("OfflinePlayer:"+name) -- plain MD5.

    NOT uuid3(NAMESPACE_DNS, ...): that prepends the DNS namespace bytes and
    yields a completely different id. Verified against real logins on this
    server (CoopOne/CoopTwo/Alice/Bob all matched). Case sensitive.
    In offline mode the server recomputes this itself and ignores whatever
    the client sends, but keeping it correct avoids misleading probes.
    """
    b = bytearray(hashlib.md5(("OfflinePlayer:" + name).encode("utf-8")).digest())
    b[6] = (b[6] & 0x0F) | 0x30
    b[8] = (b[8] & 0x3F) | 0x80
    return uuid.UUID(bytes=bytes(b))


def vi(n):
    out = b""
    while True:
        b = n & 0x7F
        n >>= 7
        out += bytes([b | (0x80 if n else 0)])
        if not n:
            return out


def sv(text):
    b = text.encode("utf-8")
    return vi(len(b)) + b


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

    def take(self, n):
        v = self.d[self.i:self.i + n]
        self.i += n
        return v

    def rest(self):
        return self.d[self.i:]


class Client(object):
    def __init__(self, name, host="127.0.0.1", port=25565):
        self.name = name
        self.threshold = -1
        self.sock = socket.create_connection((host, port), timeout=20)
        self.sock.settimeout(1.0)
        self.buf = b""
        self.lock = threading.Lock()
        self.play = False
        self.chat = []
        self.alive = True
        self.packets = {}

    def _read(self, n):
        while len(self.buf) < n:
            c = self.sock.recv(65536)
            if not c:
                raise IOError("eof")
            self.buf += c
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def _read_vi(self):
        n = 0
        sh = 0
        while True:
            b = self._read(1)[0]
            n |= (b & 0x7F) << sh
            sh += 7
            if not b & 0x80:
                return n

    def send(self, pid, payload=b""):
        body = vi(pid) + payload
        if self.threshold < 0:
            frame = vi(len(body)) + body
        elif len(body) >= self.threshold:
            frame = vi(len(vi(len(body)) + zlib.compress(body))) + vi(len(body)) + zlib.compress(body)
        else:
            inner = vi(0) + body
            frame = vi(len(inner)) + inner
        with self.lock:
            self.sock.sendall(frame)

    def recv(self):
        ln = self._read_vi()
        data = self._read(ln)
        if self.threshold >= 0:
            r0 = Reader(data)
            dlen = r0.vi()
            rest = r0.rest()
            data = zlib.decompress(rest) if dlen else rest
        r = Reader(data)
        return r.vi(), r

    def login(self):
        hs = vi(777) + sv("127.0.0.1") + struct.pack(">H", 25565) + vi(2)
        self.send(0x00, hs)
        uid = offline_uuid(self.name)
        self.uuid = uid
        self.send(0x00, sv(self.name) + uid.bytes)
        while True:
            pid, r = self.recv()
            if pid == 0x03:
                self.threshold = r.vi()
            elif pid == 0x00:
                raise RuntimeError("disconnect: %r" % r.d[:200])
            elif pid == 0x02:
                break
        self.send(0x03)  # login acknowledged
        return uid

    def client_info(self):
        payload = (sv("zh_cn") + struct.pack(">b", 10) + vi(0) + b"\x01"
                   + struct.pack(">B", 0x7F) + vi(1) + b"\x00" + b"\x01" + vi(0))
        self.send(0x00, payload)

    def configure(self, verbose=False):
        """Answer configuration phase.

        Ids verified empirically on 26.3 / protocol 777:
          0x01 custom payload (brand / register channels)
          0x04 keep alive        -> echo 8 bytes on 0x04
          0x05 ping              -> echo payload on 0x05
          0x0d feature flags
          0x0f known packs       -> reply serverbound 0x07 with pack count
          0x03 finish configuration -> ack 0x03, then play
        """
        self.client_info()
        deadline = time.time() + 60
        while time.time() < deadline:
            try:
                pid, r = self.recv()
            except socket.timeout:
                continue
            self.packets[pid] = self.packets.get(pid, 0) + 1
            if verbose:
                print("[%s] cfg 0x%02x len=%d" % (self.name, pid, len(r.d)))
            if pid == 0x05:
                self.send(0x05, r.rest())
            elif pid == 0x04:
                self.send(0x04, r.rest())
            elif pid == 0x0f:
                # declare every offered pack as known so registry sync is skipped
                rr = Reader(r.rest())
                n = rr.vi()
                packs = []
                for _ in range(n):
                    ns = rr.string()
                    ident = rr.string()
                    ver = rr.string()
                    packs.append((ns, ident, ver))
                body = vi(len(packs))
                for ns, ident, ver in packs:
                    body += sv(ns) + sv(ident) + sv(ver)
                self.send(0x07, body)
                if verbose:
                    print("[%s] known packs acked: %d" % (self.name, len(packs)))
            elif pid == 0x03:
                self.send(0x03)
                self.play = True
                return True
            elif pid == 0x02:
                raise RuntimeError("cfg disconnect %r" % r.d[:200])
        return False

    def pump(self, seconds, commands=None, verbose=False):
        """Stay online, answer keepalives, collect chat, optionally run commands."""
        end = time.time() + seconds
        sent = False
        while time.time() < end and self.alive:
            try:
                pid, r = self.recv()
            except socket.timeout:
                continue
            except Exception as exc:
                print("[%s] pump end: %s" % (self.name, exc))
                break
            self.packets[pid] = self.packets.get(pid, 0) + 1
            # Verified on 26.3/777: play keepalive = 0x4d (8-byte payload).
            # 0x00 with empty payload is a bundle delimiter, NOT a disconnect.
            if pid == 0x4D:
                self.send(0x16, r.take(8))
            elif pid == 0x20:    # disconnect (play)
                print("[%s] DISCONNECT %r" % (self.name, r.d[:200]))
                break
            elif pid in (0x73, 0x6C, 0x67):  # system chat candidates
                try:
                    txt = r.string()
                    self.chat.append(txt)
                    if verbose:
                        print("[%s] chat %s" % (self.name, txt[:160]))
                except Exception:
                    pass
            if commands and not sent and time.time() > end - seconds + 6:
                for c in commands:
                    self.send(0x05, sv(c) + struct.pack(">q", int(time.time() * 1000))
                              + struct.pack(">Q", 0) + vi(0) + vi(0) + b"\x00")
                    time.sleep(1.5)
                sent = True
        return self.chat


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "ProbeAlice"
    secs = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    cmds = sys.argv[3:]
    c = Client(name)
    print("LOGIN_OK", name, c.login())
    print("CONFIG_DONE", c.configure(verbose=True))
    print("PLAY", c.play)
    c.pump(secs, cmds, verbose=True)
    print("PACKETS", sorted((hex(k), v) for k, v in c.packets.items()))
