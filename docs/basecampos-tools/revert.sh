#!/bin/bash
# Put KERN-A (p2) back exactly as before the BasecampOS test (image + attributes). Safe to run any time from Debian.
set -e
B=/home/linux/duet/backups/boot-20261024; D=/dev/mmcblk0
(cd $B && sha256sum -c SHA256SUMS >/dev/null)
dd if=$B/KERN-A-p2.img of=${D}p2 bs=1M conv=fsync status=none
cgpt add -i 2 -P 4 -T 0 -S 1 $D
cmp <(dd if=${D}p2 bs=1M status=none) $B/KERN-A-p2.img 2>/dev/null && echo "p2 restored and identical" || echo "p2 written (verify with sha256sum)"
echo "p2: prio $(cgpt show -i 2 -P $D | tail -1) tries $(cgpt show -i 2 -T $D | tail -1) success $(cgpt show -i 2 -S $D | tail -1); p4: prio $(cgpt show -i 4 -P $D | tail -1) success $(cgpt show -i 4 -S $D | tail -1)"
