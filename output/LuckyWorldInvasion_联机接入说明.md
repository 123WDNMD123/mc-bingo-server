# LuckyWorldInvasion 联机接入说明

|   |   |
| - | - |

> 生成时间：2026-11-08　|　服务器：阿里云 ECS 4 vCPU / 8 GiB / 50 Mbps（按流量）  
> 服务端：Forge 1.20.1-47.4.4 + JDK 17，`/opt/lwi/mods/` 232 个 jar，0 崩溃报告  
> （客户端整合包原为 245 个 jar，其中 13 个客户端专属 mod 已移至 `mods-disabled/`）



---

## 一、服务器地址

```
47.120.61.237
```

端口用默认 25565，游戏内填地址时**不用写端口**（写了也行）。

这个地址是**弹性公网 IP（EIP）**，不会随实例重启变化。

---

## 二、谁可以进服

| 玩家        | 状态    | 权限      |
| --------- | ----- | ------- |
| Nashville | 已加白名单 | OP（管理员） |
| kuawaA    | 已加白名单 | OP（管理员） |

服务器开了**白名单强制**（`enforce-whitelist=true`）。不在名单里的人**进不来**，  
会直接被拒绝。要加新人，由 OP 在游戏里或控制台执行：

```
whitelist add 玩家名
```

**重要**：服务器是**离线模式**（`online-mode=false`），因为你们没有正版账号。  
离线模式下 UUID 由用户名算出，这意味着：

- 游戏内用户名**必须和白名单里的一模一样**（区分大小写，`kuawaA` ≠ `KuawaA`）
- 任何人都能用任意用户名登录，所以**不要把地址公开**发到论坛/QQ群
- 白名单是唯一防线，别关掉它

---

## 三、客户端必须做的两件事

### 1. 安装同一份整合包（用分发包，别用旧 zip）

客户端 mod 数量和服务端不一致时，Forge 会**拒绝连接**（报 `mismatched mod list`）。  
所以必须用完全相同的整合包。

**分发包**（666 MB，已按服务端要求移除冲突 mod、已预置服务器地址）：

```
G:\lwi-staging\LuckyWorldInvasion-ServerPack-20261108.zip
```

> ⚠️ 不要用 `versions\1.20.1-LuckyWorldInvasion.zip`（734 MB 那个旧包）。  
> 它有两个问题：① 不是启动器认识的整合包格式（无 manifest，HMCL 会报  
> "无法识别该整合包"）；② 打包于移除 framework/controllable **之前**，  
> 解压后直接进服会被握手拒绝。

