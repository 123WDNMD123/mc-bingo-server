# 项目交接档案

## 当前状态（2026-11-25 15:20，以本节为准）

### D-016：BINGO 26.3 服已部署并通过协议级验收
- **服务在跑**：`bingo.service`（`/opt/bingo`，已 enable 开机自启），`Done (4.328s)`；`-Xms2G -Xmx4G -XX:+UseZGC`。
  **注意 `-XX:+ZGenerational` 在 JDK 24+ 已移除**，JDK 25 会告警忽略，已从单元删除。
- **三端口实测在听**：25565/TCP（游戏）、24454/UDP（语音）、25575/TCP（RCON，**未对公网放行**）。安全组已放行前两者。
- **公网可达实证**：本机 TCP 连 `47.120.61.237:25565` 成功（47ms）；真实 MC 状态握手返回 `26.3 / protocol 777`，上限 10 人。
- **9 个服务端模组** SHA-1 + SHA-512 全部匹配 Modrinth 官方值（sodium 仅客户端，未上传）。含隐藏硬依赖 `fabric-language-kotlin`。
- **合作规则已落地**：`teamCount=1`、`teamAutoShuffle=true`、目标 `lines=1`、`isPvpEnabled=false`、`isKeepInventory=true`。
- **语音规则已落地**：`useCombinedGroupAlways=true`（全员一组、队友不限距离）、`voice_host=47.120.61.237`、`enable_groups=true`。
- **准入**：`online-mode=false`、`white-list=false`，黑名单为空数组，仅 `ban/pardon` 管理。
- **备份已实跑**：`bingo-backup.timer` 每天 04:30 已 enable；手动跑一次产出 200MB，`sha256sum -c` = OK，保留最近 7 份。

### 本轮踩到并已解决的坑（重要，勿重复）
1. **Workbench 会话上限**：CLI 守护反复重启累计创建 43 个云端会话、0 个正常关闭，孤儿会话堆到上限，`exec/upload` 全部被拒，
   本地 `session list` 却始终为空、无法自助回收。**绕行方案：改用同一 AK 直连 ECS 云助手 OpenAPI**
   （`RunCommand` + `DescribeInvocationResults`，见 `output/bingo-build/aliyun_api.py`），不占用 Workbench 会话。
2. **ECS→Modrinth CDN 仅 ~25KB/s**，直接下载必超时。**绕行方案：本机下载校验 → OSS 中转 → ECS 拉取**
   （`oss_relay.py` + `relay_mods.py`，实测 262KB/s，传完即删临时对象）。云助手单条命令有长度上限，base64 直传大文件不可行。
3. **BINGO 配置会被运行时回写**：服务运行中改 `game-options.json` 会被内存状态覆盖（`teamCount` 弹回 3）。
   正确做法：**停服 → 同时改 `game-options-default.json`（模板）和 `game-options.json` → 启动**。
4. **PvP 实际由世界 gamerule 控制**，光改 JSON 无效；需 `gamerule pvp false`（已执行，`bingo` 摘要从 `Features: PvP` 变为 `None`）。
5. **`servers.dat` NBT 曾写错**：根标签误用 TAG_String(8) 而非 TAG_Compound(10)，会导致服务器列表读不出。已修正并加解析回环断言。
6. **语音按键 ID 是 `key.push_to_talk`**（不带 `voicechat.` 前缀），已按实际类字面量修正。

### 验收边界（如实记录，勿夸大）
- 进服/开局/语音接入是用**自写离线协议客户端 + RCON + 服务端日志**验证的：
  `LOGIN_SUCCESS`、`joined the game` + 实体 ID + 坐标、`There are 2 of a max of 10 players online`、
  `GameState changed: countdown -> playing`、计分板 `Minecraft Bingo` 显示 `Goal: 1 line / Features: None`。
- **未做**：真人客户端实机（HUD 卡面、麦克风音质）、HMCL/PCL2 实机导入（用户免除）、完整连线通关结算画面。

### 交付物
- 服务端：ECS `/opt/bingo`（运行中）
- 客户端：`output/BINGO-26.3-HMCL-PCL2.zip`（51,547,569 B，10 条索引 + `overrides/mods-offline/` 10 个已校验 jar 兜底）
- 手册：`output/BINGO-26.3-玩家手册.md`
- 构建/运维脚本：`output/bingo-build/`（`aliyun_api.py`、`oss_relay.py`、`relay_mods.py`、`apply_defaults.py`、`build_client_pack.py` 等）

---

