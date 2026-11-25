#!/usr/bin/env python3
"""分块上传整合包 payload 到服务器，带逐块校验、重试与断点续传。

为什么必须分块：单连接传 550MB 实测在 61% 处被远端 RST 断开（错误 10054），
且一旦断开必须从 0 重来。分块后任何一次抖动最多损失一个块，可原地重试。

设计：
  1. 本地按 32MB 切块，逐块算 SHA-256。
  2. 每块独立 SFTP 连接上传（连接不复用，避免长连接累积故障）。
  3. 上传后立即在远端算该块 SHA-256 并比对，不一致则重传该块。
  4. 已校验通过的块记录在本地 manifest，重跑时自动跳过（断点续传）。
  5. 全部块就位后在远端按序拼接、整体校验、解包。
"""
import base64
import hashlib
import json
import os
import sys
import time

import paramiko

from ssh_exec import HOST, USER, PWD, run

LOCAL_TGZ = r"G:\lwi-staging\lwi-payload.tar.gz"
CHUNK_DIR = r"G:\lwi-staging\chunks"
MANIFEST = r"G:\lwi-staging\manifest.json"
REMOTE_DIR = "/opt/lwi"
REMOTE_CHUNK_DIR = "/opt/lwi/.chunks"
REMOTE_TGZ = "/opt/lwi/lwi-payload.tar.gz"

CHUNK_SIZE = 32 * 1024 * 1024
MAX_RETRY = 4


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def load_manifest():
    if os.path.exists(MANIFEST):
        with open(MANIFEST, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"whole_sha": None, "chunk_size": CHUNK_SIZE, "done": {}}


def save_manifest(m):
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)


def sftp_connect():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=PWD,
              timeout=30, banner_timeout=30, auth_timeout=30)
    c.get_transport().set_keepalive(15)
    return c


def upload_chunk(idx, path, want_sha, total, t_start):
    """上传单个块并在远端校验；返回 True 表示成功。"""
    for attempt in range(1, MAX_RETRY + 1):
        c = None
        try:
            c = sftp_connect()
            sftp = c.open_sftp()
            sftp.get_channel().settimeout(120)
            remote = "%s/part_%04d" % (REMOTE_CHUNK_DIR, idx)
            sftp.put(path, remote)
            sftp.close()
            c.close()
            c = None
            got = run("sha256sum %s/part_%04d | awk '{print $1}'" % (REMOTE_CHUNK_DIR, idx), timeout=180)
            got = got.strip().splitlines()[-1].strip() if got.strip() else ""
            if got == want_sha:
                return True
            print("    校验不符 期望 %s 实得 %s" % (want_sha[:12], got[:12]))
        except Exception as e:
            print("    第 %d 次失败: %s" % (attempt, str(e)[:110]))
            if c is not None:
                try:
                    c.close()
                except Exception:
                    pass
        if attempt < MAX_RETRY:
            time.sleep(3 * attempt)
    return False


