#!/usr/bin/env python3
"""Persist co-op defaults in BOTH game-options files while server is stopped.

Root cause (verified): bingo loads game-options-default.json as the template and
rewrites game-options.json from runtime state, so editing only the latter gets
reverted on the next round. Writing both, with the server stopped, sticks.

Co-op target: teamCount=1 (everyone shares one card), goal=1 line,
teamAutoShuffle=true (players auto-placed on the single team),
PvP off, keepInventory on.
"""
import base64
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from aliyun_api import run_shell

D = "/opt/bingo/config/yet-another-minecraft-bingo"

opts = {
    "winCondition": {"type": "cards", "cards": 1},
    "cards": [{
        "goal": {"type": "lines", "lines": 1},
        "itemDistribution": [0, 0, 0, 9, 16],
        "itemFilter": "-tedious -unobtainable",
        "isLockoutMode": False,
        "isInventoryMode": False,
        "isHiddenItemsMode": False,
        "isConsumeItemsMode": False,
    }],
    "stalemateBehavior": "END_GAME",
    "endGameWhen": {"type": "first_win"},
    "timeLimit": None,
    "isElytra": False,
    "isNightVision": False,
    "isUnlockRecipes": True,
    "isPvpEnabled": False,
    "isKeepInventory": True,
    "spawnDimension": "minecraft:overworld",
    "spawnDistance": 25,
    "showRemainingTime": True,
    "showCompletedItems": True,
    "showCompletedLines": True,
    "showLeadingTeam": True,
    "showPreviewCard": True,
    "showHiddenTiers": False,
    "isPlayerKit": False,
    "isTeamKit": False,
    "teamAutoShuffle": True,
    "teamCount": 1,
}

payload = base64.b64encode(
    json.dumps(opts, ensure_ascii=False, indent=4).encode("utf-8")).decode()

script = "\n".join([
    "set -e",
    "systemctl stop bingo",
    "sleep 10",
    "cd %s" % D,
    "echo %s | base64 -d > game-options-default.json" % payload,
    "echo %s | base64 -d > game-options.json" % payload,
    "grep -E 'teamCount|isPvpEnabled|isKeepInventory|teamAutoShuffle' game-options-default.json",
    "systemctl start bingo",
    "sleep 55",
    "systemctl is-active bingo",
    "echo == runtime state ==, ",
    "grep -E 'teamCount|isPvpEnabled|isKeepInventory|teamAutoShuffle' game-options.json",
    "python3 /tmp/rcon_probe.py bingo 2>&1 | head -6",
])

res = run_shell(script, timeout=240)
print(res.get("status"), res.get("exit_code"))
print(res.get("output") or json.dumps(res, ensure_ascii=False))