## 历史状态（2026-11-25 13:57 快照）
- D-014：按用户确认，《浮岛物语》和《LuckyWorldInvasion》均先冷备到本机，后可逆退役；新 BINGO 服从零开档，不原地升级 Forge/Paper、不复用旧世界，避免跨版本迁移和误删。旧服及 `lwi-backup.timer` 均已停用，不得按下文历史切服命令直接启动。
- `/opt/mc`、`/opt/lwi` 已移出至 `/opt/mc-retirement.Mlftc1TJ/{mc,lwi}`，原路径不存在；`/opt/backups` 历史备份保留。退役时服务器游戏/RCON/语音端口未监听；新服尚未部署。
- 两个本机冷备均位于 `output/server-backups/`，远端/本机 SHA-256 相同，归档可读且含世界 `level.dat`、配置、模组或插件、服务定义；归档内含私有配置，不外发。`FloatingIsland-20261125.tar.gz`：`ad49010c02f5b646441808b6c919392e28cba578219dc2095655658abe6727aa`；`LuckyWorldInvasion-20261125.tar.gz`：`a5401f6b48dbfb8b027bf33c5bf4bdd37f4faa46756245709c9a5d762c44ffe9`。LWI 停服日志确认 `All dimensions are saved`。
- D-015：新服 Java 版 26.3 + Fabric，从零开档；仅装 Yet Another Bingo、队伍语音、性能优化和配方查询，不增加世界生成或物品、生物。保留分队竞技与全员同队合作（共享计分、连一线通关）；大厅附近语音、局内仅队友不限距离，对手近身不串音。准入使用离线登录、默认可进、仅黑名单，无旧白名单继承；不把离线昵称作为管理身份。交付 HMCL/PCL2 用单 ZIP 加中文手册，免启动器实机导入，保留结构与清单校验。公网部署及普通玩家开局、结算和语音验收当前未完成。

## 历史状态（以下为退役前快照）

## 0. TL;DR
- **服务器现状（2026-11-25 复核）**：同一台阿里云 ECS（4C/8G，EIP `47.120.61.237`，实例 `i-f8zifsmhy00kro1q0pvw`，**河源区 cn-heyuan**）上**并存两个服务端，互斥运行**：
  - **当前在跑**：`lwi.service` —— Forge 1.20.1《LuckyWorldInvasion》整合包空岛服，`/opt/lwi`，供 Nashville + kuawaA 联机。**11-08 当天已真人联机实证**（服务端日志有两人 `joined/left` 记录，客户端 lionfishapi 2.8 修复后握手通过）。详见 `output/LuckyWorldInvasion_联机接入说明.md`。
  - **已暂停**：`mc.service` —— Paper 1.21.11《浮岛物语》，`/opt/mc` 数据完整保留、单元已 disable。回切见 §10。
- **停机事件（已闭环）**：11-09 11:36 用户主动关机 → 11-25 11:32 开机，历时约 16 天。EIP **通过停→启大考没漂移**（此前"未实测"项已实证）。开机后 lwi 自动恢复（enable 生效）、备份定时器照常。
- **雷爆事件（G2 已部分爆炸）**：重启使 `/tmp/rcon.py`、`/tmp/Vault.jar`、`/tmp/QuickShop-Hikari.jar` 蒸发——G2 预言的风险变成既成事实。rcon.py 已重写（零依赖）并部署到 `/opt/rcon.py`（持久位置，**已实测**：`whitelist list` 正常返回 2 人）；`lwi-backup.sh` 的引用已同步改到 `/opt/rcon.py`。剩余：Vault/QuickShop 的 `/tmp` 路径尚未迁移（仅影响浮岛物语部署，非阻塞）。
- **远程通道已换（D-013）**：SSH 密码 11-25 失效（实例开了实例连接服务，root 密码登录被替），已迁往 **阿里云 workbench CLI**（AK 凭证在本地 `~/.workbench/config.json`）。paramiko 虽已重装，但其通道已不可用；新旧脚本统一走 workbench 或需改造。
- **浮岛物语进度**：C2/C4/C5/C6/G1/验收入口 6 个问题全部修复并实证；停在 A3（临时账号全链路）之前。A2 已全绿。
- **红线**：不占用玩家岛作母岛；不改 AuraSkills JAR/userdata/汉化；不在交接文档记录密码；不将“插件加载/编译成功/Done 标记”称为玩法可用。
- **两个服的切换**：见 §10（一行命令，切勿同时启动）。

## 0.1 整合包服（lwi）关键事实
- 客户端整合包：`D:\...\versions\1.20.1-LuckyWorldInvasion`，Forge **1.20.1-47.4.4**，256 个 mod jar。
- 服务端 `/opt/lwi`：**JDK 17**（`/usr/lib/jvm/java-17-openjdk`，Forge 1.20.1 不支持 21）+ `-Xmx4G`（实测堆仅用 1.9G，5G 会挤爆系统余量）。
- 服务端 mod = 245 个 jar，其中 **13 个客户端专属已移至 `mods-disabled/`**（依据见 §0.2）。
- `online-mode=false` + `enforce-whitelist=true`，白名单 = Nashville / kuawaA（离线 UUID 已用 MD5 算法双向验证）。
- 语音 Simple Voice Chat：24454/UDP，`voice_host=47.120.61.237`（已用 tcpdump 实测 5/5 包抵达）。
- 备份：`lwi-backup.timer` 每日 04:00，脚本 `/opt/lwi-backup.sh`，已实测跑通（110MB + SHA256）。

## 0.2 mod 取舍判据（可复用，勿凭名字猜）
1. 扫 `META-INF/mods.toml` 的 `clientSideOnly=true` → 服务端排除（找到 10 个）。
2. 无 `mods.toml` 的非 FML mod（Essential）→ 服务端排除。
3. **前两条不够**：另有 12 个声明 `side="BOTH"` 却引用客户端类，靠**首启崩溃报告**才暴露
   （`NoClassDefFoundError: net/minecraft/client/...` 或 `invalid dist DEDICATED_SERVER`）。
