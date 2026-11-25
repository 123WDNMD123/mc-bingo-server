#!/usr/bin/env python3
"""
《浮岛物语》清档工具 —— 测试阶段专用

用法:
  python wipe.py              完整清档（世界 + 全部玩家进度），自动备份后执行
  python wipe.py --dry-run    只打印将要删除的内容和体积，不做任何修改
  python wipe.py --keep-worlds  保留地形，只清玩家进度（技能/背包/岛屿归属/家/余额）

安全约束（不可绕过）:
  1. 执行前必定先生成 /opt/backups/pre-wipe-<时间戳>.tgz 并校验 SHA-256，备份失败则中止。
  2. 只删除"进度数据"，绝不删除插件 JAR、配置文件、汉化文件、服务端程序。
  3. 删除范围全部白名单枚举，不使用通配符递归删除 /opt 或 /opt/mc 根目录。

清档后必做:
  BentoBox 的岛屿数据库被清空 => 母岛出生点丢失，/is spawn 会失效。
  等第一位玩家进服自动建岛后，运行:  python fix_spawn.py
"""

import sys
import argparse
from ssh_exec import run

MC = "/opt/mc"

WORLDS = [
    "world",
    "world_nether",
    "world_the_end",
    "bskyblock_world",
    "bskyblock_world_nether",
    "bskyblock_world_the_end",
]

# 玩家进度数据：目录内全部内容清空，目录本身保留
PROGRESS_DIRS = [
    "plugins/AuraSkills/userdata",
    "plugins/Essentials/userdata",
]

# 玩家进度数据：整个目录删除（插件启动时会重建）
PROGRESS_TREES = [
    "plugins/BentoBox/database/Island",
    "plugins/BentoBox/database/Players",
    "plugins/BentoBox/database/Names",
    "plugins/BentoBox/database/Ranks",
    "plugins/BentoBox/database/IslandDeletion",
]

# 进度类单文件：仅完整清档时删除（保留地形时必须留住公共进度）
PROGRESS_FILES = [
    "plugins/IslandTweaks/progress.yml",
]

# 明确保留、绝不触碰的路径（必需项缺失才算异常）
NEVER_TOUCH_REQUIRED = [
    "paper.jar",
    "server.properties",
    "bukkit.yml",
    "spigot.yml",
    "plugins/AuraSkills-2.4.0.jar",
    "plugins/BentoBox.jar",
    "plugins/CrouchGrow.jar",
    "plugins/EssentialsX.jar",
    "plugins/AuraSkills/config.yml",
    "plugins/AuraSkills/messages",
    "plugins/AuraSkills/menus",
    "plugins/BentoBox/config.yml",
    "plugins/BentoBox/addons",
    "plugins/Essentials/config.yml",
    "plugins/Essentials/spawn.yml",
    "plugins/Essentials/book.txt",
    "plugins/Essentials/kits",
]

# 可选存在的配置文件（不同 Paper 版本位置不同，缺失仅提示不算异常）
NEVER_TOUCH_OPTIONAL = [
    "paper-world.yml",
    "config/paper-global.yml",
    "config/paper-world-defaults.yml",
]


