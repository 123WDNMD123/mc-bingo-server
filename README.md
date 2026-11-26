# MC Server — Minecraft 26.3 BINGO 合作服

一套可复现的 Minecraft 服务器部署方案：**Yet Another BINGO 合作玩法 + 队伍语音 + 性能优化 + 配方查询**，
含服务端部署脚本、客户端整合包构建脚本和中文玩家手册。

**在线服务器**：`47.120.61.237:25565`（语音 UDP `24454`）

---

## 这是什么

不是又一个模组列表，而是一套**踩过坑、有实测证据**的部署工程：

- **服务端**：Minecraft Java 版 26.3 + Fabric 0.20.1 + Java 25，systemd 托管，每日自动备份
- **玩法**：全员同队合作 BINGO，共享一张 5×5 宾果卡，横/竖/斜连一线通关
- **语音**：大厅附近语音，开局后全队一组、队友不限距离
- **客户端**：HMCL / PCL2 一键导入的整合包，内置离线模组兜底
- **准入**：离线登录默认可进，仅黑名单拦截

## 快速开始（玩家）

1. 从 [Releases](../../releases) 下载 `BINGO-26.3-HMCL-PCL2.zip`
2. HMCL / PCL2 →「安装整合包」→ 选择该 ZIP
3. 启动器选**离线登录**，填个昵称
4. 进游戏 → 多人游戏 → 列表里已有「BINGO 26.3」

按住 **V** 说话，**G** 打开语音界面。详见 **[玩家手册](output/BINGO-26.3-玩家手册.md)**。

> 模组从 Modrinth 下载，国内网络可能超时。ZIP 内 `overrides/mods-offline/`
> 已附带全部 10 个模组本体（哈希已校验），下载失败时手动复制进 `mods` 即可。

## 目录结构

```
├── output/
│   ├── BINGO-26.3-玩家手册.md      # 玩家 + 服主完整手册
│   ├── bingo-build/                # 本次 BINGO 服的部署与验收脚本
│   │   ├── aliyun_api.py           # 阿里云云助手 OpenAPI 客户端（绕开 Workbench 会话上限）
│   │   ├── oss_relay.py            # OSS 中转（绕开 ECS→CDN 限速）
│   │   ├── relay_mods.py           # 模组中转 + SHA-1/SHA-512 双校验
│   │   ├── deploy_bingo_server.py  # 服务端配置 + systemd + 备份定时器
│   │   ├── apply_defaults.py       # 合作玩法配置（停服写入，避免被回写）
│   │   ├── build_client_pack.py    # 构建 HMCL/PCL2 整合包
│   │   ├── mc_client.py            # 离线协议客户端（验收用）
│   │   └── manifest.json           # 模组版本与官方哈希清单
│   └── handbook/                   # 旧服（浮岛物语）手册资料
├── island_tweaks/                  # 旧服 Paper 插件源码（Java）
├── HANDOFF.md                      # 项目交接档案：决策、坑、验收边界
└── *.py                            # 旧服部署运维脚本
```

## 服主部署要点

完整步骤见[玩家手册第七章](output/BINGO-26.3-玩家手册.md)。核心命令：

```bash
systemctl status bingo          # 服务状态
journalctl -u bingo -f          # 实时日志
systemctl start bingo-backup.service   # 立即备份一次
```

**环境变量**：仓库内不含任何密码。旧服 SSH 脚本需要自行设置：

```bash
export MC_SSH_PASSWORD='你的密码'
```

阿里云凭据从 `~/.workbench/config.json` 读取，不写入代码。
RCON 密码由部署脚本随机生成并写入 `server.properties`（权限 600，不打印）。

### 给自己开服主权限（离线服有个静默失效的坑）

**顺序不能颠倒**：

1. 先用你的昵称**离线登录一次**，让它进入 `usercache.json`
2. 再执行 `op <你的昵称>`

如果名字从未登录过，`op` 会去查 **Mojang 正版档案**。万一你的昵称恰好是真实存在的正版账号名，
服务端就会写入那个正版 UUID（还可能把名字小写化），**和你离线登录的 UUID 完全不同 —— OP 不生效，而且不报错**。

离线 UUID 的正确算法是 `UUID.nameUUIDFromBytes("OfflinePlayer:" + name)`，即**纯 MD5**（置 version=3 / variant）：