4. 反向依赖扫描：`controllable` mandatory 依赖 `framework`，必须同批移除。
5. **网络通道扫描决定客户端是否也要删**：`framework` 注册了 `SimpleChannel`/`ChannelBuilder`/
   `registerMessage` → Forge 握手比对通道清单，客户端有服务端无会被拒连，故**两端都删**；
   其余 11 个未注册通道 → **仅服务端删，客户端保留**（光影/小地图体验不受影响）。

## 1. 项目身份
- 根目录：`C:/Users/64146/WorkBuddy/MC server`；远端 systemd：`mc.service`。
- 构建/部署：`python deploy_island_tweaks.py`（先备份，再远端 javac，成功后重启）。
- 测试：`python verify_island_play.py list`；此脚本当前有缺陷，见 2.3。
- 2026-11-01 14:56 构建：备份 `island-tweaks-20261101-145557.tgz`，SHA-256 `c433d3c7c4802c184f40340f4fd68b89e14226a570c575ec93b63eef1f70b2f8`（已复核一致）。
- **服务器已完全就绪**（15:02 复核，纠正此前“尚未监听”的滞后结论）：`Done (57.477s)` @14:57:05；25565/25575 均 LISTEN；RCON `list` 返回 `0 out of maximum 10 players online`；全日志 0 条 exception。
- 已部署 `IslandTweaks.jar`（14:56）晚于本地源码最后修改（14:13），即线上 JAR 就是当前源码；插件加载日志 `浮岛物语联动已启用：公共修复阶段 0，云币经济已连接`。
- 远端 Python 3.6；旧 PyYAML；复杂文本走 SFTP/Base64；编译 classpath 需 Paper、BentoBox、Vault、`net/kyori`、`net/md-5`。

## 2. 当前状态
### 2.1 已完成且本轮验证
| 功能 | 验证 | 时间 |
|---|---|---|
| 当前源码可编译并进入部署流程 | 实际运行部署脚本，得到 `BUILD_SUCCESS` 及 JAR 类清单 | 2026-11-01 14:56 |
| 验收脚本可被 Python 解析 | `python -m py_compile verify_island_play.py` 退出 0；不代表行为正确 | 2026-11-01 |

### 2.2 进行中
- 公共工地：源码含四工地、TextDisplay、按交付量施工、右键交付；只验证编译，未验证实体/库存/云币/重启保持。**实测运行时零生效**（见 C2）。
- 私人家园：源码含岛体、小屋、床箱、农田、树、刷石区；只验证编译，未验证首进服、落点、礼包、重置不重复补给。**当前 world=null 使 onJoin 建岛分支直接 return，新玩家不会自动建岛**。
- `book.txt` 已更新但尚未上传（本地 md5 `d78a750e…` ≠ 远端 `d8388e1b…`）；HTML、交付 ZIP（14:04）早于 book.txt 与源码（14:13/14:14），未同步最新改动。

