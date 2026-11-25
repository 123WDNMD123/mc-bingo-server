# BINGO 26.3 客户端整合包 v1.0.0

面向 **HMCL / PCL2** 的一键导入整合包，连接 `47.120.61.237:25565`。

## 下载

`BINGO-26.3-HMCL-PCL2.zip` — 51,547,569 字节

**SHA-256**
```
dc43a7ef3fc00bab5dc1a6289fb309cc5ec8378193f4ee1c6e1a3130d95fed3d
```

校验（PowerShell）：
```powershell
Get-FileHash .\BINGO-26.3-HMCL-PCL2.zip -Algorithm SHA256
```

## 安装

1. HMCL：版本列表 →「安装整合包」→ 从本地文件导入
   PCL2：下载 →「整合包」→ 从本地文件安装
2. 启动器自动下载 Minecraft **26.3** + Fabric Loader **0.20.1** + 10 个模组（需联网）
3. 需要 **Java 25**（26.3 官方要求），启动器一般会自动下载
4. 选**离线登录**，填昵称即可进服

## 下载失败的兜底

ZIP 内 `overrides/mods-offline/` 已附带**全部 10 个模组本体**，
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

| 模组 | 版本 |
| --- | --- |
| Fabric API | 0.166.2+26.3 |
| Yet Another Bingo | 2.15.1+mc26.3 |
| Simple Voice Chat | 2.6.27+26.3 |
| Lithium | 0.26.4+mc26.3 |
| FerriteCore | 9.0.0 |
| Sodium（仅客户端） | 0.9.3+mc26.3 |
| REI | 26.3.824 |
| Cloth Config | 26.3.159 |
| Architectury | 22.1.7 |
| Fabric Language Kotlin | 1.14.2 |

## 已知未验证项

- HMCL / PCL2 **实机导入未测试**；已做 ZIP 结构、10 个模组哈希、`servers.dat` NBT 解析回环的严格静态校验
- 真人客户端画面、HUD 卡面显示、麦克风音质未实机确认

完整说明见仓库内 `output/BINGO-26.3-玩家手册.md`。