```python
import hashlib, uuid
def offline_uuid(name):
    b = bytearray(hashlib.md5(("OfflinePlayer:" + name).encode()).digest())
    b[6] = (b[6] & 0x0F) | 0x30
    b[8] = (b[8] & 0x3F) | 0x80
    return uuid.UUID(bytes=bytes(b))
```

**不是** `uuid.uuid3(uuid.NAMESPACE_DNS, ...)` —— 那会拼上 DNS namespace，算出完全不同的值。**大小写敏感。**

验证权限是否真的生效，别只看 `ops.json`。服务端会在 play 阶段下发 Entity Event
（包 `0x22`，5 字节载荷 = int entityId + byte eventId），**eventId = 24 + 权限等级**。
用 `output/bingo-build/op_level_probe.py <OP名> <非OP名>` 做对照，OP 应收到 28（等级 4），非 OP 收到 24（等级 0）。

## 踩过的坑（值得抄走的部分）

| 坑 | 现象 | 解法 |
| --- | --- | --- |
| **Workbench 会话上限** | CLI 守护反复重启，孤儿会话堆积到上限，`exec`/`upload` 全被拒，本地 `session list` 却为空 | 改用同一 AK 直连 **ECS 云助手 OpenAPI**（`RunCommand`），不占会话 |
| **ECS→Modrinth 仅 25KB/s** | 模组下载必超时 | 本机下载校验 → **OSS 中转** → ECS 拉取（262KB/s），用后即删 |
| **BINGO 配置被回写** | 运行中改 `game-options.json` 会被内存状态覆盖 | **停服** → 同时改 `game-options-default.json` 模板 → 启动 |
| **PvP 关不掉** | 改 JSON 无效 | PvP 实际由**世界 gamerule** 控制，需 `gamerule pvp false` |
| **JDK 25 启动告警** | `-XX:+ZGenerational` 被忽略 | 该参数在 **JDK 24+ 已移除**，删掉即可 |
| **servers.dat 读不出** | 服务器列表为空 | NBT 根标签必须是 **TAG_Compound(10)**，不是 TAG_String |
| **语音按键不生效** | 配置写了没反应 | 实际 ID 是 **`key.push_to_talk`**，不带 `voicechat.` 前缀 |
| **离线服 OP 不生效** | `ops.json` 写了却不认，且无报错 | `op` 对未登录过的名字会查正版档案。必须**先离线登录一次再 op**；离线 UUID 是纯 MD5，非 `uuid3(DNS,…)` |
| **找不到玩家存档** | `world/playerdata/` 不存在 | 26.3 改到了 **`world/players/data/`** |

## 验收边界（如实说明）

**已用硬证据验证**：服务启动 `Done (4.328s)`、公网握手返回 `26.3 / protocol 777`、
三端口监听、离线登录 `joined the game`、双人同服、BINGO 开局 `countdown -> playing`、
共享计分板 `Goal: 1 line`、语音端口接入、9 个模组双重哈希匹配、备份实跑 SHA-256 校验 OK。

**未验证**：真人客户端实机画面与麦克风音质、HMCL/PCL2 实机导入、完整连线通关结算画面。
以上进服/开局验证是用自写离线协议客户端 + RCON + 服务端日志完成的，不等于真人体验已验证。

## 模组清单（10 个）

| 模组 | 版本 | 作用 | 端 |
| --- | --- | --- | --- |
| Fabric API | 0.166.2+26.3 | 基础库 | 双端 |
| Yet Another Bingo | 2.15.1+mc26.3 | BINGO 玩法（自带简中） | 双端 |
| Simple Voice Chat | 2.6.27+26.3 | 在线语音 | 双端 |
| Lithium | 0.26.4+mc26.3 | 服务端逻辑优化 | 双端 |
| FerriteCore | 9.0.0 | 内存优化 | 双端 |
| Sodium | 0.9.3+mc26.3 | 渲染优化 | 仅客户端 |
| REI | 26.3.824 | 配方查询 | 双端 |
| Cloth Config | 26.3.159 | 配置界面库 | 双端 |
| Architectury | 22.1.7 | 兼容库 | 双端 |
| Fabric Language Kotlin | 1.14.2 | BINGO 硬依赖 | 双端 |

**不含**新矿物、生物或世界生成模组 —— 保持原版生存手感。

## 许可

代码与文档以 MIT 许可发布。所列模组各有其独立许可证，版权归原作者所有；
本仓库不重新分发模组本体，整合包通过 Modrinth 官方地址下载。
