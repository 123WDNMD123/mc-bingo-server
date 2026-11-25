#!/usr/bin/env python3
"""《浮岛物语》验收入口 —— 只读优先的纯 CLI 工具。

设计约束（不可破坏）：
  1. import 本模块不产生任何副作用；一切行为都在显式子命令里。
  2. 默认全部只读：不建命令方块、不改方块、不改世界数据。
     方块/实体探测用 `execute ... if ... run say <唯一标记>` + 读日志实现，
     因为 RCON 对 `execute` 不回显结果（已实测），而 `data get block`
     只对方块实体有效。探测只往日志写一行带 WBPROBE 前缀的标记。
  3. 唯一写操作是 clean-testblock：清除旧版脚本残留在 (0,110,0) 的
     TEST 命令方块。必须显式调用，不会被其他子命令触发。
  4. RCON 密码从远端 server.properties 动态读取，不写进本仓库。

用法：
  python verify_island_play.py status               服务/就绪/端口/插件总览
  python verify_island_play.py list                 在线玩家
  python verify_island_play.py hub                  母岛建筑与全息探测（只读）
  python verify_island_play.py islands              岛屿 JSON 摘要
  python verify_island_play.py progress             公共进度 progress.yml
  python verify_island_play.py log -n 80 -g 关键字   查看服务端日志
  python verify_island_play.py raw <命令> [命令...]  RCON 原样透传，自负其责
  python verify_island_play.py clean-testblock      清除残留 TEST 命令方块（写）
"""

import argparse
import base64
import os
import re
import shlex
import sys
import time

from ssh_exec import run

MC_DIR = "/opt/mc"
RCON_HOST = "127.0.0.1"
RCON_PORT = "25575"
RCON_SCRIPT = os.environ.get("MC_RCON_SCRIPT", "/tmp/rcon.py")
HUB_WORLD = "bskyblock_world"


# --------------------------------------------------------------------------
# 基础通道
# --------------------------------------------------------------------------

def _password_expr():
    """远端 shell 片段：从 server.properties 取 rcon.password，避免凭据入库。"""
    return "$(grep -a '^rcon.password=' %s/server.properties | cut -d= -f2-)" % MC_DIR


def rcon(commands, timeout=120):
    """通过远端 RCON 执行一条或多条命令，返回回显文本。"""
    if isinstance(commands, str):
        commands = [commands]
    remote = "python3 %s %s %s %s %s" % (
        RCON_SCRIPT, RCON_HOST, RCON_PORT, _password_expr(),
        " ".join(shlex.quote(c) for c in commands),
    )
    return run(remote, timeout=timeout)


def probe_world(tests, world=HUB_WORLD, settle=2.5):
    """批量只读探测。tests = [(标签, execute 的 if 条件片段), ...]。

    返回 [(标签, 是否命中)]。实现：条件命中时让服务端 `say` 一个唯一标记，
    再从 logs/latest.log 里 grep 回来。标记含时间戳，跨次运行互不干扰。
    """
    token = "WBPROBE%d" % (int(time.time() * 10) % 100000000)
    commands = [
        "execute in %s if %s run say %s_%d" % (world, cond, token, i)
        for i, (_label, cond) in enumerate(tests)
    ]
    rcon(commands)
    time.sleep(settle)
    out = run("grep -a '%s_' %s/logs/latest.log | tail -%d"
              % (token, MC_DIR, len(tests) * 3 + 5))
    hit = set(int(m.group(1)) for m in re.finditer(r"%s_(\d+)" % re.escape(token), out))
    return [(label, i in hit) for i, (label, _c) in enumerate(tests)]


def _print_checks(rows):
    """打印探测结果；返回是否全部命中。"""
    width = max((len(label) for label, _ in rows), default=10)
    ok_all = True
    for label, ok in rows:
        ok_all = ok_all and ok
        print("  [%s] %s" % ("HIT" if ok else "--", label.ljust(width)))
    return ok_all


# --------------------------------------------------------------------------
# 子命令
# --------------------------------------------------------------------------

