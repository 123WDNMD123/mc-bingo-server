#!/usr/bin/env python3
"""部署《LuckyWorldInvasion》服务端配置并启动，迭代修崩溃。

设计约束：
  - server.properties 用"先让 Forge 生成默认值、再 patch 必要键"的方式，
    避免写入 1.20.1 不存在的键。
  - voicechat 的 voice_host 必须填公网 IP，否则 NAT 下客户端语音连不上。
  - 启动后必须等日志出现 Done ( 才算成功，不看 systemctl is-active。
  - 崩溃时自动收集错误并停下报告，不盲目重试。

用法:
  python deploy_lwi.py            配置 + 启动
  python deploy_lwi.py --config    只写配置，不启动
  python deploy_lwi.py --status    只查当前状态
"""
import argparse
import base64
import json
import os
import sys
import time

from ssh_exec import run, HOST, USER, PWD
import paramiko

LWI = "/opt/lwi"
EIP = "47.120.61.237"          # 弹性公网 IP（已转换，不随实例重启漂移）
VOICE_PORT = 24454
CFG_LOCAL = r"G:\lwi-staging\cfg"

# 必须偏离默认值的 server.properties 键。其余交给 Forge 默认值。
SERVER_PROPS = {
    "motd": "\\u00a7bLucky World Invasion\\u00a7r \\u00a77| \\u00a7e\\u7a7a\\u5c9b\\u5f81\\u670d",
    "server-port": "25565",
    "online-mode": "false",
    "white-list": "true",
    "enforce-whitelist": "true",
    "prevent-proxy-connections": "false",
    "max-players": "4",
    # level-type=default 是刻意选择：SkyblockBuilder 注入原版 normal 预设标签，
    # default(NORMAL) 会被重定向到 skyblockbuilder:skyblock 空岛预设。
    "level-type": "default",
    "level-name": "world",
    "generate-structures": "true",
    "view-distance": "8",
    "simulation-distance": "6",
    "entity-broadcast-range-percentage": "100",
    "max-tick-time": "180000",
    "allow-flight": "true",
    "allow-nether": "true",
    "pvp": "true",
    "gamemode": "survival",
    "difficulty": "normal",
    "hardcore": "false",
    "force-gamemode": "false",
    "spawn-protection": "0",
    "enable-command-block": "false",
    "network-compression-threshold": "256",
    "use-native-transport": "true",
    "sync-chunk-writes": "true",
    "enable-rcon": "true",
    "rcon.port": "25575",
    "rcon.password": "LWI_rcon_2026",
    "enable-status": "true",
    "enable-query": "false",
}

WHITELIST = [
    {"uuid": "1b435776-e2b0-3458-b89b-20b7a222a4f8", "name": "Nashville"},
    {"uuid": "09b5f228-a45c-36eb-aab8-a602458e5983", "name": "kuawaA"},
]
OPS = [
    {"uuid": "1b435776-e2b0-3458-b89b-20b7a222a4f8", "name": "Nashville",
     "level": 4, "bypassesPlayerLimit": False},
    {"uuid": "09b5f228-a45c-36eb-aab8-a602458e5983", "name": "kuawaA",
     "level": 4, "bypassesPlayerLimit": False},
]


def upload(local, remote):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=PWD, timeout=30, banner_timeout=30, auth_timeout=30)
    c.get_transport().set_keepalive(15)
    s = c.open_sftp()
    s.put(local, remote)
    s.close()
    c.close()


def run_py(code, timeout=300):
    """远端执行 python3 代码（base64 传递，避免引号/heredoc 破坏内容）。"""
    return run("echo " + base64.b64encode(code.encode()).decode() + " | base64 -d | python3", timeout=timeout)


def inject(template, **kw):
    """把 __KEY__ 占位符替换成值。

    刻意不用 % 或 str.format 格式化模板：模板内含大量给远端 Python 用的
    '%' 和 '{'，用它们做外层格式化会造成双重转义（已实测踩坑）。
    """
    out = template
    for k, v in kw.items():
        out = out.replace("__%s__" % k.upper(), v)
    return out


