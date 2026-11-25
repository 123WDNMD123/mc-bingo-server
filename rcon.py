#!/usr/bin/env python3
"""零依赖 Minecraft RCON 客户端（替代丢失的 /tmp/rcon.py）。

用法:
    python3 rcon.py 127.0.0.1 25575 <password> "command1" ["command2" ...]

协议: Source RCON（小端序）——认证(AUTH=3) → 命令(EXEC=2)。
零第三方依赖，仅标准库，任何解释器（远端 3.6.8 与本地 3.13）皆可运行。
"""
import socket
import struct
import sys


def pack(pkt_id, pkt_type, body=b""):
    body = body.encode("utf-8", "replace") if isinstance(body, str) else body
    return struct.pack("<iii", 10 + len(body), pkt_id, pkt_type) + body + b"\x00\x00"


def unpack(data):
    # RCON 响应布局: int32 length | int32 id | int32 type | body | \x00\x00
    # 必须读 [8:12] 才是 type；此前误把 id 当 type 导致假"认证失败"。
    if len(data) >= 12:
        return struct.unpack("<iii", data[:12])
    return (0, 0, 0)


def rcon(host, port, password, cmd):
    s = socket.create_connection((host, port), timeout=10)
    s.settimeout(10)
    try:
        # 认证
        s.sendall(pack(1, 3, password))
        resp = s.recv(4096)
        if len(resp) < 12:
            raise RuntimeError("认证无响应: %r" % resp)
        _len, _pid, rtype = unpack(resp)
        if rtype != 2:
            raise RuntimeError("RCON 认证失败（密码错误？）: resp=%r" % resp[:16])
        # 命令
        s.sendall(pack(2, 2, cmd))
        out = []
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            out.append(chunk)
            if len(chunk) < 65536:
                break
        data = b"".join(out)
        if len(data) >= 12:
            _len2, _pid2, rtype2 = unpack(data)
            if rtype2 == 0:          # RESPONSE_VALUE：body 从 12 到倒数第二个 0x00
                return data[12:].rstrip(b"\x00").decode("utf-8", "replace")
        return data.decode("utf-8", "replace")
    finally:
        s.close()


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    host, port, password = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    cmds = sys.argv[4:]
    # 一个连接执行多条命令；失败则逐条重试一次
    results = []
    try:
        for c in cmds:
            results.append(rcon(host, port, password, c))
    except Exception as e:
        results = [rcon(host, port, password, c) for c in cmds]
    for r in results:
        sys.stdout.write(r.rstrip("\n") + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())