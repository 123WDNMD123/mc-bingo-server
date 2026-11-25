#!/usr/bin/env python3
"""Download + verify the 9 mod jars on the ECS from cdn.modrinth.com.

Reads manifest.json (official Modrinth version metadata) next to this script.
Verifies size + sha1 + sha512 for every file. Skips client-only sodium on server.
"""
import hashlib
import json
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
MODS = os.path.join(HERE, "mods")
os.makedirs(MODS, exist_ok=True)


def sha(path, algo):
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    manifest = json.load(open(os.path.join(HERE, "manifest.json"), encoding="utf-8-sig"))
    for m in manifest:
        # sodium is client-only; do not place on dedicated server
        if "sodium" in m["file"]:
            print("SKIP_CLIENT_ONLY", m["file"])
            continue
        dest = os.path.join(MODS, m["file"])
        req = urllib.request.Request(m["url"], headers={"User-Agent": "MC-Server deployment"})
        with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as out:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                out.write(chunk)
        size = os.path.getsize(dest)
        s1 = sha(dest, "sha1")
        s5 = sha(dest, "sha512")
        ok = size == m["size"] and s1 == m["sha1"] and s5 == m["sha512"]
        if not ok:
            raise SystemExit("HASH MISMATCH " + m["file"])
        print("OK", m["file"], size, "sha1+sha512")
    print("MODS_FETCH_DONE", len(os.listdir(MODS)), "files")


if __name__ == "__main__":
    main()
