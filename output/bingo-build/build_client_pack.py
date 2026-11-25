#!/usr/bin/env python3
"""Build the HMCL/PCL2-importable Modrinth-format client ZIP for BINGO 26.3.

Inputs (relative to this script):
  manifest.json  - Modrinth version metadata fetched from the official API
  mods/*.jar     - downloaded and hash-verified mod jars

Output:
  ../BINGO-26.3-HMCL-PCL2.zip   (modrinth.index.json + overrides/)

The index references official cdn.modrinth.com URLs with sha1+sha512 so
launchers can verify downloads; overrides carry zh_cn language, the server
entry (servers.dat) and a short README. No secrets are included.
"""
import hashlib
import json
import os
import struct
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "BINGO-26.3-HMCL-PCL2.zip")
SERVER_IP = "47.120.61.237"
SERVER_PORT = 25565

# client-only performance/visual mods must NOT go to the dedicated server
CLIENT_ONLY = {"sodium"}


def nbt_string(s):
    b = s.encode("utf-8")
    return struct.pack(">BH", 8, len(b)) + b


def nbt_byte(v):
    return struct.pack(">Bb", 1, v)


def nbt_compound_end():
    return b"\x00"


def named(tag, name):
    """Tag header: 1-byte type + name length + name bytes."""
    b = name.encode("utf-8")
    return struct.pack(">BH", tag, len(b)) + b


def build_servers_dat():
    """Uncompressed big-endian NBT for Minecraft's servers.dat.

    Structure (verified byte-by-byte):
      TAG_Compound("") {
        TAG_List("servers") of TAG_Compound, length 1 [
          { TAG_String ip, TAG_String name, TAG_Byte hidden }
        ]
      }
    List elements are anonymous: no type/name header, just the payload.
    """
    entry = b""
    entry += named(8, "ip") + payload_string("%s:%d" % (SERVER_IP, SERVER_PORT))
    entry += named(8, "name") + payload_string("BINGO 26.3")
    entry += named(1, "hidden") + b"\x00"
    entry += b"\x00"                       # end of element compound
    servers = named(10, "servers") + struct.pack(">Bi", 10, 1) + entry
    root = named(10, "") + servers + b"\x00"   # end of root compound
    return root


def payload_string(s):
    b = s.encode("utf-8")
    return struct.pack(">H", len(b)) + b


def verify_servers_dat(d):
    """Parse the NBT back and assert the server entry survives a round trip."""
    pos = [0]

    def u8():
        v = d[pos[0]]
        pos[0] += 1
        return v

    def u16():
        v = struct.unpack(">H", d[pos[0]:pos[0] + 2])[0]
        pos[0] += 2
        return v

    def i32():
        v = struct.unpack(">i", d[pos[0]:pos[0] + 4])[0]
        pos[0] += 4
        return v

    def string():
        n = u16()
        v = d[pos[0]:pos[0] + n].decode("utf-8")
        pos[0] += n
        return v

    assert u8() == 10, "root must be TAG_Compound"
    assert string() == "", "root name must be empty"
    assert u8() == 10, "servers must be TAG_List"
    assert string() == "servers"
    assert u8() == 10, "list elements must be TAG_Compound"
    count = i32()
    assert count == 1, count
    entries = []
    for _ in range(count):
        fields = {}
        while True:
            t = u8()
            if t == 0:
                break
            nm = string()
            if t == 8:
                fields[nm] = string()
            elif t == 1:
                fields[nm] = u8()
            else:
                raise AssertionError("unexpected tag %d" % t)
        entries.append(fields)
    assert u8() == 0, "root not closed"
    assert pos[0] == len(d), (pos[0], len(d))
    assert entries[0]["ip"] == "%s:%d" % (SERVER_IP, SERVER_PORT), entries
    return entries