def build_remote_script(dry_run: bool, keep_worlds: bool) -> str:
    """生成在服务器上执行的 python3 清档脚本。"""
    lines = []
    lines.append("import os, shutil, subprocess, tarfile, hashlib, sys, time")
    lines.append("from pathlib import Path")
    lines.append("MC = Path(%r)" % MC)
    lines.append("DRY = %s" % ("True" if dry_run else "False"))
    lines.append("KEEP_WORLDS = %s" % ("True" if keep_worlds else "False"))
    lines.append("WORLDS = %r" % (WORLDS,))
    lines.append("PROGRESS_DIRS = %r" % (PROGRESS_DIRS,))
    lines.append("PROGRESS_TREES = %r" % (PROGRESS_TREES,))
    lines.append("PROGRESS_FILES = %r" % (PROGRESS_FILES,))
    lines.append("")
    lines.append("def human(n):")
    lines.append("    for u in ['B','K','M','G']:")
    lines.append("        if n < 1024 or u == 'G': return '%.1f%s' % (n, u)")
    lines.append("        n /= 1024.0")
    lines.append("")
    lines.append("def dsize(p):")
    lines.append("    p = Path(p)")
    lines.append("    if p.is_file(): return p.stat().st_size")
    lines.append("    t = 0")
    lines.append("    for root, dirs, files in os.walk(p):")
    lines.append("        for f in files:")
    lines.append("            try: t += os.path.getsize(os.path.join(root, f))")
    lines.append("            except OSError: pass")
    lines.append("    return t")
    lines.append("")
    lines.append("targets = []")
    lines.append("if not KEEP_WORLDS:")
    lines.append("    targets += [MC / w for w in WORLDS]")
    # G1 修复：progress.yml 必须在 existing 计算之前加入 targets，
    # 否则既不备份也不删除，导致完整清档清不掉公共进度。
    lines.append("    targets += [MC / f for f in PROGRESS_FILES]")
    lines.append("targets += [MC / d for d in PROGRESS_DIRS]")
    lines.append("targets += [MC / d for d in PROGRESS_TREES]")
    lines.append("existing = [t for t in targets if t.exists()]")
    lines.append("")
    lines.append("print('== 清档范围 ==')")
    lines.append("total = 0")
    lines.append("for t in existing:")
    lines.append("    s = dsize(t)")
    lines.append("    total += s")
    lines.append("    print('  %-52s %s' % (str(t.relative_to(MC)), human(s)))")
    lines.append("print('  合计 %s，共 %d 项目标' % (human(total), len(existing)))")
    lines.append("if not KEEP_WORLDS:")
    lines.append("    print('  完整清档：含公共进度 progress.yml')")
    lines.append("else:")
    lines.append("    print('  保留地形与公共进度 progress.yml')")
    lines.append("")
    lines.append("if not existing:")
    lines.append("    print('没有可清除的数据，退出。')")
    lines.append("    sys.exit(0)")
    lines.append("")
    lines.append("if DRY:")
    lines.append("    print('DRY-RUN：未做任何修改。')")
    lines.append("    sys.exit(0)")
    lines.append("")
    lines.append("print('== 停服 ==')")
    lines.append("subprocess.run(['systemctl','stop','mc.service'], check=True)")
    lines.append("for _ in range(30):")
    lines.append("    if subprocess.run(['systemctl','is-active','--quiet','mc.service']).returncode != 0: break")
    lines.append("    time.sleep(1)")
    lines.append("print('  已停止')")
    lines.append("")
    lines.append("print('== 备份 ==')")
    lines.append("ts = time.strftime('%Y%m%d-%H%M%S')")
    lines.append("bk = Path('/opt/backups') / ('pre-wipe-%s.tgz' % ts)")
    lines.append("bk.parent.mkdir(parents=True, exist_ok=True)")
    lines.append("with tarfile.open(bk, 'w:gz') as tf:")
    lines.append("    for t in existing: tf.add(t, arcname=str(t.relative_to(MC)))")
    lines.append("if not bk.exists() or bk.stat().st_size == 0:")
    lines.append("    print('  备份失败，中止清档！服务器仍为停止状态，请手动 systemctl start mc.service')")
    lines.append("    sys.exit(2)")
    lines.append("sha = hashlib.sha256(bk.read_bytes()).hexdigest()")
    lines.append("print('  %s' % bk)")
    lines.append("print('  size=%s sha256=%s' % (human(bk.stat().st_size), sha))")
    lines.append("")
    lines.append("print('== 删除 ==')")
    lines.append("for t in existing:")
    lines.append("    if t.is_dir():")
    lines.append("        if str(t.relative_to(MC)) in PROGRESS_DIRS:")
    lines.append("            for c in list(t.iterdir()):")
    lines.append("                shutil.rmtree(c) if c.is_dir() else c.unlink()")
    lines.append("            print('  清空 %s' % t.relative_to(MC))")
    lines.append("        else:")
    lines.append("            shutil.rmtree(t)")
    lines.append("            print('  删除 %s' % t.relative_to(MC))")
    lines.append("    else:")
    # G1 修复：单文件目标（progress.yml）此前无分支，会被静默跳过而不删除。
    lines.append("        if str(t.relative_to(MC)) in PROGRESS_FILES:")
    lines.append("            t.unlink()")
    lines.append("            print('  删除文件 %s' % t.relative_to(MC))")
    lines.append("        else:")
    lines.append("            print('  警告：意外出现的非白名单文件目标，跳过 %s' % t.relative_to(MC))")
    lines.append("")
    lines.append("print('== 自检：受保护路径是否完好 ==')")
    lines.append("missing = []")
    lines.append("for rel in %r:" % (NEVER_TOUCH_REQUIRED,))
    lines.append("    if not (MC / rel).exists(): missing.append(rel)")
    lines.append("if missing:")
    lines.append("    print('  警告：必需路径缺失 ' + repr(missing))")
    lines.append("else:")
    lines.append("    print('  必需路径完好，共 %d 项' )" % len(NEVER_TOUCH_REQUIRED))
    lines.append("for rel in %r:" % (NEVER_TOUCH_OPTIONAL,))
    lines.append("    if not (MC / rel).exists(): print('  可选配置未使用：' + rel)")
    lines.append("")
    lines.append("print('== 启动 ==')")
    lines.append("log = MC / 'logs' / 'latest.log'")
    lines.append("old_mtime = log.stat().st_mtime if log.exists() else 0")
    lines.append("subprocess.run(['systemctl','start','mc.service'], check=True)")
    lines.append("done = False")
    lines.append("for i in range(150):")
    lines.append("    time.sleep(5)")
    lines.append("    try:")
    lines.append("        if log.exists() and log.stat().st_mtime > old_mtime:")
    lines.append("            if 'Done (' in log.read_text(encoding='utf-8', errors='replace'):")
    lines.append("                done = True")
    lines.append("                print('  启动完成，用时约 %ds' % ((i + 1) * 5))")
    lines.append("                break")
    lines.append("    except OSError: pass")
    lines.append("if not done: print('  提示：日志未确认完成启动，继续核对服务状态')")
    lines.append("")
    lines.append("# 兼容远端 Python 3.6：不使用 capture_output")
    lines.append("proc = subprocess.run(['systemctl','is-active','mc.service'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)")
    lines.append("act = proc.stdout.decode('utf-8', 'replace').strip()")
    lines.append("print('  mc.service = %s' % act)")
    lines.append("if act != 'active': sys.exit(3)")
    lines.append("")
    lines.append("errs = []")
    lines.append("try:")
    lines.append("    for ln in log.read_text(encoding='utf-8', errors='replace').splitlines():")
    lines.append("        low = ln.lower()")
    lines.append("        if ('error' in low or 'severe' in low or 'exception' in low) and 'not secure' not in low:")
    lines.append("            errs.append(ln)")
    lines.append("except OSError: pass")
    lines.append("print('== 启动日志错误 %d 条 ==' % len(errs))")
    lines.append("for e in errs[-15:]: print('  ' + e)")
    lines.append("print('BACKUP_FILE=%s' % bk)")
    lines.append("print('WIPE_DONE')")
    return chr(10).join(lines) + chr(10)


def main() -> int:
    ap = argparse.ArgumentParser(description="《浮岛物语》清档工具")
    ap.add_argument("--dry-run", action="store_true", help="只打印范围，不修改")
    ap.add_argument("--keep-worlds", action="store_true", help="保留地形，只清玩家进度")
    args = ap.parse_args()

    remote = build_remote_script(args.dry_run, args.keep_worlds)
    cmd = "python3 - <<'REMOTE_WIPE_EOF'" + chr(10) + remote + "REMOTE_WIPE_EOF"

    mode = "DRY-RUN 预演" if args.dry_run else ("保留地形清进度" if args.keep_worlds else "完整清档")
    print("### 模式: %s ###" % mode)
    out = run(cmd, timeout=1200)
    print(out)

    if not args.dry_run and "WIPE_DONE" not in out:
        print("!! 清档流程未正常结束，请检查上方输出与服务器状态。")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
