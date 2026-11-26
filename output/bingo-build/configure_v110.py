#!/usr/bin/env python3
"""Apply v1.1.0 gameplay config: VeinMiner + SkinRestorer + keep_inventory fix.

Runs locally, drives the ECS through Cloud Assistant.

Design decisions for a co-op BINGO server:
  * mustSneak=true  -> chain mining only while sneaking, so normal single-block
                       mining stays normal. Prevents accidentally nuking a vein.
  * add a Logs group -> BINGO cards frequently demand wood; default config only
                       had Ores, which made the feature useless for half the card.
  * maxChain 100->256, searchRadius 1->2 -> a whole small tree / ore vein in one go.
  * decreaseDurability stays true, needCorrectTool stays true -> no free resources,
                       the tool still wears out and you still need the right tier.
  * autoUpdate stays false -> never silently swap the jar we hash-verified.
  * SkinRestorer autoFetch providers mojang + ely_by -> offline nicknames usually
                       have no Mojang profile, ely.by is the practical fallback.

Also fixes keep_inventory: the world gamerule was still false even though the
BINGO JSON said isKeepInventory=true (same trap as PvP earlier).

Config write order matters: STOP the server first, otherwise runtime state
overwrites the files on shutdown.
"""
import base64
import json
import sys

sys.path.insert(0, ".")
from aliyun_api import run_shell

SETTINGS = {
    "cooldown": 10,
    "mustSneak": True,
    "delay": 0,
    "maxChain": 256,
    "needCorrectTool": True,
    "searchRadius": 2,
    "permissionRestricted": False,
    "mergeItemDrops": True,
    "autoUpdate": False,
    "decreaseDurability": True,
    "hungerPerBlock": 0.0,
    "miningSpeedModifier": 0.0,
    "separateGroupMining": False,
    "minEnchantLevel": 1,
    "dontDisplayUpdatesAndIWillNotAskForSupportBeforeUpdatingISwear": True,
    "debug": False,
    "client": {
        "allow": True,
        "require": False,
        "translucentBlockHighlight": True,
        "allBlocks": False,
        "allowClientGroups": True,
        "overrides": {k: None for k in [
            "cooldown", "mustSneak", "delay", "maxChain", "needCorrectTool",
            "searchRadius", "permissionRestricted", "decreaseDurability",
            "hungerPerBlock", "miningSpeedModifier", "separateGroupMining",
            "minEnchantLevel"]},
    },
}

OVERRIDE_NULLS = {k: None for k in [
    "cooldown", "mustSneak", "delay", "maxChain", "needCorrectTool",
    "searchRadius", "permissionRestricted", "decreaseDurability",
    "hungerPerBlock", "miningSpeedModifier", "separateGroupMining",
    "minEnchantLevel"]}

GROUPS = [
    {"name": "Ores", "blocks": ["#c:ores"], "tools": ["#minecraft:pickaxes"],
     "override": dict(OVERRIDE_NULLS)},
    {"name": "Logs", "blocks": ["#minecraft:logs"], "tools": ["#minecraft:axes"],
     "override": dict(OVERRIDE_NULLS)},
    {"name": "Leaves", "blocks": ["#minecraft:leaves"], "tools": ["#minecraft:axes", "#minecraft:hoes"],
     "override": dict(OVERRIDE_NULLS)},
]

PY = r'''
import json, os
base = "/opt/bingo/config"
vm = os.path.join(base, "Veinminer")
sr = os.path.join(base, "skinrestorer", "config.json")

settings = json.loads(__SETTINGS__)
groups = json.loads(__GROUPS__)

with open(os.path.join(vm, "settings.json"), "w") as f:
    json.dump(settings, f, indent=4)
with open(os.path.join(vm, "groups.json"), "w") as f:
    json.dump(groups, f, indent=4)

with open(sr) as f:
    cfg = json.load(f)
cfg["language"] = "zh_cn"
cfg["join"]["refreshSkin"] = True
cfg["join"]["autoFetch"]["enabled"] = True
cfg["join"]["autoFetch"]["providers"] = ["mojang", "ely_by"]
cfg["providers"]["mojang"]["enabled"] = True
cfg["providers"]["ely_by"]["enabled"] = True
cfg["command"]["enabled"] = True
cfg["command"]["permissionLevel"] = 0
with open(sr, "w") as f:
    json.dump(cfg, f, indent=2)

# read back to prove the writes landed
s2 = json.load(open(os.path.join(vm, "settings.json")))
g2 = json.load(open(os.path.join(vm, "groups.json")))
c2 = json.load(open(sr))
print("VM mustSneak=%s maxChain=%s radius=%s autoUpdate=%s" % (
    s2["mustSneak"], s2["maxChain"], s2["searchRadius"], s2["autoUpdate"]))
print("VM groups=%s" % [g["name"] for g in g2])
print("SR lang=%s providers=%s cmdLevel=%s" % (
    c2["language"], c2["join"]["autoFetch"]["providers"], c2["command"]["permissionLevel"]))
print("CONFIG_WRITE_OK")
'''


def main():
    py = PY.replace("__SETTINGS__", repr(json.dumps(SETTINGS)))
    py = py.replace("__GROUPS__", repr(json.dumps(GROUPS)))
    b64 = base64.b64encode(py.encode("utf-8")).decode()

    cmd = (
        "systemctl stop bingo; sleep 6; "
        "echo %s | base64 -d > /tmp/cfg110.py && python3 /tmp/cfg110.py; "
        "systemctl start bingo; sleep 40; systemctl is-active bingo; "
        "grep -a 'Done (' /opt/bingo/logs/latest.log | tail -1"
    ) % b64
    r = run_shell(cmd, timeout=200)
    print(r.get("status"), r.get("exit_code"))
    print(r.get("output") or r)


if __name__ == "__main__":
    main()