import os
import paramiko, sys

# 2026-11-08：原普通公网 IP 47.120.68.181 在实例重启后漂移失效，
# 已由用户转换为弹性公网 IP（EIP），转换后地址为 47.120.61.237。
# EIP 不随实例重启变化，此地址应保持稳定。
HOST = "47.120.61.237"
USER = "root"
PWD = os.environ.get("MC_SSH_PASSWORD")
if not PWD:
    raise SystemExit("set MC_SSH_PASSWORD environment variable first")
def run(cmd, timeout=600):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=PWD,
              timeout=20, banner_timeout=20, auth_timeout=20)
    # keepalive：长命令或大文件传输期间若链路静默，中间设备/sshd 会断开连接
    # （实测单连接传 550MB 在 61% 处被 RST，错误 10054）。每 15 秒发心跳可避免。
    c.get_transport().set_keepalive(15)
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout, get_pty=True)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    c.close()
    return (out + "\n" + err).strip()


if __name__ == "__main__":
    cmd = sys.argv[1]
    print(run(cmd))