def patch_server_props():
    """只改已有键或追加缺失键，保留 Forge 生成的其余默认值。"""
    tmpl = r'''
import json
from pathlib import Path
props = json.loads(r"""__PROPS_JSON__""")
p = Path('__LWI__/server.properties')
lines = p.read_text(encoding='utf-8', errors='replace').splitlines() if p.exists() else []
seen, out = set(), []
for ln in lines:
    s = ln.strip()
    if s.startswith('#') or '=' not in s:
        out.append(ln)
        continue
    k = s.split('=', 1)[0].strip()
    if k in props:
        out.append('%s=%s' % (k, props[k]))
        seen.add(k)
    else:
        out.append(ln)
for k, v in props.items():
    if k not in seen:
        out.append('%s=%s' % (k, v))
p.write_text('\n'.join(out) + '\n', encoding='utf-8')

# 回读校验：关键键必须等于期望值，不做乐观假设
chk = {}
for l in p.read_text(encoding='utf-8').splitlines():
    if '=' in l and not l.strip().startswith('#'):
        k, v = l.split('=', 1)
        chk[k.strip()] = v.strip()
bad = [(k, chk.get(k), v) for k, v in props.items() if chk.get(k) != str(v)]
if bad:
    print('PROPS_VERIFY_FAILED')
    for b in bad:
        print('   ', b)
    raise SystemExit(11)
print('SERVER_PROPS_OK  总键数=%d' % len(chk))
print('   online-mode=%s  white-list=%s  enforce-whitelist=%s  level-type=%s  allow-flight=%s'
      % (chk.get('online-mode'), chk.get('white-list'), chk.get('enforce-whitelist'),
         chk.get('level-type'), chk.get('allow-flight')))
print('   server-port=%s  rcon.port=%s  view-distance=%s  simulation-distance=%s  max-players=%s'
      % (chk.get('server-port'), chk.get('rcon.port'), chk.get('view-distance'),
         chk.get('simulation-distance'), chk.get('max-players')))
'''
    return run_py(inject(tmpl, props_json=json.dumps(SERVER_PROPS), lwi=LWI))


def write_json(name, obj):
    tmpl = r'''
import json
from pathlib import Path
p = Path('__LWI__/__NAME__')
payload = json.loads(r"""__PAYLOAD__""")
p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
back = json.loads(p.read_text(encoding='utf-8'))
if back != payload:
    print('__NAME___VERIFY_FAILED'); raise SystemExit(12)
print('__NAME__ OK  条目=%d' % len(back))
for e in back:
    print('   ', e.get('name'), e.get('uuid'))
'''
    return run_py(inject(tmpl, lwi=LWI, name=name, payload=json.dumps(obj, ensure_ascii=False)))


def patch_voicechat():
    """voice_host 必须填公网 IP：为空时客户端拿到的是连不上语音的地址。"""
    tmpl = r'''
from pathlib import Path
p = Path('__LWI__/config/voicechat/voicechat-server.properties')
if not p.exists():
    print('VOICECHAT_CONFIG_MISSING（mod 首启后才生成，需在启动后补）')
    raise SystemExit(0)
lines = p.read_text(encoding='utf-8', errors='replace').splitlines()
out, seen = [], set()
for ln in lines:
    s = ln.strip()
    if s.startswith('#') or '=' not in s:
        out.append(ln); continue
    k = s.split('=', 1)[0].strip()
    if k == 'voice_host':
        out.append('voice_host=__EIP__'); seen.add(k)
    elif k == 'port':
        out.append('port=__VPORT__'); seen.add(k)
    else:
        out.append(ln)
if 'voice_host' not in seen: out.append('voice_host=__EIP__')
if 'port' not in seen: out.append('port=__VPORT__')
p.write_text('\n'.join(out) + '\n', encoding='utf-8')
chk = {}
for l in p.read_text(encoding='utf-8').splitlines():
    if '=' in l and not l.strip().startswith('#'):
        k, v = l.split('=', 1); chk[k.strip()] = v.strip()
ok = chk.get('voice_host') == '__EIP__' and chk.get('port') == '__VPORT__'
print('VOICECHAT_%s voice_host=%s port=%s' % ('OK' if ok else 'VERIFY_FAILED',
      chk.get('voice_host'), chk.get('port')))
if not ok: raise SystemExit(13)
'''
    return run_py(inject(tmpl, lwi=LWI, eip=EIP, vport=str(VOICE_PORT)))


def install_service():
    upload(os.path.join(CFG_LOCAL, "lwi.service"), "/etc/systemd/system/lwi.service")
    out = run("systemctl daemon-reload && systemctl enable lwi.service 2>&1 && echo SERVICE_ENABLED")
    return out


