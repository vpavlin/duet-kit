#!/usr/bin/env python3
"""Make a BasecampOS root (btrfs subvolume, e.g. /home/@basecampos) start the Debian userland's shrooms daemon + agent (Claude) at boot.
Run as root from Debian: sudo apply-agent-chroot.py /home/@basecampos [--window MINUTES]
Idempotent. Nothing is copied from Debian except the two Wi-Fi profiles (so the tablet gets online); the shrooms credential and the
Claude files are used in place through a chroot into the Debian root (p5) + Debian's /home (p1 top level)."""
import os, shutil, sys, re

root = sys.argv[1].rstrip('/')
window = int(sys.argv[sys.argv.index('--window') + 1]) if '--window' in sys.argv else 90

def resolve(p, depth=0):
    """resolve p inside root (absolute symlinks are relative to root), returns a host path"""
    parts = [x for x in p.split('/') if x]
    cur = '/'
    for i, part in enumerate(parts):
        nxt = os.path.join(cur, part)
        host = root + nxt
        if os.path.islink(host) and depth < 40:
            t = os.readlink(host)
            t = t if t.startswith('/') else os.path.normpath(os.path.join(cur, t))
            rest = '/'.join(parts[i + 1:])
            return resolve(t + ('/' + rest if rest else ''), depth + 1)
        cur = nxt
    return root + cur

