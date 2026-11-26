# BINGO 26.3 客户端整合包 v1.1.0

面向 **HMCL / PCL2** 的一键导入整合包，连接 `47.120.61.237:25565`。

## v1.1.0 新增

- **连锁挖矿（VeinMiner 2.14.0）**：**按住 Shift** 挖掘即一次挖掉整片相连同类方块。
  支持矿石（需镐）、原木与树叶（需斧）。上限 256 个、搜索半径 2、正常消耗耐久。
  不按 Shift 就是普通单个挖掘，不会误伤。
- **联机皮肤（Skin Restorer 2.11.1，服务端）**：离线登录也能有皮肤。
  进服自动按昵称取皮肤，可用 `/skin set <正版昵称>` 或 `/skin set <图片URL>` 更换。
  **客户端不需要装任何皮肤模组** —— 该模组仅服务端，整合包已硬排除。
- **修正死亡保留物品栏**：26.3 的规则名是 `keep_inventory`（带下划线），
  且 BINGO 的 `isKeepInventory=true` 不会同步到世界 gamerule。此前世界实际是 `false`，本次已改为 `true`。

## 下载

`BINGO-26.3-HMCL-PCL2.zip` — 52,252,460 字节

**SHA-256**
```
394b8af50bc612f09ea8e4d46b4754082e47b197cf1b9f3cea6e94590fdddadd
```

校验（PowerShell）：
```powershell
Get-FileHash .\BINGO-26.3-HMCL-PCL2.zip -Algorithm SHA256
```

> 国内直连 GitHub Release 可能较慢或中断，建议用下载工具或镜像加速。
> 命令行可用 `curl -C -` 断点续传。

## 安装

1. HMCL：版本列表 →「安装整合包」→ 从本地文件导入
   PCL2：下载 →「整合包」→ 从本地文件安装
2. 启动器自动下载 Minecraft **26.3** + Fabric Loader **0.20.1** + 11 个模组（需联网）
3. 需要 **Java 25**（26.3 官方要求），启动器一般会自动下载
4. 选**离线登录**，填昵称即可进服

**从 v1.0.0 升级**：建议新建一个版本导入，或把旧版本 `mods` 里的 jar 换成包内
`overrides/mods-offline/` 的 11 个。**不要**自行往客户端添加 Skin Restorer。

## 下载失败的兜底

ZIP 内 `overrides/mods-offline/` 已附带**全部 11 个模组本体**，
与索引记录的 SHA-1/SHA-512 完全一致。若 Modrinth CDN 下载超时，
把它们复制进该版本的 `mods` 文件夹即可。

## 已预置

- 服务器地址 `47.120.61.237:25565`（多人游戏列表可见）
- 简体中文界面
- 语音按键：**V** 按住说话，**G** 打开语音界面

## 玩法

全员同队合作，共享一张 5×5 宾果卡，**横/竖/斜连成一条线**即通关。
PvP 已关闭，死亡保留物品栏。按 **R** 查配方（REI）。

## 模组清单

**客户端 11 个**：

| 模组 | 版本 |
| --- | --- |
| Fabric API | 0.166.2+26.3 |
| Yet Another Bingo | 2.15.1+mc26.3 |
| Simple Voice Chat | 2.6.27+26.3 |
| **VeinMiner** | **2.14.0** |
| Lithium | 0.26.4+mc26.3 |
| FerriteCore | 9.0.0 |
| Sodium（仅客户端） | 0.9.3+mc26.3 |
| REI | 26.3.824 |
| Cloth Config | 26.3.159 |
| Architectury | 22.1.7 |
| Fabric Language Kotlin | 1.14.2 |

**服务端额外 1 个（客户端不要装）**：Skin Restorer 2.11.1+26.3

## 已知未验证项

- HMCL / PCL2 **实机导入未测试**；已做 ZIP 结构、11 个模组哈希、`servers.dat` NBT 解析回环的严格静态校验
- **连锁挖矿的实际连锁动作未实机跑**：已证明模组加载、`#c:ores` 与 `#minecraft:logs` 标签可解析、配置重启后持久化
- **皮肤在真人客户端的显示效果未确认**：已证明服务端取到并存储了带 Mojang 官方签名的材质数据
- 真人客户端画面、HUD 卡面显示、麦克风音质未实机确认

完整说明见仓库内 `output/BINGO-26.3-玩家手册.md`。