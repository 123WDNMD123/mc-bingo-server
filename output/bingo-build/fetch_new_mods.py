#!/usr/bin/env python3
"""Download and verify the v1.1.0 additions: SkinRestorer + VeinMiner.

Queries Modrinth for the exact 26.3 / fabric build, downloads it, and checks
size + SHA-1 + SHA-512 against the official values before anything is shipped.

Side requirements recorded from the Modrinth project metadata:
  skinrestorer : client_side=unsupported, server_side=required
                 -> SERVER ONLY. Must never be placed in the client pack.
  veinminer    : client_side=optional,    server_side=required
                 -> server required; client optional (we include it).
                 Hard deps: fabric-language-kotlin, fabric-api (both present).
"""
import hashlib
import json
import os
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
MODS = os.path.join(HERE, "mods")
API = "https://api.modrinth.com/v2"

TARGETS = [
    # slug, project_id, expected client behaviour in the pack
    ("skinrestorer", "ghrZDhGW", "server_only"),
    ("veinminer", "OhduvhIc", "both"),
]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "mc-bingo-build/1.1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    out = []
    for slug, pid, pack_role in TARGETS:
        q = urllib.parse.urlencode({
            "game_versions": json.dumps(["26.3"]),
            "loaders": json.dumps(["fabric"]),
        })
        vers = get("%s/project/%s/version?%s" % (API, slug, q))
        assert vers, "no 26.3 fabric build for " + slug
        v = vers[0]
        f = next((x for x in v["files"] if x.get("primary")), v["files"][0])
        dest = os.path.join(MODS, f["filename"])

        req = urllib.request.Request(f["url"], headers={"User-Agent": "mc-bingo-build/1.1.0"})
        with urllib.request.urlopen(req, timeout=300) as r:
            data = r.read()
        with open(dest, "wb") as fh:
            fh.write(data)

        sha1 = hashlib.sha1(data).hexdigest()
        sha512 = hashlib.sha512(data).hexdigest()
        ok_size = len(data) == f["size"]
        ok1 = sha1 == f["hashes"]["sha1"]
        ok5 = sha512 == f["hashes"]["sha512"]
        print("%-14s %-45s size=%d %s sha1=%s sha512=%s" % (
            slug, f["filename"], len(data),
            "OK" if ok_size else "BAD",
            "OK" if ok1 else "BAD",
            "OK" if ok5 else "BAD"))
        assert ok_size and ok1 and ok5, "hash mismatch for " + slug

        out.append({
            "id": v["id"],
            "project": pid,
            "name": "%s %s" % (slug, v["version_number"]),
            "version": v["version_number"],
            "file": f["filename"],
            "url": f["url"],
            "size": len(data),
            "sha1": sha1,
            "sha512": sha512,
            "pack_role": pack_role,
            "dependencies": v["dependencies"],
        })

    with open(os.path.join(HERE, "new_mods.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=4)
    print("NEW_MODS_VERIFIED", len(out))


if __name__ == "__main__":
    main()