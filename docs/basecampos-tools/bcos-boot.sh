#!/bin/bash
# Debian side: boot BasecampOS ONCE on the next restart (KERN-A, one try; if it fails the firmware falls back to Debian by itself).
# Do not run revert.sh before this - KERN-A (p2) must still hold the BasecampOS blob.
# usage: sudo bcos-boot.sh [--now]
set -e
D=/dev/mmcblk0
vbutil_kernel --verify ${D}p2 2>/dev/null | grep -q "subvol=@basecampos" || { echo "KERN-A does not hold a BasecampOS blob (was revert.sh run?)"; exit 1; }
[ "$(cgpt show -i 4 -S $D | tail -1)" = 1 ] || { echo "KERN-B (Debian) is not marked successful - refusing"; exit 1; }
cgpt add -i 2 -P 6 -T 1 -S 0 $D
echo "armed: the next restart boots BasecampOS (one try), Debian stays the fallback."
[ "$1" = "--now" ] && { echo "restarting..."; sleep 2; systemctl reboot; }