START = r'''#!/run/current-system/sw/bin/bash
# BasecampOS on the Duet: bring up the Debian userland's shrooms daemon + shrooms-agent (and with them the Claude session) via chroot.
# Nothing is copied: Debian's root (p5) and its /home (p1 top level) are mounted in place; secrets stay where they are.
export PATH=/run/current-system/sw/bin
mkdir -p /var/lib/duet-agent
exec >>/var/lib/duet-agent/start.log 2>&1
echo "=== $(date) start"
D=/mnt/debian
mkdir -p $D
modprobe tun; modprobe wireguard 2>/dev/null
[ -w /sys/class/backlight/backlight_lcd0/brightness ] && [ "$(cat /sys/class/backlight/backlight_lcd0/brightness)" -lt 100 ] && echo 700 > /sys/class/backlight/backlight_lcd0/brightness
mountpoint -q $D || mount -t btrfs -o rw,noatime /dev/mmcblk0p5 $D || { echo "cannot mount Debian root"; exit 1; }
mountpoint -q $D/home || mount -t btrfs -o rw,noatime,subvolid=5 /dev/mmcblk0p1 $D/home || { echo "cannot mount /home top level"; exit 1; }
grep -q zram /proc/swaps || grep -q swapfile /proc/swaps || swapon /mnt/debian/home/swapfile 2>&1 || true   # no zram in the first image: reuse Debian's swapfile
for m in proc sys dev; do mountpoint -q $D/$m || mount --rbind /$m $D/$m; done
mountpoint -q $D/run || { mount --bind /run $D/run; mount --make-rslave $D/run; }
# rslave: later host mounts (logind's /run/user/1000 tmpfs) still show up in the chroot, but our nscd hiding mount below does not leak back.
# the NixOS nscd socket lives in /run/nscd: hide it, or NSS inside the chroot resolves uid 1000 as 'basecamp' and Debian's sudo breaks
mountpoint -q $D/run/nscd || { mkdir -p /run/nscd-hidden; mount --bind /run/nscd-hidden $D/run/nscd; }
mountpoint -q $D/tmp || mount --bind /tmp $D/tmp
mkdir -p /run/systemd/resolve
{ grep -h '^nameserver' /etc/resolv.conf 2>/dev/null; echo "nameserver 9.9.9.9"; echo "nameserver 1.1.1.1"; } > /run/systemd/resolve/stub-resolv.conf
for i in $(seq 1 24); do nmcli -t -f STATE general 2>/dev/null | grep -q '^connected' && break; sleep 5; done
echo "network: $(nmcli -t -f STATE general 2>&1)"
mkdir -p /run/shrooms; chmod 0777 /run/shrooms
fwopen() { for t in ip ip6; do chroot $D /usr/sbin/nft list chain $t filter nixos-fw 2>/dev/null | grep -q shrooms0 || chroot $D /usr/sbin/nft insert rule $t filter nixos-fw iifname shrooms0 accept; done; }
DEBPATH=/usr/local/sbin:/usr/sbin:/usr/local/bin:/usr/bin:/sbin:/bin
chroot $D /usr/bin/env PATH=$DEBPATH LD_LIBRARY_PATH=/opt/shrooms/lib /opt/shrooms/bin/shrooms daemon >>/var/lib/duet-agent/shrooms.log 2>&1 &
DPID=$!
for i in $(seq 1 30); do [ -S /run/shrooms/shrooms.sock ] && break; sleep 2; done
for i in $(seq 1 20); do ip link show shrooms0 >/dev/null 2>&1 && break; sleep 2; done; fwopen   # NixOS firewall drops new inbound connections: accept everything arriving on the mesh interface
chmod 0666 /run/shrooms/shrooms.sock 2>/dev/null; chmod 0755 /run/shrooms   # the daemon resets the dir to 0750 root:<socket_group>; the Basecamp user is gid 100
for i in $(seq 1 60); do mountpoint -q /run/user/1000 && break; sleep 3; done
mkdir -p /run/user/1000; chown 1000 /run/user/1000
chroot --userspec=1000:1000 $D /usr/bin/env HOME=/home/linux USER=linux LOGNAME=linux XDG_RUNTIME_DIR=/run/user/1000 \
  PATH=/home/linux/.local/bin:$DEBPATH /usr/local/bin/shrooms-agent -claude /home/linux/.local/bin/claude-sonnet >>/var/lib/duet-agent/agent.log 2>&1 &
APID=$!
( for i in $(seq 1 60); do [ -S /run/user/1000/shrooms-agent/agent.sock ] && break; sleep 3; done; sleep 40
  curl -s -m 20 --unix-socket /run/user/1000/shrooms-agent/agent.sock -X POST -H 'Content-Type: application/json' \
   -d "{\"text\":\"[sent by the BasecampOS start script] The shrooms daemon and agent are now running INSIDE BasecampOS (NixOS, chroot into the Debian userland; kernel $(uname -r); started $(date +%T)). You are active in BasecampOS. Logs: /home/@basecampos/var/lib/duet-agent/ (p1 top level). Read ~/duet/basecampos/NEXT.md.\",\"id\":\"basecampos-agent-up-$(date +%s)\"}" http://a/v1/sessions/duet/messages >> /var/lib/duet-agent/notify.log 2>&1 ) &
# health monitor: log mesh/net state every 30 s; if no peer is online for 3 min while the Internet answers (post-roam/suspend churn), restart everything
( BAD=0; while sleep 30; do
    P=$(chroot $D /usr/bin/env PATH=$DEBPATH LD_LIBRARY_PATH=/opt/shrooms/lib /opt/shrooms/bin/shrooms status 2>/dev/null | sed -n 's/.*peers [0-9]* (\([0-9]*\) online.*/\1/p')
    fwopen; chmod 0755 /run/shrooms 2>/dev/null; chmod 0666 /run/shrooms/shrooms.sock 2>/dev/null
    N=$(nmcli -t -f STATE general 2>/dev/null | head -1)
    if ping -c1 -W3 1.1.1.1 >/dev/null 2>&1; then I=up; else I=down; fi
    echo "$(date +%T) peers_online=${P:-?} nm=$N internet=$I" >> /var/lib/duet-agent/health.log
    if [ "${P:-0}" = 0 ] && [ $I = up ]; then BAD=$((BAD+1)); else BAD=0; fi
    if [ $BAD -ge 6 ]; then echo "$(date +%T) no peers for 3 min with Internet up: restarting daemon+agent" >> /var/lib/duet-agent/health.log; kill $DPID; break; fi
  done ) &
wait -n $DPID $APID
echo "=== $(date) a child exited, restarting via systemd"
exit 1
'''
UNIT = '''[Unit]
Description=Debian userland shrooms daemon + agent (chroot) for the Duet
After=network-online.target NetworkManager.service
Wants=network-online.target
[Service]
Type=simple
ExecStart=/run/current-system/sw/bin/bash /var/lib/duet-agent/start.sh
Restart=on-failure
RestartSec=15
[Install]
WantedBy=multi-user.target
'''
os.makedirs(root + '/var/lib/duet-agent', exist_ok=True)
open(root + '/var/lib/duet-agent/start.sh', 'w').write(START); os.chmod(root + '/var/lib/duet-agent/start.sh', 0o755)
units = resolve('/nix/var/nix/profiles/system/etc/systemd/system')   # the system-units store dir of this generation (works before the first boot too)
assert os.path.isdir(units), units
os.chmod(units, 0o755)
open(units + '/duet-debian-agent.service', 'w').write(UNIT)
wants = units + '/multi-user.target.wants'
os.chmod(wants, 0o755)
l = wants + '/duet-debian-agent.service'
if os.path.lexists(l): os.remove(l)
os.symlink('../duet-debian-agent.service', l)
# test window length
tw = units + '/basecampos-test-window.service'
if os.path.islink(tw): tw = resolve(os.readlink(tw))
txt = open(tw).read()
m = re.search(r'ExecStart=(\S+)', txt)
if m:
    script = resolve(m.group(1))
    s = open(script).read()
    s2 = re.sub(r'sleep \d+;', 'sleep %d;' % (window * 60), s)
    os.chmod(script, 0o755); open(script, 'w').write(s2)
    print('test window script:', script, '->', re.search(r'sleep \d+', s2).group(0))
os.makedirs(root + '/etc/NetworkManager/system-connections', mode=0o700, exist_ok=True)
for p in ('Internety', 'BRNO_BRM_5G'):
    src = '/etc/NetworkManager/system-connections/%s.nmconnection' % p
    if os.path.exists(src):
        dst = root + '/etc/NetworkManager/system-connections/%s.nmconnection' % p
        shutil.copy(src, dst); os.chmod(dst, 0o600)
print('applied to', root, 'units dir', units)
