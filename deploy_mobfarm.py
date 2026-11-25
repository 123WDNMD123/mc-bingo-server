import os
import paramiko

HOST = "47.120.61.237"
USER = "root"
PWD = os.environ.get("MC_SSH_PASSWORD")
if not PWD:
    raise SystemExit("set MC_SSH_PASSWORD environment variable first")
PACK_MCMETA = '''{
  "pack": {
    "min_format": [94, 1],
    "max_format": [94, 1],
    "description": "Mob Farm Generator (canyue-budao)"
  }
}
'''

SPAWN_FUNC = '''# 残血怪刷怪器：在最近玩家周围生成残血怪（半颗心，一刀补死）
execute at @p run summon minecraft:zombie ~ ~1 ~ {Health:1.0f,PersistenceRequired:1b}
execute at @p run summon minecraft:zombie ~1 ~1 ~ {Health:1.0f,PersistenceRequired:1b}
execute at @p run summon minecraft:skeleton ~-1 ~1 ~ {Health:1.0f,PersistenceRequired:1b}
execute at @p run summon minecraft:spider ~ ~1 ~1 {Health:1.0f,PersistenceRequired:1b}
execute at @p run summon minecraft:zombie ~ ~1 ~-1 {Health:1.0f,PersistenceRequired:1b}
'''

BUILD_FUNC = '''# 残血补刀式刷怪塔生成器 (命令方块原点, 塔在东边+X方向)
# --- 收集间 + 竖井墙 (玻璃, 透明方便观察) ---
fill ~2 ~1 ~0 ~2 ~20 ~1 minecraft:glass
fill ~1 ~1 ~0 ~2 ~20 ~0 minecraft:glass
fill ~1 ~1 ~1 ~2 ~20 ~1 minecraft:glass
fill ~1 ~2 ~0 ~1 ~20 ~1 minecraft:glass
# --- 补刀半砖口 (西墙 y=1) ---
setblock ~1 ~1 ~0 minecraft:stone_slab[type=bottom]
setblock ~1 ~1 ~1 minecraft:stone_slab[type=bottom]
# --- 刷怪房底板 8x8 ---
fill ~-2 ~20 ~-3 ~5 ~20 ~4 minecraft:stone
# --- 中心 2x2 掉落口 ---
fill ~1 ~20 ~0 ~2 ~20 ~1 minecraft:air
# --- 活板门 (怪走上去掉进洞) ---
setblock ~1 ~21 ~0 minecraft:spruce_trapdoor[open=true]
setblock ~2 ~21 ~0 minecraft:spruce_trapdoor[open=true]
setblock ~1 ~21 ~1 minecraft:spruce_trapdoor[open=true]
setblock ~2 ~21 ~1 minecraft:spruce_trapdoor[open=true]
# --- 刷怪房墙 (3 格高) ---
fill ~-2 ~21 ~-3 ~-2 ~23 ~4 minecraft:stone
fill ~5 ~21 ~-3 ~5 ~23 ~4 minecraft:stone
fill ~-2 ~21 ~-3 ~5 ~23 ~-3 minecraft:stone
fill ~-2 ~21 ~4 ~5 ~23 ~4 minecraft:stone
# --- 天花板 ---
fill ~-2 ~24 ~-3 ~5 ~24 ~4 minecraft:stone
'''


def main():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=PWD, timeout=20)
    # 建目录
    c.exec_command("mkdir -p /opt/mc/world/datapacks/mobfarm/data/mobfarm/function")
    sftp = c.open_sftp()
    with sftp.open("/opt/mc/world/datapacks/mobfarm/pack.mcmeta", "w") as f:
        f.write(PACK_MCMETA)
    with sftp.open("/opt/mc/world/datapacks/mobfarm/data/mobfarm/function/build.mcfunction", "w") as f:
        f.write(BUILD_FUNC)
    with sftp.open("/opt/mc/world/datapacks/mobfarm/data/mobfarm/function/spawn.mcfunction", "w") as f:
        f.write(SPAWN_FUNC)
    sftp.close()
    # 校验
    _, out, _ = c.exec_command(
        "find /opt/mc/world/datapacks/mobfarm -type f | sort && "
        "echo '--- spawn.mcfunction ---' && cat /opt/mc/world/datapacks/mobfarm/data/mobfarm/function/spawn.mcfunction"
    )
    print(out.read().decode("utf-8", "replace"))
    c.close()


if __name__ == "__main__":
    main()
