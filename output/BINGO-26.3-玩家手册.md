# BINGO 26.3 玩家手册

> 服务器地址：**47.120.61.237:25565**　语音端口：**UDP 24454**
> 游戏版本：**Minecraft Java 版 26.3**（需 **Java 25**）　模组加载器：**Fabric 0.20.1**
> 玩法：**全员同队合作 BINGO**，共享一张卡，横/竖/斜连成一条线即通关
> 登录：**离线登录，默认可进**，仅黑名单玩家被拦

---

## 一、五分钟上手

1. 下载 `BINGO-26.3-HMCL-PCL2.zip`（约 51 MB）。
2. 打开 HMCL 或 PCL2 → 找到「安装整合包 / 导入整合包」→ 选择这个 ZIP。
3. 等启动器自动装好 Minecraft 26.3、Fabric 0.20.1 和 10 个模组（**需要联网**）。
4. 在启动器里选**离线登录 / 离线模式**，随便填一个昵称（如 `XiaoMing`）。
5. 启动游戏 → 多人游戏 → 列表里已经有「BINGO 26.3」→ 双击进服。
6. 按住 **V** 说话，按 **G** 打开语音界面。

---

## 二、导入整合包（分启动器）

### HMCL
- 主界面左侧「版本列表」→ 右上「安装整合包」→「从本地文件导入」→ 选 ZIP。
- 或直接把 ZIP 拖进 HMCL 窗口。

### PCL2
- 顶部「下载」→「整合包」→「从本地文件安装」→ 选 ZIP。
- 也可把 ZIP 拖到 PCL2 主界面。

### 装完检查
版本应为 `26.3`，加载器 `Fabric 0.20.1`，`mods` 文件夹里有 **10 个 jar**。

### 下载失败怎么办（重要）
模组从 Modrinth 官方 CDN 下载，国内网络可能很慢或超时。本 ZIP 已经内置兜底：

- 解压 ZIP，找到 `overrides/mods-offline/` 文件夹，里面是**全部 10 个模组本体**（已校验哈希）。
- 把它们全部复制到该游戏版本的 `mods` 文件夹，覆盖同名文件即可。
- 这些 jar 与索引里记录的 SHA-1/SHA-512 完全一致，可放心使用。

### Java 版本
26.3 官方要求 **Java 25**。启动器通常会自动下载；若提示 Java 版本过低，在
「版本设置 → Java 路径」里手动指定 Java 25。

---

## 三、进服与登录

- **无需正版账号**。启动器里选「离线登录」，填昵称即可进服。
- 昵称建议用英文/数字，避免特殊符号；**昵称就是你的身份**，换昵称等于换角色（背包、进度都会变新的）。
- 服务器上限 **10 人**。
- 默认可进，不设白名单；只有被列入黑名单的昵称会被拒绝。

---

## 四、玩法：合作 BINGO

### 核心规则
- **全员同队**（服务器已设 `teamCount=1`，自动分配队伍），大家共用**一张宾果卡**。
- 卡面 5×5 共 25 个目标物品。**任何人**拿到某个目标物品，整队一起记进度。
- **横、竖、斜任意连成一条线**即通关（目标 = 1 条线）。
- 已关闭 PvP（队友之间不会互相伤害），开启死亡保留物品栏，适合合作。

### 怎么算「拿到」
把目标物品**拿进背包**即可判定，不需要交给谁、也不需要放在特定位置。

### 开局流程
1. 玩家进服后处于准备阶段（pregame）。
2. 全员就位后，输入 `/ready` 投票加速开局；或由管理员执行 `/bingo start`。
3. 倒计时结束后进入游戏，卡面出现在屏幕左上角（HUD）。
4. 连成一线后自动结算，展示本局用时与完成情况。

### 常用命令
| 命令 | 作用 |
| --- | --- |
| `/ready` | 投票准备，人齐后可提前开局 |
| `/bingo` | 查看当前玩法配置（目标、难度、特色） |
| `/bingo book` | 领取玩法说明书 |
| `/bingoprefs` | 调整个人显示偏好（计分板、提示、夜视等） |
| `/bingo stats` | 查看自己的 BINGO 统计 |
| `/g <消息>` | 全局聊天（默认聊天是队内） |

### 配方查询
装了 **REI（Roughly Enough Items）**：
- 背包界面右侧是物品列表。
- 鼠标悬停物品按 **R** 看合成配方，按 **U** 看它能用来做什么。
- 服务器已开启配方解锁，配方会随进度自动解锁。

---

## 五、语音通话