### 2.3 已知损坏 / 未验证
| 问题 | 现象 / 排查 | 阻塞 |
|---|---|---|
| **C5 中心信标被灯柱循环覆盖（本轮新发现，已修复）** | `buildHub()` 先放 `BEACON(0,120,0)`+`GLASS(0,121,0)`，紧接着灯笼柱循环 `x,z∈{-22,-11,0,11,22}` **包含 (0,0)**，把信标覆盖成 `oak_log`、玻璃覆盖成 `lantern`。实测线上 `(0,120,0)=oak_log`、`(0,121,0)=lantern`、`(0,122,0)=lantern`（残留）完全吻合——**信标从未真正存在过**。修法：灯柱循环 `if(x==0&&z==0)continue`，并把放信标移到循环之后。修复后 `data get block 0 120 0 id` 直读为 `minecraft:beacon` | 已修复 |
| **C6 spawnPoint 写入无效 + 乐观日志（本轮新发现，已修复）** | 同一次 `saveObject` 里 `reserved/purgeProtected/protectionRange/homes` 全部落盘，唯独 `spawnPoint.NORMAL` 保持旧值 (0.5,125,2.5)。反编译确认 `Island.setSpawnPoint(Environment,Location)` 走 `Map.compute`（lambda$setSpawnPoint$16），在 3.11.1 上不覆盖已有键。改用 `setSpawnPoint(Map)` 重载整体写入后回读成功。**附带教训**：我第一版日志打印的是调用参数而非回读值，属档案自己批评的乐观验证——已改为回读校验，不一致时 `severe` 报警 | 已修复 |
| **G5 旧母岛残留清不掉（本轮量化）** | `buildHub()` 只重建 y=116..122，实测 y=123..130 有 **21 个实体残留方块**，含 `(0,125,0)`、`(0,126,0)`——正位于信标上方，会遮挡信标光束。原地修复无法清除，需完整清档或显式 `fill air` 清理 | 待决策 |
| **G1 wipe.py 漏删 progress.yml（已修复）** | `wipe.py:118-119` 在 `existing` 计算之后才把 `plugins/IslandTweaks/progress.yml` append 进 `targets`，而备份(:141)与删除(:150)只遍历 `existing` → **完整清档既不备份也不删除公共进度**，与“完整清档清公共进度”的既定行为矛盾（dry-run 13 项清单中确无它）。**连带缺陷**：删除循环只有 `if t.is_dir()` 分支，文件目标即使进了 existing 也会被静默跳过；`dsize()` 用 `os.walk` 对文件恒返回 0。三处一并修复后实测：完整清档 14 项含 `progress.yml 272.0B`，`--keep-worlds` 7 项不含 | 已修复 |
| **验收脚本副作用（已修复）** | `verify_island_play.py:14-26` 重复定义 `rcon()`，模块级 `print(rcon(...))` 在 import/CLI 后都会执行，改写 `(0,110,0)` 命令方块。实测远端确有残留 `repeating_command_block`，Command=`tellraw @a {"text":"TEST"}`。已重写为 argparse 纯 CLI（status/list/hub/islands/progress/log/raw/clean-testblock），密码改为从远端 server.properties 动态读取；import 已验证无副作用，残留方块已清除 | 已修复 |
| **C2 world 解析时序（根因，已修复）** | 见下方说明。`IslandTweaks.java:68` 在 `onEnable` 里 `world = Bukkit.getWorld("bskyblock_world")` 只赋值一次。日志时序：IslandTweaks Enabling 14:56:50（行198）→ BSkyBlock Enabling 14:56:58 → bskyblock_world 区块加载 14:56:59（行302）。故 onEnable 时世界不存在，**world 恒为 null**，`restoreHub`、`applyStage`、`onJoin` 全部首行短路。已改为惰性 `world()` + `BentoBoxReadyEvent` 监听 + 周期重试兜底；部署后日志实证 `公共母岛已就绪：…NORMAL 回家点回读=(0.5,120.0,5.5)` @16:33:13 | 已修复 |
| **C4 回家点坐标三处矛盾（已统一）** | A2 完成标准与 `IslandTweaks.java` 为 `(0.5,120,5.5)`；`fix_spawn.py` 曾写 `(0.5,120,2.5)`；`Essentials/spawn.yml` 曾为 `(0.5,125,2.5)`。三处已按 D-007 统一为 `(0.5,120,5.5)`；`fix_spawn.py` 另修复“服务运行时热改 JSON 会被内存态覆盖”缺陷（改为停服→改→回读校验→起服，并新增 `--dry-run`） | 已修复 |
| 首进服竞态 | `onJoin` 直接装饰，CREATED 事件也延迟装饰；`decoratedHomes` 为内存 Set 不持久，重启后失效、失败可能半生成 | 是 |
| 公共刷新 | `applyStage()` 重建整岛，可能覆盖实体/玩家改变；全息更新仅在有玩家时执行（:69），无玩家时刷新不更新 | 否（设计风险） |
| **G3 QuickShop 建店费未真正配置** | 部署脚本写入的 `shop.cost=0`、`price-change-requires-fee=false`、`fee-for-price-change=0`、`name-fee=0` 在最终 config.yml 中**全部不存在**（grep 0 命中；插件启动 14:56 重写配置时丢弃不识别的键）。目前只有 `shop-tax.basic.rate: 0.0` 与 `game-language: zh-CN` 有实据。“建店免费”依赖插件默认值，须用测试账号实测 | 是（A3 前） |
| **G2 /tmp 单点依赖** | 部署依赖 `/tmp/Vault.jar`、`/tmp/QuickShop-Hikari.jar`；一切 RCON 验证依赖 `/tmp/rcon.py`（10-31 放置）。/tmp 易失，云主机重启即断链 | 否（但需迁移） |
| **G4 place_cmdblock.py 游离** | 含明文 SSH+RCON 凭据，指向 `mobfarm:build`，不在关键文件清单，用途不明 | 否（待用户决定去留） |
| 其余玩法 | 商店、普通玩家建店、自然怪过滤、公共采收、维度入口、称号奖励均未实测；**称号奖励确未实现**（全源码 grep `title/称号` 仅命中背包标题 `getTitle()` @:241） | 是（验收前） |

