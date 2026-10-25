#!/bin/bash
# Experiment: write a blob into KERN-A (p2), arm ONE try, schedule a reboot. Debian boots under test kernels return by themselves
# (p2test-return.service ~3 min after boot, only when the cmdline has p2test=<label>) and log evidence to ~/duet/basecampos/p2test-<label>.log.
# usage: sudo try-blob.sh <blob> <label>
set -e
BLOB=$1; LABEL=$2; D=/dev/mmcblk0
[ -n "$LABEL" ] && [ -s "$BLOB" ] || { echo "usage: try-blob.sh blob label"; exit 2; }
(cd /home/linux/duet/backups/boot-20261024 && sha256sum -c SHA256SUMS >/dev/null) || { echo backup bad; exit 1; }
[ "$(cgpt show -i 4 -P $D | tail -1)" = 5 ] && [ "$(cgpt show -i 4 -S $D | tail -1)" = 1 ] || { echo "KERN-B not healthy"; exit 1; }
futility vbutil_kernel --verify "$BLOB" >/dev/null || { echo "blob does not verify"; exit 1; }
dd if="$BLOB" of=${D}p2 bs=1M conv=fsync status=none
cgpt add -i 2 -P 6 -T 1 -S 0 $D
touch /home/linux/duet/basecampos/.armed
echo "$LABEL" > /home/linux/duet/basecampos/CURRENT-EXPERIMENT.txt
echo "armed $LABEL: p2 prio $(cgpt show -i 2 -P $D | tail -1) tries $(cgpt show -i 2 -T $D | tail -1)"
sync
systemd-run --on-active=20 systemctl reboot >/dev/null
echo "reboot in 20 s"
