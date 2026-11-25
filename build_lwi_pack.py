#!/usr/bin/env python3
"""组装《LuckyWorldInvasion》可分发版本包。

为什么不用"整合包格式"（Curse/Modrinth/MultiMC manifest）：
  启动器的"安装整合包"只认那几种 manifest；而 HMCL/PCL 会把
  .minecraft/versions/ 下的每个文件夹自动识别为实例。本包就是把
  「版本文件夹 + 父版本 + 内容目录 + servers.dat」原样打包，
  朋友解压进 .minecraft 即出现在实例列表，无需"导入"。

包含（内容）：
  mods(254 jar, 已移除与服务端冲突的 framework/controllable)、
  config、kubejs、defaultconfigs、addons、tacz、tlm_custom_pack、
  shaderpacks、resourcepacks、版本 JSON、icon.png、父版本 1.20.1-clean/

排除（运行时缓存/个人数据/空目录）：
  saves、logs、screenshots、options.txt、usercache、usernamecache、
  knownkeys、TrashSlotSaveState、authlib-injector.log、log4j2.xml、
  rhino.local.properties、patchouli_data.json、.hmcl、ESM、PCL、xaero、
  essential、local、modernfix、controllable_natives、natives-*、
  puresufferingmusic(空)、skyblockbuilder(空,真预设在 config/skyblockbuilder)、
  patchouli_books(空)、keybinding presets、mods-disabled
"""
import os
import shutil
import struct
import sys
import time
import zipfile

SRC = r"D:\HuaweiMoveData\Users\64146\Desktop\game\.minecraft\versions"
INST = os.path.join(SRC, "1.20.1-LuckyWorldInvasion")
CLEAN = os.path.join(SRC, "1.20.1-clean")
STAGE = r"G:\lwi-staging\pack"
ROOT = os.path.join(STAGE, "LuckyWorldInvasion-ServerPack")
OUT = r"G:\lwi-staging\LuckyWorldInvasion-ServerPack-20261108.zip"
SERVER_IP = "47.120.61.237"

CONTENT_DIRS = ["mods", "config", "kubejs", "defaultconfigs", "addons",
                "tacz", "tlm_custom_pack", "shaderpacks", "resourcepacks"]
CONTENT_FILES = ["1.20.1-LuckyWorldInvasion.json", "icon.png"]

# 已压缩过的类型用 STORE（再 deflate 只浪费时间不减小体积）
STORE_EXT = {".jar", ".zip", ".png", ".dll", ".so", ".nbt", ".mca", ".ogg", ".mp3"}


def nbt_string_payload(s):
    b = s.encode("utf-8")
    return struct.pack(">H", len(b)) + b


def nbt_child_string(name, value):
    return b"\x08" + nbt_string_payload(name) + nbt_string_payload(value)


def nbt_child_byte(name, value):
    return b"\x01" + nbt_string_payload(name) + bytes([value & 0xFF])


def build_servers_dat(entries):
    """生成 Minecraft servers.dat（NBT）。entries=[(显示名, 地址)]"""
    comps = b""
    for disp, ip in entries:
        c = nbt_child_string("name", disp)
        c += nbt_child_string("ip", ip)
        c += nbt_child_byte("acceptTextures", 1)
        comps += b"\x0a" + c + b"\x00"          # 列表元素是匿名 compound
    lst = b"\x09" + nbt_string_payload("servers") + b"\x0a" + struct.pack(">i", len(entries)) + comps
    return b"\x0a" + nbt_string_payload("") + lst + b"\x00"


INSTALL_TXT = """\
《LuckyWorldInvasion》空岛联机包 · 安装说明
服务器地址：%s（已预置，多人游戏里直接能看到）

一、解压
把本 zip 里的所有内容解压到你的 Minecraft 目录（.minecraft）下。
不确定在哪：打开启动器 → 全局游戏设置 / 版本隔离设置 里能看到"游戏目录"。
解压后 .minecraft\\versions\\ 下应出现两个文件夹：
    1.20.1-clean
    1.20.1-LuckyWorldInvasion

二、启动
打开 HMCL 或 PCL2，版本列表里会出现 "1.20.1-LuckyWorldInvasion"，直接启动。
首次启动启动器会自动补下载原版 1.20.1 核心与 Forge 库（约一两百 MB），需要联网。
Java 选 17（启动器一般会自动选对）。

三、登录（重要）
本服为离线模式 + 白名单。登录方式选"离线登录"，
用户名必须与白名单完全一致（区分大小写）：
    Nashville   或   kuawaA
名字不对会被服务器直接拒绝。

四、进服
多人游戏里已预置服务器 "LuckyWorldInvasion"（%s）。
注意：servers.dat 位于 .minecraft 根目录。如果你原本就有自己的服务器列表，
解压前先备份 .minecraft\\servers.dat，解压后手动把 %s 加回去即可。
若没看到预置项，手动添加服务器，地址填 %s 即可（端口默认不用写）。
首次进服要加载 mod、生成空岛，可能等 30 秒到 2 分钟，别急着退。

五、不要做的事
- 不要增删 mods 里的任何 jar。本包已按服务端要求移除了 framework 与
  controllable 两个会与服务端握手冲突的 mod，加回去会连不上。
- 不要把本目录里的 saves / logs / options.txt 等个人文件拷给别人。

六、语音
整合包自带 Simple Voice Chat，进游戏按 V 设置麦克风即可，无需额外配置。
""" % (SERVER_IP, SERVER_IP, SERVER_IP, SERVER_IP)


