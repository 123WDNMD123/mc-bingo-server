#!/usr/bin/env python3
"""Relay server-side mods to /opt/bingo/mods via OSS, verifying sha1+sha512.

sodium is client-only and is intentionally excluded from the server.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from aliyun_api import run_shell
from oss_relay import put, signed_url, delete

mods = json.load(open(os.path.join(HERE, "manifest.json"), encoding="utf-8-sig"))
server_mods = [m for m in mods if "sodium" not in m["file"]]
print("server mods:", len(server_mods), "of", len(mods))

run_shell("mkdir -p /opt/bingo/mods && rm -f /opt/bingo/mods/*.jar.part", timeout=60)

uploaded = []
for m in server_mods:
    local = os.path.join(HERE, "mods", m["file"])
    raw = open(local, "rb").read()
    assert len(raw) == m["size"], (m["file"], len(raw), m["size"])
    assert hashlib.sha1(raw).hexdigest() == m["sha1"], m["file"]
    key, n = put(local)
    uploaded.append(key)
    print("UPLOADED", m["file"], n, flush=True)

# Fetch everything on the ECS in one invocation, then verify hashes.
lines = ["set -e", "cd /opt/bingo/mods"]
for m in server_mods:
    url = signed_url("mc-bingo-relay-20261125/" + m["file"], ttl=3600)
    lines.append('curl -sSL --retry 3 --max-time 600 -o "%s" "%s"' % (m["file"], url))
lines.append("echo == sha1 ==")
lines.append("sha1sum *.jar")
lines.append("echo == sha512 ==")
lines.append("sha512sum *.jar")
lines.append("echo == sizes ==")
lines.append("stat -c '%s %n' *.jar")
res = run_shell("\n".join(lines), timeout=900)
print("FETCH", res.get("status"), res.get("exit_code"))
out = res.get("output") or json.dumps(res, ensure_ascii=False)
print(out)

if res.get("status") != "Success":
    sys.exit("fetch failed; keys kept for retry: %s" % uploaded)

expected1 = {m["file"]: m["sha1"] for m in server_mods}
expected5 = {m["file"]: m["sha512"] for m in server_mods}
got1, got5 = {}, {}
section = None
for line in out.splitlines():
    if line.startswith("== sha1"):
        section = 1
        continue
    if line.startswith("== sha512"):
        section = 5
        continue
    if line.startswith("== sizes"):
        section = None
        continue
    parts = line.split()
    if section and len(parts) == 2:
        (got1 if section == 1 else got5)[parts[1]] = parts[0]

bad = []
for m in server_mods:
    f = m["file"]
    if got1.get(f) != expected1[f] or got5.get(f) != expected5[f]:
        bad.append(f)
if bad:
    sys.exit("HASH MISMATCH: %s" % bad)
print("ALL_HASH_OK", len(server_mods))

for key in uploaded:
    print("cleanup", key, delete(key))