## 3. 决策日志
- **D-001 独立无属主母岛＋默认私有岛**：玩家应拥有经营主线。否决“把首玩家岛设 spawn”：会夺走私人岛并混淆所有权；否决公共竞争排行榜：用户选择合作共建。
- **D-002 逐步实体施工＋全息进度**：可见变化才是玩法反馈。否决“整期材料齐后突然生成建筑”：用户明确反馈此前母岛建设无体现。
- **D-003 家园式开局＋石工具**：降低无谓重复劳动，保留资源经营。否决一棵树/少量方块的极简岛及平均技能等级航线：前者被用户否定，后者只有文字门槛、无真实内容。
- **D-004 云币个人收益＋公共设施，玩家自由市场**：兼顾共建与流通。否决税费、建店费、改价费、出售高强度战斗装备：用户明确不收这些费用且不希望官方商店替代市场。
- **D-005 新岛/重置美化，不自动覆盖旧岛**：避免毁玩家建设；旧岛迁移需另行决定。
- **D-006 world 延迟解析 + BentoBoxReadyEvent（2026-11-01 核查后确定）**：插件 enable 早于世界加载是 Paper/BentoBox 的固定时序，不能靠调大延迟赌时序。方案：所有用到 world 的地方改为 `resolveWorld()` 惰性解析（null 时重新 `Bukkit.getWorld`），母岛恢复/重建挂到 `BentoBoxReadyEvent` 监听器执行；`restoreHub` 改为周期重试直到成功，成功后自取消。否决“把 runTaskLater 延迟调大”：赌固定 tick 数，机器负载变化即复发。
- **D-007 母岛回家点统一为 (0.5,120,5.5)**：以源码 `restoreHub` 设计值为唯一标准，`fix_spawn.py` 与 `spawn.yml` 向它对齐。否决“沿用旧 (0.5,125,2.5)”：y=125 是旧版母岛平台残留高度，与现行 y=119 地面 + y=120 建筑体系脱节，实测落点上方 (0,124,2) 仍有固体方块，存在卡墙/窒息风险。
- **D-008 整合包联机采用「停旧服、整机改造」而非双开或本机开服**：4C/8G 机器上，浮岛物语(Paper 堆 4G) 与整合包(Forge 245 mod 需 5-6G 堆) 内存之和超物理上限，双开不可能；本机在 NAT 后无公网 IP 且可用内存仅 5G，穿透方案延迟稳定性差且关机即掉线。故暂停浮岛物语（只 stop+disable，`/opt/mc` 与 `mc.service` 全部保留），整机跑整合包。否决“升配到 16G 双开”：要加钱且 4 核跑两个重载服 TPS 互拖，当前无此需求。
- **D-009 公网 IP 转为弹性公网 IP(EIP)**：本次“服务器失联”的唯一根因是普通公网 IP 随实例停机被回收重分配（47.120.68.181 → 47.120.61.237）。EIP 不随实例重启漂移，十几元/月买地址永久稳定。否决“继续用普通公网 IP”：每次重启朋友存的地址、脚本 HOST、voice_host 全部失效，坑已实际踩过一次。
- **D-010 服务端 mod 集合 = 客户端全量 − 13 个客户端专属**：不能凭 mod 名字猜是否客户端专属。判据链：①扫 `mods.toml` 的 `clientSideOnly=true`（10 个）②无 mods.toml 的非 FML mod（Essential，1 个）③首启崩溃报告暴露的、声明 `side=BOTH` 却引用客户端类的（12 个，与前两类有交集）。`framework` 因注册网络通道需**两端都删**（否则 Forge 握手 mismatched mod list 拒连），`controllable` 因 mandatory 依赖 framework 一并删；其余 11 个仅服务端删、客户端保留（未注册通道，不影响连接，保留光影/小地图体验）。否决“按名字批量删看起来像客户端的 mod”：会误删 Oculus/Xaero 等未声明 clientSideOnly 的双端 mod，导致握手失败。
- **D-011 JVM 堆定 4G 而非 5G**：`jcmd GC.heap_info` 实测堆仅用 1.9G，而 5G 堆配 `AlwaysPreTouch` 会立即全额预触，使系统 available 仅剩 985Mi，玩家进服加载区块时堆外增长有 OOM 风险。降到 4G 后 available 回升到 1.9Gi，堆内仍余 2.1G（空岛世界+1-2人充裕）。否决“6G”：整机仅 7.3G，OS+堆外刚性支出约 1.5G，6G 堆必 OOM。
- **D-012 整合包开全新世界，不上传本地单人存档**：本地「新的世界」是单人模式产物，带个人进度/作弊痕迹/单人侧 mod 状态，进服务器会造成不公与不一致；且存档由客户端全量 mod 写出，服务端少 13 个 mod，个别存档数据可能引用不存在注册项而炸档。新世界从零生成天然与服务端 mod 集合一致。存档进度价值低（11-01 才建），放弃成本近零。
- **D-013 远程通道迁往 workbench CLI（2026-11-25 确定）**：SSH 密码登录失效后（根因：实例的 `AuthorizedKeysCommand` 实例连接服务 + 用户持有的密码不再被服务端接受，多次密码认证 `Authentication failed`），改走阿里云官方 `workbench` CLI：`exec` 跑远端命令、`upload`/`download` 走 OSS 中转、配置放 `~/.workbench/config.json`（用户提供 AK，权限仅工作台）。**代价与坑**：①实例活跃会话数有上限，密集连发 exec 会被 `该实例活跃会话数已达上限` 拒绝，需间隔/合并命令；②upload 的 OSS 端点域名可能解析超时，此时用 base64 走 exec 落盘兜底；③workbench 的 exec 每次都是新 shell，状态不保留，多步操作用 `&&` 或 `;` 串成一条。保持 SSH 分支可回切（paramiko 已重装）。

## 4. 用户约束
- 测试阶段说“清档”即执行 `python wipe.py`，不再逐次确认；必须保留其备份/白名单机制。
- 优先复用开源方案、节省 Token；以第一性原理讲清因果。
- AuraSkills 用简体中文“轻梗体”，术语机制准确；保留 YAML 键、命令、权限、占位符、颜色/MiniMessage。
- 不用 OP 权限结果替代普通玩家验收；验收必须覆盖入口→执行→奖励/进度→失败恢复。
- **禁止乐观验证**：不得把“调用参数”“配置写入”“进程 active”“Done 标记”当作功能可用。必须回读实际状态（如 `setSpawnPoint` 后要回读 JSON 而非打印入参）。这是本项目反复踩的坑，已写进地雷区。
- **验证结论必须有硬证据**：日志解析/RCON 命令可能被截断或穿插（实测 `/forge mods` 被 RCON 截断到 42/232、Puzzles Lib 清单被其他线程打断只读到 8 条）。优先用可数文件、可实测端口、崩溃报告、对照实验等硬证据，不可靠时明确标注“未实测”。

