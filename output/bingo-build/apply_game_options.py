#!/usr/bin/env python3
"""Write game-options.json while the server is STOPPED.

Root cause found by实测: bingo rewrites game-options.json from its in-memory
state on shutdown/reload, so editing it while running gets reverted
(teamCount went back to 3). Stop -> write -> start avoids the overwrite.
"""
import base64
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from aliyun_api import run_shell

BINGO = "/opt/bingo/config/yet-another-minecraft-bingo"

game_options = {
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
    "teamAutoShuffle": False,
    "teamCount": 1,
}

payload = base64.b64encode(
    json.dumps(game_options, ensure_ascii=False, indent=4).encode("utf-8")).decode()

script = "\n".join([
    "set -e",
    "systemctl stop bingo",
    "sleep 8",
    "systemctl is-active bingo || true",
    "cd %s" % BINGO,
    "echo %s | base64 -d > game-options.json" % payload,
    "grep -E 'teamCount|isPvpEnabled|isKeepInventory' game-options.json",
    "systemctl start bingo",
    "sleep 55",
    "systemctl is-active bingo",
    "echo == after-start config ==, ",
    "grep -E 'teamCount|isPvpEnabled|isKeepInventory' game-options.json",
    "journalctl -u bingo --no-pager -n 250 | grep -E 'Done \\(|GameState changed|CardService|team' | tail -8",
])

res = run_shell(script, timeout=240)
print(res.get("status"), res.get("exit_code"))
print(res.get("output") or json.dumps(res, ensure_ascii=False))