def main():
    manifest = json.load(open(os.path.join(HERE, "manifest.json"), encoding="utf-8-sig"))
    files = []
    for m in manifest:
        jar = os.path.join(HERE, "mods", m["file"])
        data = open(jar, "rb").read()
        sha1 = hashlib.sha1(data).hexdigest()
        sha512 = hashlib.sha512(data).hexdigest()
        assert sha1 == m["sha1"] and sha512 == m["sha512"], m["file"]
        env = {"client": "required", "server": "required"}
        # sodium is client-side only
        if "sodium" in m["file"]:
            env = {"client": "required", "server": "unsupported"}
        files.append({
            "path": "mods/" + m["file"],
            "hashes": {"sha1": sha1, "sha512": sha512},
            "env": env,
            "downloads": [m["url"]],
            "fileSize": m["size"],
        })
    index = {
        "formatVersion": 1,
        "game": "minecraft",
        "versionId": "1.0.0",
        "name": "BINGO 26.3 (Yet Another Bingo)",
        "summary": "轻量 BINGO 竞技/合作服客户端：Yet Another Bingo + 队伍语音 + 性能优化 + REI 配方查询，简体中文。",
        "files": files,
        "dependencies": {"minecraft": "26.3", "fabric-loader": "0.20.1"},
    }

    # Key ids verified from voicechat's KeyEvents class: plain "key.push_to_talk".
    options = (
        "lang:zh_cn\n"
        "resourcePacks:[]\n"
        "incompatibleResourcePacks:[]\n"
        "guiScale:0\n"
        "renderDistance:10\n"
        "simulationDistance:8\n"
        "maxFps:120\n"
        "enableVsync:true\n"
        "soundCategory_master:1.0\n"
        "soundCategory_record:1.0\n"
        "key_key.push_to_talk:key.keyboard.v\n"
        "key_key.voice_chat:key.keyboard.g\n"
        "key_key.voice_chat_settings:key.keyboard.unknown\n"
        "key_key.voice_chat_group:key.keyboard.unknown\n"
    )
    readme = (
        "BINGO 26.3 客户端整合包（HMCL / PCL2）\n"
        "=====================================\n"
        "【导入】启动器 → 版本列表/安装整合包 → 选择本 ZIP → 等待自动安装。\n"
        "启动器会联网下载 Minecraft 26.3、Fabric Loader 0.20.1 与全部模组。\n"
        "需要 Java 25（26.3 官方要求），启动器一般会自动下载。\n"
        "\n"
        "【网络不佳的兜底】本 ZIP 内 overrides/mods-offline/ 已附带全部 10 个模组。\n"
        "若启动器下载失败，把它们复制进该版本的 mods 文件夹即可。\n"
        "\n"
        "【服务器】已预置 47.120.61.237:25565，多人游戏列表可见。\n"
        "离线登录：直接在启动器里填一个昵称即可进服（无需正版账号）。\n"
        "\n"
        "【语音】按 V 说话（长按），按 G 打开语音界面。\n"
        "语音走 UDP 24454，若听不到声音请检查本地防火墙/路由器是否放行 UDP。\n"
        "\n"
        "【玩法】全员同队合作，共享一张宾果卡，横/竖/斜连成一条线即通关。\n"
        "详细说明见随附《BINGO-26.3-玩家手册.md》。\n"
    )

    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("modrinth.index.json", json.dumps(index, ensure_ascii=False, indent=2))
        z.writestr("overrides/options.txt", options)
        z.writestr("overrides/servers.dat", build_servers_dat())
        z.writestr("overrides/README.txt", readme)
        # Offline fallback: ship the verified jars so a blocked CDN never
        # prevents installation. Kept out of mods/ so launchers don't double-load.
        for m in manifest:
            jar = os.path.join(HERE, "mods", m["file"])
            z.write(jar, "overrides/mods-offline/" + m["file"])

    # verify roundtrip
    with zipfile.ZipFile(OUT) as z:
        bad = z.testzip()
        assert bad is None, bad
        idx = json.loads(z.read("modrinth.index.json"))
        assert idx["dependencies"]["minecraft"] == "26.3"
        assert len(idx["files"]) == len(manifest)
        names = z.namelist()
        for need in ("overrides/options.txt", "overrides/servers.dat", "overrides/README.txt"):
            assert need in names, need
        offline = [n for n in names if n.startswith("overrides/mods-offline/")]
        assert len(offline) == len(manifest), offline
        # every bundled jar must match the index hashes byte-for-byte
        for m in manifest:
            data = z.read("overrides/mods-offline/" + m["file"])
            assert hashlib.sha1(data).hexdigest() == m["sha1"], m["file"]
            assert hashlib.sha512(data).hexdigest() == m["sha512"], m["file"]
        assert b"key.push_to_talk" in z.read("overrides/options.txt")
        verify_servers_dat(z.read("overrides/servers.dat"))
    print("PACK_OK", os.path.abspath(OUT), os.path.getsize(OUT), "bytes,",
          len(files), "mod entries,", len(manifest), "offline jars verified")


if __name__ == "__main__":
    main()
