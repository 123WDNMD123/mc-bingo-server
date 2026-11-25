import os
import paramiko, shlex

HOST = "47.120.61.237"
USER = "root"
PWD = os.environ.get("MC_SSH_PASSWORD")
if not PWD:
    raise SystemExit("set MC_SSH_PASSWORD environment variable first")
CMDS = [
    # 1. 重载数据包，让 spawn 函数生效
    'reload',
    # 2. 拆掉出生点东边的物理刷怪塔 (结构包围盒)
    'fill -146 72 -99 -139 95 -92 minecraft:air',
    # 3. 拆掉测试塔 (500,100,500 处)
    'fill 498 101 497 505 124 504 minecraft:air',
    # 4. 命令方块重配为 spawn
    'setblock -144 71 -96 minecraft:command_block[facing=east]{Command:"function mobfarm:spawn"}',
    # 5. 重新放踏板
    'setblock -144 72 -96 minecraft:stone_pressure_plate',
]


def main():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=PWD, timeout=20)
    args = " ".join(shlex.quote(x) for x in CMDS)
    remote = f"python3 /tmp/rcon.py 127.0.0.1 25575 MCrcon_2026x {args}"
    stdin, stdout, stderr = c.exec_command(remote, get_pty=True)
    print(stdout.read().decode("utf-8", "replace"))
    print(stderr.read().decode("utf-8", "replace"))
    c.close()


if __name__ == "__main__":
    main()
