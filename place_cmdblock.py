import os
import paramiko, shlex

HOST = "47.120.61.237"
USER = "root"
PWD = os.environ.get("MC_SSH_PASSWORD")
if not PWD:
    raise SystemExit("set MC_SSH_PASSWORD environment variable first")
# 要执行的 RCON 命令
CMDS = [
    'setblock -144 71 -96 minecraft:command_block[facing=east]{Command:"function mobfarm:build"}',
    'setblock -144 72 -96 minecraft:stone_pressure_plate',
    # 出生点旁边再放一个供验证用的踏板标记牌(可选)
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