def cmd_status(_args):
    """服务与就绪状态总览，全部只读。"""
    script = r'''
echo "== systemd =="
systemctl is-active mc.service
echo "== 启动完成标记 =="
grep -a 'Done (' {mc}/logs/latest.log | tail -1
echo "== 端口监听 =="
ss -ltn | grep -E ':(25565|25575)' || echo "未监听"
echo "== 已启用插件清单行 =="
grep -a 'IslandTweaks (' {mc}/logs/latest.log | tail -1
echo "== IslandTweaks 启用日志 =="
grep -a '\[IslandTweaks\]' {mc}/logs/latest.log | tail -4
echo "== 全日志 exception 计数 =="
grep -a -c -i 'exception' {mc}/logs/latest.log
echo "== 关键插件 JAR =="
ls -la --time-style=+%Y-%m-%d\ %H:%M {mc}/plugins/IslandTweaks.jar {mc}/plugins/QuickShop-Hikari.jar {mc}/plugins/Vault.jar 2>&1
'''.format(mc=MC_DIR)
    print(run(script))
    print("\n== RCON 连通性（list）==")
    print(rcon("list"))
    return 0


def cmd_list(_args):
    """在线玩家，只读。"""
    print(rcon("list"))
    return 0


def cmd_hub(_args):
    """母岛建筑、工地与全息只读探测。"""
    print("== 期望存在的建筑/实体（只读探测）==")
    want = probe_world([
        ("中心信标 (0,120,0)=beacon", "block 0 120 0 minecraft:beacon"),
        ("信标玻璃罩 (0,121,0)=glass", "block 0 121 0 minecraft:glass"),
        # 中心 d<5 区域被石砖/平滑石覆盖草地（buildHub 设计如此），
        # 故此处期望 stone_bricks 而非 grass_block。
        ("中心地面 (0,119,0)=stone_bricks", "block 0 119 0 minecraft:stone_bricks"),
        # 十字步道：buildHub 条件为 d<5 || |x|<=1 || |z|<=1，
        # 故 x=0 或 z=0 的整条带都是平滑石，草地只在两者都不成立的区域。
        ("十字步道 (0,119,10)=smooth_stone", "block 0 119 10 minecraft:smooth_stone"),
        ("草地带 (5,119,7)=grass_block", "block 5 119 7 minecraft:grass_block"),
        ("岛基底 (0,116,0)=stone", "block 0 116 0 minecraft:stone"),
        ("一期工地地基 (-13,120,-13)=oak_planks", "block -13 120 -13 minecraft:oak_planks"),
        ("一期工地告示牌 (-13,121,-7)=oak_sign", "block -13 121 -7 minecraft:oak_sign"),
        ("全息文本实体 island-hub-text 存在", "entity @e[type=text_display,tag=island-hub-text]"),
        ("母岛区块已加载", "loaded 0 120 0"),
        ("回家点站立面 (0,119,5)=smooth_stone", "block 0 119 5 minecraft:smooth_stone"),
        ("回家点脚部空间 (0,120,5)=air", "block 0 120 5 minecraft:air"),
        ("回家点头部空间 (0,121,5)=air", "block 0 121 5 minecraft:air"),
    ])
    _print_checks(want)

    print("\n== 反向指标（这些“命中”说明有问题）==")
    unwanted = probe_world([
        ("中心地面是空气（应为实体地面）", "block 0 119 0 minecraft:air"),
        ("残留 TEST 命令方块 (0,110,0)", "block 0 110 0 minecraft:repeating_command_block"),
    ])
    _print_checks(unwanted)

    print("\n== 信标方块实体直读（仅方块实体可用 data get）==")
    print(rcon("execute in %s run data get block 0 120 0 id" % HUB_WORLD))
    return 0


def cmd_islands(_args):
    """岛屿数据库摘要，只读。"""
    code = r'''
import glob, json
files = sorted(glob.glob('/opt/mc/plugins/BentoBox/database/Island/*.json'))
files = [f for f in files if '.bak-' not in f]
if not files:
    print('NO_ISLAND_JSON')
for f in files:
    d = json.loads(open(f).read())
    sp = d.get('spawnPoint', {}).get('NORMAL')
    print(f.split('/')[-1])
    print('   owner=%r spawn=%s reserved=%s purgeProtected=%s protectionRange=%s'
          % (d.get('owner'), d.get('spawn'), d.get('reserved'),
             d.get('purgeProtected'), d.get('protectionRange')))
    print('   NORMAL_spawnPoint=%s' % (sp,))
    print('   homes=%s' % list((d.get('homes') or {}).keys()))
'''
    print(run("echo " + base64.b64encode(code.encode()).decode() + " | base64 -d | python3"))
    print("\n== Essentials spawn.yml（母岛落点，须与插件一致）==")
    print(run("cat %s/plugins/Essentials/spawn.yml" % MC_DIR))
    return 0