def main():
    if os.path.exists(ROOT):
        shutil.rmtree(ROOT)
    os.makedirs(ROOT)

    inst_dst = os.path.join(ROOT, "versions", "1.20.1-LuckyWorldInvasion")
    os.makedirs(inst_dst)

    t0 = time.time()
    n_files = 0
    n_bytes = 0

    # 1) 内容文件
    for f in CONTENT_FILES:
        s = os.path.join(INST, f)
        if os.path.exists(s):
            shutil.copy2(s, os.path.join(inst_dst, f))
            n_files += 1

    # 2) 内容目录
    for d in CONTENT_DIRS:
        s = os.path.join(INST, d)
        if not os.path.isdir(s):
            print("  跳过不存在:", d)
            continue
        dst = os.path.join(inst_dst, d)
        for r, _ds, fs in os.walk(s):
            rel = os.path.relpath(r, s)
            t = os.path.join(dst, rel) if rel != "." else dst
            os.makedirs(t, exist_ok=True)
            for f in fs:
                shutil.copy2(os.path.join(r, f), os.path.join(t, f))
                n_files += 1
        print("  已复制目录 %-18s 累计 %d 文件" % (d, n_files))

    # 3) 父版本 1.20.1-clean（启动器需要它解析 inheritsFrom）
    clean_dst = os.path.join(ROOT, "versions", "1.20.1-clean")
    shutil.copytree(CLEAN, clean_dst)
    n_files += sum(len(fs) for _r, _ds, fs in os.walk(clean_dst))
    print("  已复制父版本 1.20.1-clean")

    # 4) servers.dat（预置服务器地址）
    with open(os.path.join(ROOT, "servers.dat"), "wb") as f:
        f.write(build_servers_dat([("LuckyWorldInvasion", SERVER_IP)]))
    n_files += 1

    # 5) 安装说明（UTF-8 BOM，记事本不乱码）
    with open(os.path.join(ROOT, "INSTALL.txt"), "w", encoding="utf-8-sig") as f:
        f.write(INSTALL_TXT)
    n_files += 1

    print("\n组装完成：%d 个文件，用时 %ds" % (n_files, int(time.time() - t0)))

    # 6) 打 zip：已压缩类型用 STORE，其余 DEFLATE
    print("打包 zip …")
    t1 = time.time()
    with zipfile.ZipFile(OUT, "w", allowZip64=True) as z:
        for r, _ds, fs in os.walk(ROOT):
            for f in sorted(fs):
                p = os.path.join(r, f)
                # 以 ROOT 为基准：解压到 .minecraft 后直接是 versions/、servers.dat、INSTALL.txt，
                # 不能带外层包装目录，否则启动器识别不到。
                arc = os.path.relpath(p, ROOT).replace("\\", "/")
                ext = os.path.splitext(f)[1].lower()
                z.write(p, arc, zipfile.ZIP_STORED if ext in STORE_EXT else zipfile.ZIP_DEFLATED)
                n_bytes += os.path.getsize(p)
    print("zip 完成：%.0f MB（原始 %.0f MB），用时 %ds"
          % (os.path.getsize(OUT) / 1048576.0, n_bytes / 1048576.0, int(time.time() - t1)))

    # 7) 校验：条目数、mods jar 数、确认两个冲突 mod 不在包内
    z = zipfile.ZipFile(OUT)
    names = z.namelist()
    jars = [n for n in names if n.endswith(".jar") and "/mods/" in n]
    print("\n== 校验 ==")
    print("  zip 条目总数        =", len(names))
    print("  包内 mods jar 数    =", len(jars), "(应为 254)")
    for bad in ["framework-forge-1.20.1-0.7.15.jar", "controllable-forge-1.20.1-0.21.7.jar"]:
        hit = [n for n in names if n.endswith(bad)]
        print("  %-44s %s" % (bad, "!! 仍在包内" if hit else "已排除 OK"))
    for need in ["versions/1.20.1-clean/1.20.1-clean.json",
                 "versions/1.20.1-LuckyWorldInvasion/1.20.1-LuckyWorldInvasion.json",
                 "servers.dat", "INSTALL.txt",
                 "versions/1.20.1-LuckyWorldInvasion/config/skyblockbuilder/templates/default.nbt"]:
        print("  %-70s %s" % (need[:70], "OK" if need in names else "!! 缺失"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
