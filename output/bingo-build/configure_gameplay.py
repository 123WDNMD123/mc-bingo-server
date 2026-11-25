#!/usr/bin/env python3
"""Apply co-op gameplay + team-only voice settings on the BINGO server.

Runs remotely through Cloud Assistant. Idempotent; restarts bingo.service once.

Decisions implemented (user-confirmed):
- Co-op: everyone on ONE team, one shared card, one line (row/col/diagonal) wins.
- Voice: proximity in lobby, team-only in game (teammates any distance,
  opponents never audible). Achieved via a single persistent combined group.
- Access: offline mode, open by default, blacklist only.
"""
import base64
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from aliyun_api import run_shell

CFG = "/opt/bingo/config"
BINGO = CFG + "/yet-another-minecraft-bingo"

# game-options.json: single team => one shared card; goal = 1 line.
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

# voicechat.json: one combined group always => all co-op players hear each
# other at any distance; no per-team split, no opponent leakage.
bingo_voice = {
    "enabled": True,
    "useCombinedGroupForSingleplayerTeams": True,
    "useCombinedGroupAlways": True,
    "teamGroups": {"name": "Bingo: %s Team", "type": "OPEN",
                   "password": None, "hidden": False},
    "spectatorGroup": {"name": "Bingo: Spectators", "type": "NORMAL",
                       "password": None, "hidden": False},
    "combinedGroup": {"name": "Bingo 合作语音", "type": "OPEN",
                      "password": None, "hidden": False},
}


def b64(obj):
    return base64.b64encode(
        json.dumps(obj, ensure_ascii=False, indent=4).encode("utf-8")).decode()


script = "\n".join([
    "set -e",
    "cd %s" % BINGO,
    "cp -a game-options.json game-options.json.bak.$(date +%s)",
    "cp -a voicechat.json voicechat.json.bak.$(date +%s)",
    "echo %s | base64 -d > game-options.json" % b64(game_options),
    "echo %s | base64 -d > voicechat.json" % b64(bingo_voice),
    # voice_host must be the public EIP so clients can reach UDP 24454.
    "sed -i 's|^voice_host=.*|voice_host=47.120.61.237|' "
    + CFG + "/voicechat/voicechat-server.properties",
    "grep -E '^voice_host=|^enable_groups=|^max_voice_distance=' "
    + CFG + "/voicechat/voicechat-server.properties",
    "python3 -c \"import json;print('game-options ok', json.load(open('game-options.json'))['teamCount'])\"",
    "python3 -c \"import json;print('voice ok', json.load(open('voicechat.json'))['useCombinedGroupAlways'])\"",
    "systemctl restart bingo",
    "sleep 50",
    "systemctl is-active bingo",
    "journalctl -u bingo --no-pager -n 200 | grep -E 'Done \\(|voice_host|Voice chat server started|GameState changed|CardService|ERROR.*bingo' | tail -12",
])

res = run_shell(script, timeout=240)
print(res.get("status"), res.get("exit_code"))
print(res.get("output") or json.dumps(res, ensure_ascii=False))