def cmd_progress(_args):
    """公共修复进度，只读。"""
    print(run("cat %s/plugins/IslandTweaks/progress.yml 2>&1" % MC_DIR))
    print("\n== 文件时间戳 ==")
    print(run("ls -la --time-style=full-iso %s/plugins/IslandTweaks/" % MC_DIR))
    return 0


def cmd_log(args):
    """查看服务端日志，只读。"""
    cmd = "tail -n %d %s/logs/latest.log" % (args.lines, MC_DIR)
    if args.grep:
        cmd += " | grep -a -i %s" % shlex.quote(args.grep)
    print(run(cmd))
    return 0


def cmd_raw(args):
    """RCON 原样透传。可能含写操作，调用者自负其责。"""
    if not args.cmds:
        print("没有给定命令。示例：python verify_island_play.py raw list")
        return 2
    print(rcon(args.cmds))
    return 0


def cmd_clean_testblock(_args):
    """清除旧版脚本残留在 (0,110,0) 的 TEST 命令方块。本文件唯一写操作。"""
    print("== 清理前状态 ==")
    before = probe_world([
        ("残留 repeating_command_block (0,110,0)", "block 0 110 0 minecraft:repeating_command_block"),
        ("残留 command_block (0,110,0)", "block 0 110 0 minecraft:command_block"),
    ])
    _print_checks(before)
    if not any(ok for _l, ok in before):
        print("\n未发现残留命令方块，无需清理。")
        return 0

    print("\n== 执行 setblock 0 110 0 minecraft:air ==")
    print(rcon("execute in %s run setblock 0 110 0 minecraft:air" % HUB_WORLD))
    time.sleep(1.0)

    print("\n== 清理后复核 ==")
    after = probe_world([
        ("(0,110,0) 已为空气", "block 0 110 0 minecraft:air"),
        ("仍残留 repeating_command_block", "block 0 110 0 minecraft:repeating_command_block"),
    ])
    _print_checks(after)
    ok = after[0][1] and not after[1][1]
    print("\nCLEAN_TESTBLOCK_%s" % ("OK" if ok else "FAILED"))
    return 0 if ok else 1


# --------------------------------------------------------------------------

def build_parser():
    ap = argparse.ArgumentParser(
        prog="verify_island_play.py",
        description="《浮岛物语》只读验收入口（约束见文件头）",
    )
    sub = ap.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="服务/就绪/端口/插件总览").set_defaults(func=cmd_status)
    sub.add_parser("list", help="在线玩家").set_defaults(func=cmd_list)
    sub.add_parser("hub", help="母岛建筑与全息只读探测").set_defaults(func=cmd_hub)
    sub.add_parser("islands", help="岛屿 JSON 摘要").set_defaults(func=cmd_islands)
    sub.add_parser("progress", help="公共进度 progress.yml").set_defaults(func=cmd_progress)

    p_log = sub.add_parser("log", help="查看服务端日志")
    p_log.add_argument("-n", "--lines", type=int, default=60, help="tail 行数，默认 60")
    p_log.add_argument("-g", "--grep", default=None, help="按关键字过滤（忽略大小写）")
    p_log.set_defaults(func=cmd_log)

    p_raw = sub.add_parser("raw", help="RCON 原样透传（可能含写操作）")
    p_raw.add_argument("cmds", nargs="*", help="要执行的 RCON 命令")
    p_raw.set_defaults(func=cmd_raw)

    sub.add_parser("clean-testblock", help="清除 (0,110,0) 残留 TEST 命令方块（唯一写操作）") \
        .set_defaults(func=cmd_clean_testblock)
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