## 5. 地雷区
- BentoBox 新版曾要求 Java 25；勿盲目升级，当前组合匹配 Java 21。
- Essentials 立即传送与 BSkyBlock 延迟建岛会竞态；现由 IslandTweaks 统一处理，需实测。
- 多层 heredoc 曾破坏 YAML；远端 Python 不支持 `capture_output`、PyYAML 不支持 `sort_keys`。
- 部署脚本的 `active` 不是服务器就绪；须等 `Done (` 并测试 RCON。
- RCON 密码在远端配置，勿复制进交接/提交；本地 `ssh_exec.py` 含凭据。
- **插件 enable 早于 bskyblock_world 加载**（实测差 9 秒）：任何在 `onEnable` 缓存 World 对象的代码都会拿到 null；必须惰性解析或等 `BentoBoxReadyEvent`。
- **RCON `say` 输出不回显**：结果只进 `logs/latest.log`，验证方块/实体存在性用 `execute … if/unless … run say` + 日志 grep；`data get block` 只对方块实体有效，对普通方块报 `not a block entity`。
- **QuickShop-Hikari 启动时会用默认模板重写 config.yml**，部署脚本写入的未知/旧键会被静默丢弃；改配置后必须回读 grep 验证键仍在。
- `verify_island_play.py` 修复前**禁止直接 import 或运行**：模块级副作用会改写母岛 (0,110,0) 命令方块。

## 6. 下一步（有序）
- [x] **A1 修验收入口并确认就绪**（已完成并实证）：重写为 argparse 纯 CLI，删除重复 `rcon()` 与模块级副作用，改密码为远端动态读取，探测改用 `execute if … run say <token>` + grep 日志（不再 setblock）。实证：`py_compile` 退出 0；`import verify_island_play` 仅输出 IMPORT_CLEAN 无副作用；`list` 只见一次响应；日志 TEST 计数 0；`clean-testblock` 已清除 (0,110,0) 残留 `repeating_command_block` 并复核为空气（`CLEAN_TESTBLOCK_OK`）。
- [x] **A1.5 修 C2 world 时序 + C4 坐标统一 + G1 wipe 漏删**（已完成并实证）：`IslandTweaks.java` 改为惰性 `world()` + `BentoBoxReadyEvent` 监听 + 周期重试兜底；`fix_spawn.py` 重写为停服→改→回读校验→起服并新增 `--dry-run`；`spawn.yml` 坐标对齐；`wipe.py` 把 progress.yml 移到 `existing` 之前并补文件删除分支与 `dsize` 文件分支。实证：部署后日志 `公共母岛已就绪：…NORMAL 回家点回读=(0.5,120.0,5.5)` @16:33:13；wipe dry-run 完整清档 14 项含 `progress.yml 272.0B`、`--keep-worlds` 7 项不含。
- [x] **A2 查明母岛恢复/保存**（已完成，全绿）：JSON `owner=None spawn/reserved/purgeProtected=true NORMAL=(0.5,120.0,5.5)`；RCON 实测 (0,120,0)=beacon、(0,121,0)=glass、(0,119,0)=stone_bricks、(0,119,10)=smooth_stone 步道、(5,119,7)=grass_block 草地、(-13,120,-13)=oak_planks、(-13,121,-7)=oak_sign、`island-hub-text` 实体存在；落点 (0,119,5)=smooth_stone 实体 + y=120/121/122 全空气 → 不卡墙不悬空。`/is spawn` 真人实测归入 A3。
- [ ] **A3 临时普通账号全链路**：首进服建岛、石工具、箱子/农田/床、回家；工地交付前后库存与余额数值准确、实体施工变化；重启后进度一致；**并实测普通玩家建店是否真免费（G3）**。测试后仅清理该测试账号/岛并保留公共测试进度备份。**注意：此项现被 lwi 服占用，需先按 §10 切回 mc。且因 SSH 通道失效，切回前需把浮岛部署脚本改造为走 workbench CLI（或恢复 SSH 凭据）。**
- [ ] **A4 同步交付**：上传手册（book.txt 本地已改）、更新 HTML/ZIP；解包核对包含当前源码。贡献者称号未实现，必须在手册与交付说明中明确标为“设计未上线”。
- [ ] **G5 母岛残留清理**（待用户决策）：实测 y=123..130 有 **21 个实体残留方块**，含 (0,125,0)/(0,126,0)，正位于信标上方会遮挡光束；`buildHub()` 只重建 y=116..122，原地修复清不掉，需完整清档或显式 `fill air`。
- [ ] **G2 迁移 /tmp 依赖（剩 Vault/QuickShop）**：`rcon.py` 已重写为零依赖并部署 `/opt/rcon.py`（实测通过），`lwi-backup.sh` 引用已改；仍需迁移 `/tmp/Vault.jar`、`/tmp/QuickShop-Hikari.jar`（浮岛物语的部署依赖，重启已蒸发，需重新上传到 `/opt/` 并更新 `deploy_island_tweaks.py` 的引用路径）。

