#!/usr/bin/env python3
"""移除在服务端崩溃的客户端专属 mod（可逆：移动到 mods-disabled/，不删除）。

处置依据全部来自实测取证，不靠 mod 名字猜测：
  - 崩溃报告给出每个 mod 的失败原因（NoClassDefFoundError 客户端类 /
    "Attempted to load class ... for invalid dist DEDICATED_SERVER"）。
  - 反向依赖扫描：controllable mandatory 依赖 framework，必须同批处理。
  - 网络通道扫描：注册了 SimpleChannel/ChannelBuilder/registerMessage 的 mod，
    客户端有而服务端无会被 Forge 握手以 "mismatched mod list" 拒绝，
    因此这类 mod 必须两端同时移除（framework）。
    未注册通道的 mod 只从服务端移除即可，客户端保留不影响连接。
"""
import sys

from ssh_exec import run

LWI = "/opt/lwi"

# (modId, 文件名, 处置, 依据)
PLAN = [
    ("lootbeams", "506757-5548970-lootbeams-1.20.1-1.2.6.jar", "server",
     "NoClassDefFoundError: client/renderer/RenderStateShard$EmptyTextureStateShard"),
    ("mafglib", "910766-6763273-MaFgLib-0.1.14-mc1.20.1.jar", "server",
     "invalid dist DEDICATED_SERVER (client/gui/screens/Screen)"),
    ("oculus", "581495-6020952-oculus-mc1.20.1-1.8.0.jar", "server",
     "invalid dist DEDICATED_SERVER；光影渲染，纯客户端"),
    ("itemphysiclite", "270441-6045994-ItemPhysicLite_FORGE_v1.6.6_mc1.20.1.jar", "server",
     "ExceptionInInitializerError（客户端物理渲染）"),
    ("nolijium", "969602-6264798-nolijium-0.5.6.jar", "server",
     "invalid dist DEDICATED_SERVER；客户端优化"),
    ("great_scrollable_tooltips", "982671-6707703-great_scrollable_tooltips-15.5.0+forge.jar", "server",
     "invalid dist DEDICATED_SERVER；tooltip 滚动"),
    ("ktnilcks", "304487-5148656-ItemLocks-Forge-1.20.1-1.3.8.jar", "server",
     "invalid dist DEDICATED_SERVER；物品锁 GUI"),
    ("tweakerge", "915857-5633999-Tweakerge-0.1.5-mc1.20.1.jar", "server",
     "invalid dist DEDICATED_SERVER；客户端 tweak"),
    ("legendarytooltips", "532127-4662781-LegendaryTooltips-1.20.1-forge-1.4.5.jar", "server",
     "ExceptionInInitializerError（tooltip 边框渲染）"),
    ("jecharacters", "250702-6680042-jecharacters-1.20.1-forge-4.5.16.jar", "server",
     "NoClassDefFoundError: client/searchtree/SuffixArray；中文输入法"),
    ("badoptimizations", "949555-6742958-BadOptimizations-2.3.0-1.20.1.jar", "server",
     "NoClassDefFoundError: com/mojang/text2speech/Narrator；客户端优化"),
    # 以下两个必须两端同时移除
    ("framework", "549225-6531428-framework-forge-1.20.1-0.7.15.jar", "both",
     "NoClassDefFoundError: client/gui/components/toasts/Toast；"
     "且注册了网络通道 -> 两端必须一致，否则握手 mismatched mod list"),
    ("controllable", "317269-6171424-controllable-forge-1.20.1-0.21.7.jar", "both",
     "mandatory 依赖 framework，framework 移除后必然 MissingModsException"),
]


def main():
    names = " ".join('"%s"' % f for _m, f, _s, _w in PLAN)
    script = (
        "cd %s && mkdir -p mods-disabled && moved=0; miss=0; "
        "for f in %s; do "
        "  if [ -f \"mods/$f\" ]; then mv \"mods/$f\" mods-disabled/ && moved=$((moved+1)); "
        "  elif [ -f \"mods-disabled/$f\" ]; then miss=$((miss+0)); "
        "  else echo \"  NOT FOUND: $f\"; miss=$((miss+1)); fi; "
        "done; "
        "echo \"moved=$moved  notfound=$miss\"; "
        "echo -n 'mods 剩余 jar: '; ls mods/*.jar 2>/dev/null | wc -l; "
        "echo -n 'mods-disabled jar: '; ls mods-disabled/*.jar 2>/dev/null | wc -l"
        % (LWI, names)
    )
    print(run(script, timeout=180))
    print("\n== 核对：mods-disabled 内容 ==")
    print(run("ls -1 %s/mods-disabled/ 2>/dev/null" % LWI, timeout=120))
    return 0


if __name__ == "__main__":
    sys.exit(main())