def do_config():
    print("== eula ==")
    upload(os.path.join(CFG_LOCAL, "eula.txt"), LWI + "/eula.txt")
    print(run("cat %s/eula.txt" % LWI))

    print("\n== JVM 参数 ==")
    upload(os.path.join(CFG_LOCAL, "user_jvm_args.txt"), LWI + "/user_jvm_args.txt")
    print(run("grep -E '^-Xm' %s/user_jvm_args.txt" % LWI))

    print("\n== server.properties ==")
    print(patch_server_props())

    print("\n== whitelist.json ==")
    print(write_json("whitelist.json", WHITELIST))

    print("\n== ops.json ==")
    print(write_json("ops.json", OPS))

    print("\n== voicechat ==")
    print(patch_voicechat())

    print("\n== systemd 单元 ==")
    print(install_service())

    print("\n== 目录核对 ==")
    print(run("cd %s && ls -la | head -20; echo -n 'mods: '; ls mods/*.jar 2>/dev/null | wc -l; "
              "echo -n '内存余量: '; free -h | awk '/Mem:/{print $7}'" % LWI))


def status():
    print(run("""
echo '== lwi.service =='
systemctl is-active lwi.service; systemctl is-enabled lwi.service 2>/dev/null
echo '== 进程 =='
pgrep -af 'unix_args' | head -2 || echo '无 java 进程'
echo '== 端口 =='
ss -ltn | grep -E ':(25565|25575)' || echo '未监听'
ss -uln | grep ':%d' || echo '语音端口未监听'
echo '== 日志尾部 =='
tail -30 %s/logs/console.log 2>/dev/null || tail -30 %s/logs/latest.log 2>/dev/null || echo '无日志'
echo '== Done 标记 =='
grep -a 'Done (' %s/logs/latest.log 2>/dev/null | tail -2 || echo '尚未就绪'
echo '== 内存 =='
free -h | head -2
""" % (VOICE_PORT, LWI, LWI, LWI)))


def wait_done(max_wait=900):
    """等 Done ( 出现；期间报告崩溃。"""
    t0 = time.time()
    while time.time() - t0 < max_wait:
        out = run("grep -a 'Done (' %s/logs/latest.log 2>/dev/null | tail -1; "
                  "grep -a -c 'Done (' %s/logs/latest.log 2>/dev/null || echo 0" % (LWI, LWI), timeout=120)
        if "Done (" in out:
            return out.strip()
        # 检测崩溃
        crash = run("tail -25 %s/logs/console.log 2>/dev/null | grep -aiE 'crash|exception|error|failing|failed to start|A problem occurred' | tail -6" % LWI, timeout=120)
        if crash.strip() and "Not Secure" not in crash:
            act = run("systemctl is-active lwi.service", timeout=60).strip()
            if act != "active":
                return "CRASH\n" + crash
        time.sleep(15)
        print("  等待中 %ds …" % int(time.time() - t0))
    return "TIMEOUT"


def main():
    ap = argparse.ArgumentParser(description="部署 LuckyWorldInvasion 服务端")
    ap.add_argument("--config", action="store_true", help="只写配置，不启动")
    ap.add_argument("--status", action="store_true", help="只查状态")
    ap.add_argument("--no-wait", action="store_true", help="启动后不等待 Done")
    args = ap.parse_args()

    if args.status:
        status()
        return 0

    do_config()
    if args.config:
        print("\n--config 模式：未启动服务。")
        return 0

    print("\n== 启动 lwi.service ==")
    print(run("mkdir -p %s/logs && systemctl start lwi.service && sleep 5 && systemctl is-active lwi.service" % LWI))

    if args.no_wait:
        print("（--no-wait：不等待就绪）")
        return 0

    print("\n== 等待服务器就绪（最长 15 分钟）==")
    res = wait_done()
    print(res)
    if res.startswith("CRASH") or res == "TIMEOUT":
        print("\n!! 未成功启动。以下是日志尾部与崩溃报告：")
        print(run("echo '--- console.log 尾 60 行 ---'; tail -60 %s/logs/console.log 2>/dev/null; "
                  "echo '--- 最新崩溃报告 ---'; ls -t %s/crash-reports/*.txt 2>/dev/null | head -1 | xargs -r head -60"
                  % (LWI, LWI)))
        return 1

    print("\n== 就绪核对 ==")
    print(run("grep -a 'Done (' %s/logs/latest.log | tail -1; "
              "echo -n '25565/TCP: '; ss -ltn | grep -c ':25565'; "
              "echo -n '25575/TCP: '; ss -ltn | grep -c ':25575'; "
              "echo -n '%d/UDP : '; ss -uln | grep -c ':%d'; "
              "echo -n '世界类型: '; grep -a -oE 'level-type=[a-z]+' %s/server.properties; "
              "echo -n '内存余量: '; free -h | awk '/Mem:/{print $7}'"
              % (VOICE_PORT, VOICE_PORT, LWI)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