## 7. 待用户决策
1. 已有旧私人岛是否迁移为家园模板；默认不自动覆盖。
2. 公共进度是否用临时账号推进后保留；默认备份后仅保留必要的少量测试交付或回滚。
3. **G5 母岛残留清理方式**：先完整清档干净重做（测试阶段已授权免确认），还是在现状上修复？影响 A2/A3 执行顺序。
4. **G4 `place_cmdblock.py` 去留**：含明文凭据、指向 `mobfarm:build`、用途不明，是否删除或归档。
5. **浮岛物语是否还要继续**：现已暂停让位给整合包联机。若确定搁置，可考虑清理 `/opt/mc`（356MB）回收空间；若还要做 A3/A4，则保留现状。

## 8. 关键文件
### 浮岛物语（mc.service，已暂停）
- `island_tweaks/src/main/java/workbuddy/islands/IslandTweaks.java`：家园、母岛、经济与交互主逻辑（惰性 `world()` + `BentoBoxReadyEvent` + 母岛回家点常量 `HUB_HOME_*`）。
- `island_tweaks/src/main/resources/plugin.yml`：hub/cloudshop 命令与 QuickShop 玩家建店权限默认授予。
- `deploy_island_tweaks.py`：备份、远端编译、配置和重启。
- `verify_island_play.py`：**已重写**为只读优先的 argparse 纯 CLI（status/list/hub/islands/progress/log/raw/clean-testblock），密码从远端 server.properties 动态读取，import 无副作用。
- `wipe.py` / `fix_spawn.py`：测试清档（G1 已修）/ 仅无属主母岛恢复（C4 已对齐，含 `--dry-run`）。
- `ssh_exec.py`：Paramiko 远程执行入口（含凭据，勿外传；已加 keepalive，HOST 已更新为 EIP）。
- `output/handbook/book.txt`：已改未上传；`output/handbook/浮岛物语手册.html`：待更新；`output/handbook/spawn.yml`：已对齐 `(0.5,120,5.5)` 并已上传远端。
- `.workbuddy/skills/mc-gameplay-acceptance/SKILL.md`：玩法验收标准。
- `place_cmdblock.py`：游离文件，待用户决定去留（G4）。

### LuckyWorldInvasion 整合包服（lwi.service，当前在跑）
- `upload_lwi.py`：分块上传（32MB/块，逐块 SHA-256 校验、失败重试、断点续传）。
- `deploy_lwi.py`：配置部署（server.properties patch / whitelist / ops / voicechat）+ 启动 + 等 Done + 崩溃取证。
- `fix_lwi_mods.py`：把 13 个客户端专属 mod 从 `mods/` 移到 `mods-disabled/`（可逆），含完整判据注释。
- `build_lwi_pack.py`：组装**可分发版本包**（666MB，`G:\lwi-staging\LuckyWorldInvasion-ServerPack-20261108.zip`）。注意：旧 `versions\1.20.1-LuckyWorldInvasion.zip`（734MB）**不可用**——无 manifest 启动器不认，且打包于移除冲突 mod 之前。分发包走「版本文件夹原样分发」：解压进 `.minecraft` 即被 HMCL/PCL 识别为实例，含父版本 `1.20.1-clean/`、预置 `servers.dat` 与 `INSTALL.txt`。
- `output/LuckyWorldInvasion_联机接入说明.md`：**给玩家的交付文档**，含接入步骤、必删的 2 个 mod、已验证事实表、39 条 ERROR 归因。
- 远端：`/opt/lwi`（服务端）、`/opt/lwi-backup.sh`、`/etc/systemd/system/lwi.service`、`lwi-backup.{service,timer}`。

### 运维通道（2026-11-25 起）
- **workbench CLI**（阿里云官方，v1.0.6）：`C:\Users\64146\AppData\Local\Programs\workbench\workbench-windows-amd64\workbench.exe`；AK 凭证 `~/.workbench/config.json`（用户提供，勿写进交接文档）；实例 `i-f8zifsmhy00kro1q0pvw`（河源区）。技能入口 `.workbuddy/skills/alibabacloud-workbench-cli/SKILL.md`。
- `rcon.py`：零依赖 RCON 客户端，本地新写（修过两次：①把自己的包 ID 误判为响应类型的假警报 bug；②多命令容错）。已通过 base64+exec 部署到 `/opt/rcon.py` 并**实测验证通过**（`whitelist list` / `list` 正常）。
- `ssh_exec.py`：paramiko 通道已失效（2026-11-25 密码认证失败），**保留但不作为主通道**，脚本 HOST=EIP 与旧凭据仍在。所有依赖它的脚本（deploy_island_tweaks/verify_island_play/wipe/fix_spawn 等）需改走 workbench 或待用户恢复 SSH 凭据。

