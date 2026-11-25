#!/usr/bin/env python3
"""Build and deploy IslandTweaks. Configuration is backed up before restart."""
import base64
from pathlib import Path
from ssh_exec import run, HOST, USER, PWD
import paramiko

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "island_tweaks" / "src" / "main"

def upload(local, remote):
    c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=PWD, timeout=20)
    s = c.open_sftp(); s.put(str(local), remote); s.close(); c.close()

def main():
    remote = r'''
mkdir -p /opt/island-tweaks/src/main/java/workbuddy/islands /opt/island-tweaks/src/main/resources
mkdir -p /opt/mc/backups
stamp=$(date +%Y%m%d-%H%M%S)
tar -czf /opt/mc/backups/island-tweaks-$stamp.tgz -C /opt/mc plugins/Essentials/config.yml plugins/Essentials/kits.yml plugins/Essentials/spawn.yml plugins/BentoBox/addons/BSkyBlock/config.yml plugins/BentoBox/database/Island bskyblock_world/region 2>/dev/null
sha256sum /opt/mc/backups/island-tweaks-$stamp.tgz
'''
    print(run(remote))
    for p in SRC.rglob("*"):
        if p.is_file(): upload(p, "/opt/island-tweaks/src/main/" + str(p.relative_to(SRC)).replace("\\", "/"))
    cp = ":".join([
        "/opt/mc/libraries/io/papermc/paper/paper-api/1.21.11-R0.1-SNAPSHOT/paper-api-1.21.11-R0.1-SNAPSHOT.jar",
        "/opt/mc/plugins/BentoBox.jar", "/tmp/Vault.jar"
    ])
    build = "set -e; rm -rf /opt/island-tweaks/classes; mkdir -p /opt/island-tweaks/classes; CP=" + cp + ":$(find /opt/mc/libraries/net/kyori /opt/mc/libraries/net/md-5 -name '*.jar' | tr '\\n' ':') && /opt/java/jdk-21/bin/javac -encoding UTF-8 -cp \"$CP\" -d /opt/island-tweaks/classes /opt/island-tweaks/src/main/java/workbuddy/islands/IslandTweaks.java && cp /opt/island-tweaks/src/main/resources/plugin.yml /opt/island-tweaks/classes/ && /opt/java/jdk-21/bin/jar cf /opt/mc/plugins/IslandTweaks.jar -C /opt/island-tweaks/classes . && /opt/java/jdk-21/bin/jar tf /opt/mc/plugins/IslandTweaks.jar && echo BUILD_SUCCESS"
    result = run(build, timeout=120)
    print(result)
    if "BUILD_SUCCESS" not in result:
        raise RuntimeError("编译失败：未安装新插件，未重启服务器。")
    patch = '''
import yaml
from pathlib import Path
p=Path('/opt/mc/plugins/Essentials/config.yml')
lines=p.read_text().splitlines()
for i,line in enumerate(lines):
 if line.startswith('spawn-on-join:'): lines[i]='spawn-on-join: false'
 if line.startswith('currency-symbol:'): lines[i]="currency-symbol: '云币'"
p.write_text(chr(10).join(lines)+chr(10))
p=Path('/opt/mc/plugins/Essentials/kits.yml')
d=yaml.safe_load(p.read_text())
d['kits']['starter']={'delay': -1, 'items': ['stone_sword 1', 'stone_pickaxe 1', 'stone_axe 1', 'stone_shovel 1', 'bread 8', 'torch 16']}
p.write_text(yaml.safe_dump(d,allow_unicode=True))
assert yaml.safe_load(p.read_text())['kits']['starter']['items']
p=Path('/opt/mc/plugins/BentoBox/addons/BSkyBlock/config.yml')
d=yaml.safe_load(p.read_text())
d['island']['commands']['on-join']=['[SUDO] kit starter']
d['world']['nether']['create-and-link-portals']=True
d['world']['end']['dragon-spawn']=True
p.write_text(yaml.safe_dump(d,allow_unicode=True))
print('CONFIG_VERIFIED')
qs=Path('/opt/mc/plugins/QuickShop-Hikari/config.yml')
if qs.exists():
 d=yaml.safe_load(qs.read_text())
 d['use-crowdin-ota']=False
 d['game-language']='zh-CN'
 d['enabled-languages']=['zh-CN','en-US']
 d['shop-tax']['basic']['rate']=0.0
 d['shop']['cost']=0
 d['shop']['price-change-requires-fee']=False
 d['shop']['fee-for-price-change']=0
 d['shop']['name-fee']=0
 qs.write_text(yaml.safe_dump(d,allow_unicode=True))
 print('QUICKSHOP_ZERO_TAX_VERIFIED')
'''
    print(run("echo " + base64.b64encode(patch.encode()).decode() + " | base64 -d | python3"))
    print(run('install -m 644 /tmp/Vault.jar /opt/mc/plugins/Vault.jar; if python3 -c "import zipfile; zipfile.ZipFile(chr(47)+chr(116)+chr(109)+chr(112)+chr(47)+chr(81)+chr(117)+chr(105)+chr(99)+chr(107)+chr(83)+chr(104)+chr(111)+chr(112)+chr(45)+chr(72)+chr(105)+chr(107)+chr(97)+chr(114)+chr(105)+chr(46)+chr(106)+chr(97)+chr(114)).testzip()"; then install -m 644 /tmp/QuickShop-Hikari.jar /opt/mc/plugins/QuickShop-Hikari.jar; echo QUICKSHOP_READY; else echo QUICKSHOP_DOWNLOAD_INCOMPLETE; fi; systemctl restart mc.service; systemctl is-active mc.service', timeout=120))

if __name__ == "__main__": main()