### 按键
| 按键 | 功能 |
| --- | --- |
| **V**（按住） | 说话 |
| **G** | 打开语音界面 |
| 其余 | 选项 → 按键绑定 → 「语音通话」分类里自定义 |

### 语音范围规则（按你的要求配置）
- **准备阶段/大厅**：附近语音，离得近才听得到（默认 48 格内）。
- **开局之后**：**全队一个语音组**，队友之间**不限距离**都能听清；不存在对手串音（本服全员同队）。

### 听不到声音的排查
1. 语音走 **UDP 24454**，服务器安全组已放行。检查**本机防火墙/路由器**是否拦 UDP。
2. 按 G 打开语音界面，确认麦克风设备选对、音量不为 0。
3. 确认没有按到「禁用麦克风」快捷键。
4. 校园网/公司网络常封 UDP，换热点测试即可确认。

> 说明：因为服务器是离线模式，语音加密强度低于正版验证服，属预期行为，
> 日志里的 `Voice chat encryption is not secure` 提示可以忽略。

---

## 六、装了哪些模组（10 个）

| 模组 | 版本 | 作用 | 端 |
| --- | --- | --- | --- |
| Fabric API | 0.166.2+26.3 | 模组基础库 | 双端 |
| **Yet Another Bingo** | 2.15.1+mc26.3 | BINGO 玩法本体（自带简体中文） | 双端 |
| Simple Voice Chat | 2.6.27+26.3 | 在线语音 | 双端 |
| Lithium | 0.26.4+mc26.3 | 服务端逻辑优化 | 双端 |
| FerriteCore | 9.0.0 | 内存占用优化 | 双端 |
| **Sodium** | 0.9.3+mc26.3 | 渲染性能优化 | **仅客户端** |
| REI | 26.3.824 | 配方查询 | 双端 |
| Cloth Config | 26.3.159 | 配置界面库 | 双端 |
| Architectury | 22.1.7 | 跨加载器兼容库 | 双端 |
| Fabric Language Kotlin | 1.14.2 | BINGO 的 Kotlin 运行时（硬依赖） | 双端 |

**没有**新增矿物、生物或世界生成模组 —— 保持原版生存手感，只做轻量竞技。

---

## 七、管理员运维

> 以下内容面向服主，普通玩家可跳过。

### 服务与目录
- 服务端目录：`/opt/bingo`
- systemd 服务：`bingo.service`（已 `enable`，开机自启）
- 启动命令：`java -Xms2G -Xmx4G -XX:+UseZGC -jar fabric-server-launch.jar nogui`
- Java：`/opt/bingo/jdk-25.0.5.1+2`（Temurin 25，官方 SHA-256 已核验）
- 与旧服互斥：单元里写了 `Conflicts=mc.service lwi.service`

```bash
systemctl status bingo      # 查看状态
systemctl restart bingo     # 重启
journalctl -u bingo -f      # 实时日志
```

### 黑名单管理（唯一的准入控制）
```bash
# 通过 RCON 或游戏内管理员执行
ban <昵称> [原因]        # 拉黑
pardon <昵称>            # 解除
banlist players          # 查看名单
ban-ip <IP>              # 按 IP 拉黑
pardon-ip <IP>           # 解除 IP
```
名单文件：`/opt/bingo/banned-players.json`、`banned-ips.json`。

### 玩法配置（改之前务必先停服）
配置文件在 `/opt/bingo/config/yet-another-minecraft-bingo/`：
- `game-options-default.json`：**默认模板**，新一局从这里读
- `game-options.json`：运行时状态，会被服务端回写

> **坑（已实测确认）**：服务运行中改 `game-options.json` 会被内存状态覆盖。
> 正确做法：`systemctl stop bingo` → 同时改**两个文件** → `systemctl start bingo`。

另外，**PvP 实际由世界 gamerule 控制**，不是只看 JSON：
```bash
gamerule pvp false        # 关闭 PvP（当前已关）
```

当前合作配置：`teamCount=1`、`teamAutoShuffle=true`、目标 `lines=1`、
`isPvpEnabled=false`、`isKeepInventory=true`。

### 语音配置
- `/opt/bingo/config/voicechat/voicechat-server.properties`
  - `voice_host=47.120.61.237`（**必须是公网 IP**，否则客户端连不上语音）
  - `port=24454`、`enable_groups=true`、`max_voice_distance=48.0`
- `/opt/bingo/config/yet-another-minecraft-bingo/voicechat.json`
  - `useCombinedGroupAlways=true` → 全员一个组，实现队内不限距离通话