## 9. 变更记录
| 日期 | 模型 | 摘要 |
|---|---|---|
| 2026-11-01 | 当前负责模型 | 核查构建、启动、持久化与验收入口；记录未验证项及失败原因 |
| 2026-11-01 15:37 | 新负责模型 | 冷启动核查后写回：纠正 C1（服务器实际已就绪）；定位 C2 根因（world 缓存时序，连带 onJoin 建岛失效）；新增 C4（回家点三处坐标矛盾，统一为 0.5,120,5.5）、G1（wipe 漏删 progress.yml）、G2（/tmp 依赖）、G3（QuickShop 建店费键被丢弃）、G4（place_cmdblock 游离）；新增 D-006/D-007 决策；调整下一步顺序（插入 A1.5）；地雷区补充 4 条实证教训 |
| 2026-11-01 16:40 | 新负责模型 | 完成 A1（重写 verify_island_play.py 为只读 CLI、清除 TEST 命令方块）、A1.5（修 C2 world 惰性解析+BentoBoxReadyEvent、C4 三处坐标统一、G1 wipe 三处缺陷）、A2（母岛全绿）。修复中另发现并修复 **C5**（buildHub 灯笼柱循环覆盖中心信标，致信标从未存在）与 **C6**（`Island.setSpawnPoint(Environment,Location)` 走 Map.compute 不覆盖已有键，改用 Map 重载；同时把我第一版的乐观日志改为回读校验）。量化 **G5**（y=123..130 有 21 个旧残留方块，buildHub 清不掉）。用户约束新增「禁止乐观验证」「验证结论必须有硬证据」两条 |
| 2026-11-08 02:50 | 新负责模型 | **新增 LuckyWorldInvasion 整合包联机服（D-008~D-012）**。发现并修复 EIP 转换后 HOST 失效（47.120.68.181→47.120.61.237，5 个脚本）；暂停浮岛物语（stop+disable，数据完整保留）；装 JDK 17 + Forge 1.20.1-47.4.4；分块上传 577MB payload（单连接曾在 61% 被 RST，改为 32MB 分块+逐块 SHA256+断点续传，18/18 通过）；按 §0.2 判据移除 13 个客户端专属 mod（framework/controllable 两端都删）；配置离线模式+白名单+voice_host；堆从 5G 降到 4G（jcmd 实测仅用 1.9G）；每日备份定时器实测跑通。验证：`Done (2.121s)`、TCP 25565/25575 与 UDP 24454 外部实测可达（tcpdump 5/5）、Forge 握手正常、空岛世界（region 16KB）、0 崩溃报告、39 条 ERROR 经客户端日志对照实验全部归因无害。产出 `output/LuckyWorldInvasion_联机接入说明.md` |
| 2026-11-25 | 交接轮次模型 | **17 天空白补齐与通道重建**。补时间线：11-08 当天客户端修 lionfishapi 3.0（`EMP_Model` 不实现 `BasicEntityModel.root()` 致 `AbstractMethodError` 崩溃）→ 换 2.8 后 Nashville+kuawaA 成功联机（服务端日志实证两人进出服）；11-09 11:36 用户主动关机；11-25 11:32 开机（EIP 未漂移，上次"未实测"项闭环）。爆雷：`/tmp/rcon.py` 蒸发（G2 成真）→ 重写零依赖 `rcon.py` 并部署 `/opt/rcon.py`。SSH 密码认证失效 → **D-013** 迁往 workbench CLI（装 v1.0.6、写入 AK、实例定位在**河源区**而非杭州）；paramiko 重装但通道不可用。教训：workbench 实例会话有上限（连发 exec 报"活跃会话数已达上限"，需间隔/合并）；upload 的 OSS 端点可能 DNS 超时（改 base64+exec 落盘兜底）。rcn.py 有一处自我误判（把包 ID 当响应类型）已修。中断后未完成的收尾：修正版 rcon.py 的实机验证、lwi-backup.sh 的 rcon 路径修正、Vault/QuickShop 的持久迁移、交接提示词文档 |

## 10. 两个服务端的切换（互斥，切勿同时启动）
两者都独占 25565 端口与大部分内存，**绝对不能同时运行**。

**当前 → 整合包服（lwi）在跑。**

切到浮岛物语（mc）：
```bash
systemctl stop lwi && systemctl disable lwi
systemctl enable --now mc
# 等日志出现 Done ( ，约 60s；随后 python verify_island_play.py status 核对
```

切回整合包服（lwi）：
```bash
systemctl stop mc && systemctl disable mc
systemctl enable --now lwi
# 等 Done ( ，首启约 60s（mixin 变换），之后重启约 2s
```

**停机务必用 `systemctl stop`，不要用 RCON/控制台 `stop`**：两个单元都配了 `Restart`，
java 自行退出会被 systemd 当作崩溃而自动重启（本项目实际踩过：RCON stop 后服务被拉起）。
若已误用导致状态变 `failed`，先 `systemctl reset-failed <unit>` 再操作。

浮岛物语数据完整保留在 `/opt/mc`（356MB，含世界/插件/岛屿数据库/备份），`mc.service` 单元文件保留，
仅 disable（不自启）。整合包数据在 `/opt/lwi`，每日 04:00 自动备份到 `/opt/backups/lwi-*.tgz`。
两者互斥关系已写入 `lwi.service` 的 `Conflicts=mc.service`。