def main():
    if not os.path.exists(LOCAL_TGZ):
        print("找不到本地包: %s" % LOCAL_TGZ)
        return 2

    os.makedirs(CHUNK_DIR, exist_ok=True)
    total_size = os.path.getsize(LOCAL_TGZ)

    m = load_manifest()
    if m.get("whole_sha") is None:
        print("计算本地整包 SHA-256 …")
        m["whole_sha"] = sha256_file(LOCAL_TGZ)
        m["size"] = total_size
        save_manifest(m)
    whole_sha = m["whole_sha"]
    print("本地包 %.1f MB  SHA256=%s" % (total_size / 1048576.0, whole_sha))

    run("mkdir -p %s" % REMOTE_CHUNK_DIR)

    n_chunks = (total_size + CHUNK_SIZE - 1) // CHUNK_SIZE
    print("分块数 = %d（每块 %d MB）" % (n_chunks, CHUNK_SIZE // 1048576))

    t_start = time.time()
    with open(LOCAL_TGZ, "rb") as f:
        for idx in range(n_chunks):
            key = "%04d" % idx
            data = f.read(CHUNK_SIZE)
            if not data:
                break
            want = sha256_bytes(data)
            # 断点续传：远端已存在且校验一致则跳过
            if m["done"].get(key) == want:
                exists = run("test -f %s/part_%s && sha256sum %s/part_%s | awk '{print $1}' || echo MISSING"
                             % (REMOTE_CHUNK_DIR, key, REMOTE_CHUNK_DIR, key), timeout=180).strip().splitlines()[-1].strip()
                if exists == want:
                    print("  [%2d/%d] 已就位，跳过" % (idx + 1, n_chunks))
                    continue
                else:
                    print("  [%2d/%d] manifest 记录但远端缺失，重传" % (idx + 1, n_chunks))
            cpath = os.path.join(CHUNK_DIR, "part_%s" % key)
            with open(cpath, "wb") as cf:
                cf.write(data)
            print("  [%2d/%d] 上传 %d 字节 …" % (idx + 1, n_chunks, len(data)), end="", flush=True)
            if upload_chunk(idx, cpath, want, total_size, t_start):
                m["done"][key] = want
                save_manifest(m)
                el = time.time() - t_start
                print(" OK  (%.1f%% 完成, 已用 %ds)" % ((idx + 1) * 100.0 / n_chunks, int(el)))
                try:
                    os.remove(cpath)
                except OSError:
                    pass
            else:
                print(" !! 块 %s 重传 %d 次仍失败，中止。重跑本脚本可续传。" % (key, MAX_RETRY))
                return 1

    print("\n全部块已就位，远端拼接 …")
    concat = ("cd %s && rm -f %s && for i in $(seq -f 'part_%%04g' 0 %d); do cat $i; done > %s && echo CONCAT_OK"
              % (REMOTE_CHUNK_DIR, REMOTE_TGZ, n_chunks - 1, REMOTE_TGZ))
    out = run(concat, timeout=900)
    print(out.strip())
    if "CONCAT_OK" not in out:
        print("!! 拼接失败")
        return 1

    print("\n== 整包 SHA-256 校验 ==")
    remote_sha = run("sha256sum %s | awk '{print $1}'" % REMOTE_TGZ, timeout=600).strip().splitlines()[-1].strip()
    remote_size = run("stat -c %%s %s" % REMOTE_TGZ, timeout=120).strip().splitlines()[-1].strip()
    print("  远端 sha = %s" % remote_sha)
    print("  本地 sha = %s" % whole_sha)
    print("  远端 size = %s / 本地 size = %d" % (remote_size, total_size))
    if remote_sha != whole_sha or str(remote_size) != str(total_size):
        print("!! 整包校验不一致，中止（不静默继续）。")
        return 1
    print("  整包校验一致 OK")

    print("\n== 清理块文件并解包 ==")
    print(run("rm -rf %s && cd %s && tar -xzf lwi-payload.tar.gz && echo UNTAR_OK"
              % (REMOTE_CHUNK_DIR, REMOTE_DIR), timeout=900).strip())

    print("\n== 解包结果核对 ==")
    print(run("cd %s && echo -n 'mods jar: '; ls mods/*.jar 2>/dev/null | wc -l; "
              "echo -n 'config: '; find config -type f | wc -l; "
              "echo -n 'kubejs: '; find kubejs -type f | wc -l; "
              "echo -n 'addons: '; find addons -type f | wc -l; "
              "echo -n 'tacz: '; find tacz -type f | wc -l; "
              "echo -n 'tlm: '; find tlm_custom_pack -type f 2>/dev/null | wc -l; "
              "echo -n 'defaultconfigs: '; find defaultconfigs -type f 2>/dev/null | wc -l; "
              "echo; echo '--- 空岛模板 ---'; ls config/skyblockbuilder/templates/ 2>&1; "
              "echo; echo '--- 体积 ---'; du -sh mods config kubejs addons tacz tlm_custom_pack defaultconfigs 2>/dev/null; "
              "echo; echo '--- 磁盘 ---'; df -h / | tail -1"
              % REMOTE_DIR, timeout=300))
    print("\n总耗时 %ds" % int(time.time() - t_start))
    return 0


if __name__ == "__main__":
    sys.exit(main())