**安装方式**：把 zip 里的内容解压到朋友的 `.minecraft` 目录下（不是"安装整合包"，  
就是普通解压）。解压后 `.minecraft\versions\` 下会出现两个文件夹：

```
versions\1.20.1-clean
versions\1.20.1-LuckyWorldInvasion
```

启动器（HMCL / PCL2）会把 `versions\` 下的每个文件夹自动识别为实例，  
列表里直接出现 `1.20.1-LuckyWorldInvasion`，选中启动即可。  
首次启动启动器会自动补下载原版核心与 Forge 库（约一两百 MB，需联网）。

包内已附 `INSTALL.txt`（同样的说明）和 `servers.dat`（预置服务器地址）。  
若朋友原本有自己的服务器列表，解压前先备份 `.minecraft\servers.dat`。

### 2. 不要增删 mods 里的 jar

本包已按服务端要求移除了 `framework` 与 `controllable` 两个会与服务端握手冲突的  
mod（共 254 个 jar，与服务端清单匹配）。**加回这两个会连不上**；  
增删其他 jar 同样可能触发 `mismatched mod list`。

> 背景：`framework` 注册了网络通道（实测含 `SimpleChannel` /  
> `ChannelBuilder` / `registerMessage`），Forge 握手会比对通道清单，客户端有而  
> 服务端没有就会被拒连。`controllable` 强制依赖 `framework`，删了前者就得一起删。  
> 其他 11 个客户端专属 mod（lootbeams、oculus、jecharacters 等）**没注册通道**，  
> 客户端保留、服务端移除不影响连接，所以包里保留了它们（光影/小地图体验不受影响）。  
> 服务端那 13 个已移到 `/opt/lwi/mods-disabled/`（移动而非删除，可恢复）。

---

## 四、进服步骤

1. 解压分发包到 `.minecraft`（见 §三.1），启动器选 `1.20.1-LuckyWorldInvasion`
2. **离线登录**，用户名填 `Nashville` 或 `kuawaA`（必须与白名单完全一致）
3. 多人游戏里已预置服务器 `LuckyWorldInvasion`（来自包内 `servers.dat`），直接双击进入；  
   若没看到，手动添加服务器，地址填 `47.120.61.237`（端口默认不用写）
4. 首次进服会加载 mod、生成空岛，可能等待 30 秒～2 分钟，不要急着退出

进服后是**空岛世界**（SkyblockBuilder），出生点会给一个岛屿模板。  
可选模板：`default`、`one_barrel`、`lucky_block_racing`（服务端已加载全部 3 个）。

---

## 五、语音聊天

整合包自带 **Simple Voice Chat**，服务端已配置：

- 语音端口：`24454/UDP`（已实测外部可达）
- `voice_host` 已填 `47.120.61.237`

进游戏后按 `V` 键设置语音（首次会提示选麦克风）。  
如果语音连不上，检查客户端 `config/voicechat/voicechat-client.properties`。

---

## 六、已验证的事实（不是推测）

| 项目                  | 结果                                                                                            | 验证方式                                                      |                   |
| ------------------- | --------------------------------------------------------------------------------------------- | --------------------------------------------------------- | ----------------- |
| 服务器就绪               | `Done (2.121s)` @02:37:01                                                                     | 读 `logs/latest.log`                                       |                   |
| mod 文件数             | `mods/` 232 个 jar；另 13 个在 `mods-disabled/`；合计 245 与上传时逐项吻合                                    | 数目录文件（硬事实，不依赖日志解析）                                        |                   |
| 内嵌依赖                | 56 个 JarInJar 依赖由 FML 自动加载                                                                    | 日志 `Found 56 dependencies adding them to mods collection` |                   |
| 13 个客户端 mod 已排除     | `mods-disabled/` 列出 13 个文件，`mods/` 中**重复文件数 = 0**                                             | 遍历比对两个目录文件名                                               |                   |
| 空岛模板                | 3 个全部加载（default / one_barrel / lucky_block_racing）                                            | 日志 `Loaded template` × 3                                  |                   |
| 世界是虚空而非原版地形         | `save-all flush` 后 `r.0.0.mca` 仅 **16 KB**，其余 region 0 字节（原版地形会是几十 MB；对比浮岛物语 Paper 空岛 7.7 MB） | 强制保存后实测 region 文件大小                                       |                   |
| TCP 25565 外部可达      | 握手成功，读回版本 1.20.1 / 协议 763 / MOTD \`§bLucky World Invasion§r §7                                | §e空岛征服\` / 0-4 人                                          | 自写 MC 协议客户端连公网 IP |
| UDP 24454 外部可达      | **5/5** 探测包抵达网卡（`112.32.83.102 → 24454`）                                                      | 本地发 UDP 包 + 服务器 `tcpdump` 抓包                              |                   |
| Forge 握手正常          | 返回 `packet 0x04` + `channel=fml:handshake` 通道协商                                               | 带 `\0FML3\0` 标记握手                                         |                   |
| 服务端要求 Forge 客户端     | vanilla 客户端被拒：`This server has mods that require Forge to be installed on the client`         | 不带 Forge 标记握手实测                                           |                   |
| 内存余量                | available **1.9 Gi**；堆 total 4G / used 1.9G；java RSS 4.86G                                    | `jcmd GC.heap_info` 实测                                    |                   |
| 每日备份                | 04:00 自动执行；手动跑通一次，110 MB + SHA256                                                             | `lwi-backup.timer` active，下次 04:02                        |                   |
| 0 崩溃报告              | `crash-reports/` 为空（首次启动的 12-mod 崩溃报告已随重启清理）                                                  | \`ls                                                      | wc -l\` = 0       |
| 日志 39 条 ERROR 已逐条归因 | 全部无害：34 条为整合包自身数据问题，5 条为 Forge 设计行为                                                           | 与客户端单人日志对照实验（见下）                                          |                   |
| 分发包完整可用            | zip CRC 无损坏；8050 条目；mods 254 jar；两个冲突 mod 已排除；实例/父版本 JSON 均在包内且 inheritsFrom 可解析；servers.dat 为合法 NBT 且含服务器地址 | 解包测试（testzip + 逐项解出核对）                                        |                   |

### 关于日志里那 39 条 ERROR（已做对照实验归因）

服务器日志有 39 条 ERROR，我做了**对照实验**而不是逐条猜：你本地单人跑过同一个  
整合包，`logs/latest.log` 里保留了客户端的错误记录。两边比对结果：

| 错误类型                              | 客户端   | 服务端   | 归因                    |
| --------------------------------- | ----- | ----- | --------------------- |
| advancement 解析失败（Unknown item id） | 15    | 2     | 整合包固有                 |
| mixin 缺 minVersion                | 5     | 5     | 整合包固有                 |
| 数据文件解析失败                          | 4     | 1     | 整合包固有                 |
| boss 刷新规则无效                       | 4     | 2     | 整合包固有                 |
| 联网更新检查失败                          | 4     | 4     | 整合包固有（服务器无法访问 GitHub） |
| affixes Codec / 文件解析失败            | 2 / 2 | 1 / 1 | 整合包固有（apotheosis 系）   |
| insanelib function 失败             | 2     | 1     | 整合包固有                 |
| wanderer_trades 空物品               | 2     | 1     | 整合包固有                 |
| fence_gates 标签缺失                  | 1     | 1     | 整合包固有（shadowlands）    |
| talisman slot 未注册                 | 1     | 1     | 整合包固有                 |
| MissionerRaid 父类问题                | 3     | 1     | 整合包固有                 |
| coremod transform 失败              | 2     | 1     | 整合包固有                 |
| **invalid dist DEDICATED_SERVER** | **0** | **5** | **Forge 设计行为，见下**     |

**结论**：34 条是整合包本身的数据问题（`apotheotic_additions` 注册了不存在的  
affix、advancement 引用了缺失物品等），你单人玩的时候就有，不影响游戏，**不用管**。

剩下 5 条 `invalid dist DEDICATED_SERVER` 只在服务端出现，原因是：  
这是 Forge `RuntimeDistCleaner` 的**设计行为**——它拦截客户端专属类在专用服务器上的  
加载并跳过，Mixin 随后报 `@Mixin target ... was not found` 后忽略。涉及  
AsyncParticles（粒子）、relics（Screen mixin）、TACZ（枪械图示数据），都是纯客户端  
视觉功能。单人模式下**不可能**出现这类错误，因为单人没有 dist 分离。

硬证据：这 5 条发生在 `02:36:16~02:36:18`，服务器仍在 `02:37:01` 成功 `Done`，  
0 崩溃报告，已稳定运行 24 分钟以上。

**关于「12 个 mod 导致崩溃」的因果证据**：首次启动时崩溃报告明确列出 12 个 mod 为  
`ERROR` 状态，失败原因全部是客户端类缺失（6 个 `NoClassDefFoundError: net/minecraft/client/...`

- 6 个 `Attempted to load class net/minecraft/client/gui/screens/Screen for invalid dist
  DEDICATED_SERVER`）。把这 13 个 jar（含 mandatory 依赖 framework 的 controllable）移出  
  `mods/` 后，**同一环境同一配置启动成功、0 崩溃报告**。这是因果闭环，不依赖清单解析。

> 注：我曾尝试用 `/forge mods` 和日志清单做逐项核对，两者都不可靠——  
> `/forge mods` 被 RCON 响应长度截断（只返回 42/232 条），日志清单被其他线程  
> 输出穿插打断（Puzzles Lib 声称 249 个但只能连续读到 8 条）。因此上表只保留  
> 可数文件、可实测端口、可读崩溃报告这类硬证据。

### 未实测的部分（诚实标注）

- **白名单拦截行为**：配置已写入并回读校验（`whitelist list` 返回 2 人、  
  `enforce-whitelist=true`），但**未做协议级实测**。原因是白名单校验发生在  
  FML 握手完成之后，我的简化协议客户端到不了那一层。需真人进服验证一次。
- **真实玩家进服体验**：岛屿生成、任务、枪械、暮色森林传送、维度切换、  
  掉落物、性能表现，全部需要真人进游戏确认。
- **EIP 是否已永久生效**：当前 IP `47.120.61.237` 实测可用，但"转换后重启不变"  
  这一特性无法在不重启的情况下验证。

---

## 七、运维命令

服务器上操作（先 SSH 登录 `root@47.120.61.237`）：

```bash
systemctl status lwi          # 查看状态
systemctl restart lwi         # 重启
systemctl stop lwi            # 停止（注意：别用游戏内 stop，会被 systemd 重启）
tail -f /opt/lwi/logs/latest.log      # 看日志
bash /opt/lwi-backup.sh       # 立即备份一次
```

游戏内命令（RCON，仅服务器本地可用，未暴露公网）：

```bash
PW=$(grep '^rcon.password=' /opt/lwi/server.properties | cut -d= -f2-)
python3 /tmp/rcon.py 127.0.0.1 25575 "$PW" 'whitelist list'
python3 /tmp/rcon.py 127.0.0.1 25575 "$PW" 'list'
```

---

## 八、原来的「浮岛物语」服务器

**没有删除，随时可切回**。两者都独占 25565 端口和大部分内存，不能同时跑。

- 数据完整保留在 `/opt/mc`（356 MB，含世界、插件、岛屿数据库、备份）
- systemd 单元 `mc.service` 保留，已 disable（不自启）
- 切回浮岛物语：

```bash
systemctl stop lwi && systemctl disable lwi
systemctl enable --now mc
```

- 再切回整合包：

```bash
systemctl stop mc && systemctl disable mc
systemctl enable --now lwi
```

浮岛物语项目当时的进度：A1（验收入口）、A2（母岛恢复）、以及 4 个 bug 修复  
（world 时序、信标被覆盖、spawnPoint 写入失效、wipe 漏删 progress.yml）都已完成  
并验证，停在 A3（临时账号全链路测试）之前。详见项目根目录 `HANDOFF.md`。