### 备份
- 脚本：`/opt/bingo-backup.sh`（先 RCON `save-off` + `save-all flush`，再打包，最后 `save-on`）
- 定时器：`bingo-backup.timer`，**每天 04:30** 执行，已启用
- 产物：`/opt/backups/bingo-<时间戳>.tar.gz` + `.sha256`，保留最近 **7** 份
- 已实跑验证一次：200 MB，`sha256sum -c` 校验 **OK**

```bash
systemctl start bingo-backup.service    # 立即备份一次
systemctl list-timers bingo-backup.timer
```

### 端口与安全组
| 端口 | 协议 | 用途 | 对外 |
| --- | --- | --- | --- |
| 25565 | TCP | 游戏 | 已放行 |
| 24454 | UDP | 语音 | 已放行 |
| 25575 | TCP | RCON 管理 | **未放行**（仅本机，安全） |

RCON 密码在 `server.properties` 的 `rcon.password`，**请勿外泄**。

---

## 八、旧服备份在哪

两套旧服都已**完整冷备到本机**后才退役，可随时恢复：

| 备份 | 大小 | SHA-256 |
| --- | --- | --- |
| `output/server-backups/FloatingIsland-20261125.tar.gz` | 305,510,916 B | `ad49010c02f5b646441808b6c919392e28cba578219dc2095655658abe6727aa` |
| `output/server-backups/LuckyWorldInvasion-20261125.tar.gz` | 804,279,460 B | `a5401f6b48dbfb8b027bf33c5bf4bdd37f4faa46756245709c9a5d762c44ffe9` |

云端原目录只是**移走**（未删除）：`/opt/mc-retirement.Mlftc1TJ/{mc,lwi}`，
历史备份 `/opt/backups` 也保留着。

---

## 九、本次验收做了什么（硬证据）

| 项目 | 结果 |
| --- | --- |
| 服务端启动 | `Done (4.328s)!`，`systemctl is-active` = active |
| 版本握手 | 真实 MC 协议查询返回 `26.3 / protocol 777`，上限 10 人 |
| 公网连通 | 本机 TCP 连 47.120.61.237:25565 成功，47 ms |
| 三端口监听 | 25565/TCP、25575/TCP、24454/UDP 全部在听 |
| 离线登录 | 模拟客户端 `LOGIN_SUCCESS`，服务端日志 `joined the game` + 实体 ID + 坐标 |
| 双人同服 | `There are 2 of a max of 10 players online` |
| BINGO 开局 | 日志 `GameState changed: countdown -> playing`，计分板 `Minecraft Bingo` 建立 |
| 合作规则生效 | 计分板显示 `Goal: 1 line`、`Features: None`（PvP 已关） |
| 语音集成 | 日志 `Voice host is '47.120.61.237'`、`Voice chat server started at port 24454`，玩家接入/断开有记录 |
| 模组校验 | 9 个服务端模组 SHA-1 + SHA-512 **全部匹配** Modrinth 官方值 |
| 客户端包 | ZIP 完整性 OK，10 条索引 + 10 个离线 jar 哈希一致，`servers.dat` NBT 解析回环通过 |
| 备份 | 实跑一次 200 MB，`sha256sum -c` = OK，定时器已启用 |

### 尚未做的验证（如实说明）
- **没有真人客户端实测**：以上进服/开局/语音接入是用自写协议客户端 + RCON + 服务端日志验证的。
  真人的画面、HUD 卡面显示、实际麦克风通话音质需要你或玩家实机确认。
- **HMCL / PCL2 实机导入未测**：按你的要求免除。已改为对 ZIP 做结构、哈希、NBT 的严格静态校验。
- **完整通关结算未跑完**：已验证到 `playing` 状态与共享计分板，但没有真人集齐一条线走到结算画面。

---

## 十、遇到问题

| 现象 | 原因与处理 |
| --- | --- |
| 进不去服，提示验证失败 | 启动器要选**离线登录**，不是正版登录 |
| 版本不匹配 | 确认是 **26.3** + Fabric **0.20.1**，不是 26.2 或 Forge |
| 启动崩溃提示缺 Kotlin | `fabric-language-kotlin` 没装上，从 `mods-offline/` 补 |
| 模组下载卡住 | 用 `overrides/mods-offline/` 里的 jar 手动放进 `mods` |
| 能进服但没声音 | UDP 24454 被本地网络拦了，换网络或放行 UDP |
| 卡面不显示 | 确认装了 BINGO 客户端模组；按 `/bingo book` 拿说明书 |
| 昵称换了进度没了 | 离线模式下昵称即身份，请固定使用同一昵称 |
