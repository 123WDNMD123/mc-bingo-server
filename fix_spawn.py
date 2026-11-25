#!/usr/bin/env python3
"""恢复无属主的公共母岛（完整清档后的兜底工具）。

红线：绝不把玩家岛设为母岛。若找不到无属主岛，本脚本拒绝执行并保持玩家岛不变。

重要前提：正常情况下 **不需要运行本脚本**。IslandTweaks 的 restoreHub()
在 BentoBoxReadyEvent 后会自动建立/校正母岛属性与回家点。本脚本只用于
插件恢复失败、或需要在服务停止状态下直接修数据库的场景。

用法:
  python fix_spawn.py            停服 → 改 JSON + spawn.yml → 起服 → 复核
  python fix_spawn.py --dry-run  只报告将要改动哪个岛，不停服、不写任何文件

坐标标准（D-007，三处必须一致）:
  IslandTweaks.HUB_HOME_*  /  本脚本 HUB_HOME  /  Essentials/spawn.yml
  = (0.5, 120.0, 5.5)
"""
import argparse
import base64
import sys
import time
from pathlib import Path

import paramiko

from ssh_exec import run, HOST, USER, PWD

ROOT = Path(__file__).resolve().parent
SPAWN_YML_LOCAL = ROOT / "output" / "handbook" / "spawn.yml"
SPAWN_YML_REMOTE = "/opt/mc/plugins/Essentials/spawn.yml"

# 母岛回家点唯一标准值，与 IslandTweaks.HUB_HOME_* 一致（D-007）。
HUB_HOME = (0.5, 120.0, 5.5)


def upload(local, remote):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=PWD, timeout=20)
    s = c.open_sftp()
    s.put(str(local), remote)
    s.close()
    c.close()


def remote_code(dry_run: bool) -> str:
    """生成在远端 python3 执行的岛屿数据库修补脚本。"""
    return '''import glob, json
from pathlib import Path
DRY = %s
HX, HY, HZ = %r
files = sorted(glob.glob('/opt/mc/plugins/BentoBox/database/Island/*.json'))
files = [f for f in files if '.bak-' not in f]
if not files:
    print('NO_ISLAND: 岛屿数据库为空，请先启动服务器等 BentoBox 初始化')
    raise SystemExit(10)
found = False
for f in files:
    p = Path(f)
    d = json.loads(p.read_text())
    if d.get('owner'):
        # 红线：玩家岛一律不动
        print('PLAYER_ISLAND_UNTOUCHED', p.name, 'owner=', d.get('owner'))
        continue
    found = True
    print('TARGET_UNOWNED_ISLAND', p.name)
    print('  before: spawn=%%s reserved=%%s purgeProtected=%%s NORMAL=%%s'
          %% (d.get('spawn'), d.get('reserved'), d.get('purgeProtected'),
              (d.get('spawnPoint') or {}).get('NORMAL')))
    if DRY:
        print('  DRY-RUN：未写入')
        continue
    d['spawn'] = True
    d['reserved'] = True
    d['purgeProtected'] = True
    d['protectionRange'] = 50
    d['spawnPoint'] = {'NORMAL': ['bskyblock_world', HX, HY, HZ, 0.0, 0.0]}
    d['homes'] = {}
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2))
    # 回读校验，确认写盘成功
    chk = json.loads(p.read_text())
    ok = (chk.get('spawn') is True and chk.get('reserved') is True
          and chk.get('purgeProtected') is True
          and (chk.get('spawnPoint') or {}).get('NORMAL') == ['bskyblock_world', HX, HY, HZ, 0.0, 0.0])
    print('  after : spawn=%%s reserved=%%s purgeProtected=%%s NORMAL=%%s -> %%s'
          %% (chk.get('spawn'), chk.get('reserved'), chk.get('purgeProtected'),
              (chk.get('spawnPoint') or {}).get('NORMAL'), 'OK' if ok else 'VERIFY_FAILED'))
    if not ok:
        raise SystemExit(11)
if not found:
    print('NO_UNOWNED_ISLAND: 没有无属主岛可设为母岛；拒绝使用玩家岛（红线）')
    raise SystemExit(12)
print('HUB_JSON_DONE' if not DRY else 'HUB_JSON_DRYRUN_OK')
''' % ("True" if dry_run else "False", HUB_HOME)


def patch_hub(dry_run: bool):
    """执行岛屿数据库修补，返回 (输出, 退出码是否为成功标记)。"""
    code = remote_code(dry_run)
    out = run("echo " + base64.b64encode(code.encode()).decode() + " | base64 -d | python3; echo RC=$?")
    ok = ("HUB_JSON_DRYRUN_OK" in out) if dry_run else ("HUB_JSON_DONE" in out and "RC=0" in out)
    return out, ok


def start_server():
    run("systemctl start mc.service")


def wait_done(max_wait_s=180):
    """轮询日志直到出现 Done ( 标记。"""
    for i in range(max_wait_s // 5):
        time.sleep(5)
        out = run("grep -a 'Done (' /opt/mc/logs/latest.log | tail -1")
        if "Done (" in out:
            return out.strip()
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="恢复无属主公共母岛（兜底工具）")
    ap.add_argument("--dry-run", action="store_true", help="只报告将改动哪个岛，不停服不写文件")
    args = ap.parse_args()

    if not SPAWN_YML_LOCAL.exists():
        print("缺少本地 spawn.yml：%s" % SPAWN_YML_LOCAL)
        return 2

    if args.dry_run:
        print("### DRY-RUN：不停服、不写文件 ###")
        out, ok = patch_hub(dry_run=True)
        print(out)
        return 0 if ok else 1

    print("### 停服修补模式 ###")
    print("提示：正常情况下 IslandTweaks.restoreHub() 会自动处理，无需本脚本。")
    print(run("systemctl stop mc.service && echo STOPPED"))

    # 停服后再修：BentoBox 运行时持有内存态，热改 JSON 会在下次保存时被覆盖。
    out, ok = patch_hub(dry_run=False)
    print(out)

    upload(SPAWN_YML_LOCAL, SPAWN_YML_REMOTE)
    print("已上传 spawn.yml -> %s" % SPAWN_YML_REMOTE)
    print(run("cat %s" % SPAWN_YML_REMOTE))

    if not ok:
        print("!! 岛屿数据库修补未成功，但仍会把服务器拉起来，避免留在停机状态。")
        start_server()
        print(run("systemctl is-active mc.service"))
        return 1

    start_server()
    print("已请求启动，等待就绪…")
    done = wait_done()
    if done:
        print("就绪：%s" % done)
    else:
        print("!! 未在预期时间内看到 Done (，请手工检查 systemctl status mc.service")

    print("\n== 插件侧母岛恢复日志 ==")
    print(run("grep -a '公共母岛已就绪\\|已自动恢复独立公共母岛\\|恢复公共母岛失败' /opt/mc/logs/latest.log | tail -3"))
    print("\n请进游戏用 /is spawn 实测落点为 (0.5,120,5.5)，并确认落点安全。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
