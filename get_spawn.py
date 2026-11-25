import os
import paramiko, struct

HOST = "47.120.61.237"
USER = "root"
PWD = os.environ.get("MC_SSH_PASSWORD")
if not PWD:
    raise SystemExit("set MC_SSH_PASSWORD environment variable first")
NBT_SCRIPT = r'''
import gzip, struct

class R:
    def __init__(self, d): self.d = d; self.p = 0
    def rd(self, n):
        b = self.d[self.p:self.p+n]; self.p += n; return b
    def u8(self): return self.rd(1)[0]
    def u16(self): return struct.unpack(">H", self.rd(2))[0]
    def i32(self): return struct.unpack(">i", self.rd(4))[0]
    def i64(self): return struct.unpack(">q", self.rd(8))[0]

def payload(r, t):
    if t == 1: return r.rd(1)[0]
    if t == 2: return struct.unpack(">h", r.rd(2))[0]
    if t == 3: return r.i32()
    if t == 4: return r.i64()
    if t == 5: return struct.unpack(">f", r.rd(4))[0]
    if t == 6: return struct.unpack(">d", r.rd(8))[0]
    if t == 7: return r.rd(r.i32())
    if t == 8: return r.rd(r.u16()).decode("utf-8", "replace")
    if t == 9:
        et = r.u8(); n = r.i32()
        return [payload(r, et) for _ in range(n)]
    if t == 10:
        d = {}
        while True:
            ct = r.u8()
            if ct == 0: break
            nl = r.u16(); name = r.rd(nl).decode("utf-8", "replace")
            d[name] = payload(r, ct)
        return d
    if t == 11: return [r.i32() for _ in range(r.i32())]
    if t == 12: return [r.i64() for _ in range(r.i32())]
    return None

with gzip.open("/opt/mc/world/level.dat", "rb") as f:
    raw = f.read()
r = R(raw)
t = r.u8(); nl = r.u16(); r.rd(nl)  # root name
root = payload(r, t)
print("ROOT KEYS:", list(root.keys()))
data = root.get("Data", {})
print("DATA KEYS:", list(data.keys()))
for k in ("SpawnX", "SpawnY", "SpawnZ", "SpawnAngle", "spawn", "paperSpawnDimension"):
    print(k, "=", data.get(k))
'''


def main():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=PWD, timeout=20)
    stdin, stdout, stderr = c.exec_command("python3")
    stdin.write(NBT_SCRIPT)
    stdin.channel.shutdown_write()
    print(stdout.read().decode("utf-8", "replace"))
    print(stderr.read().decode("utf-8", "replace"))
    c.close()


if __name__ == "__main__":
    main()
