#!/bin/bash
# Write the test blob into KERN-A (p2) and arm ONE boot try (prio 6 > KERN-B 5, tries=1, successful=0). Does NOT reboot.
# Needs: --yes. Refuses unless the backups exist, KERN-B is healthy and the blob verifies.
set -e
[ "$1" = "--yes" ] || [ "$1" = "--check" ] || { echo "refusing without --yes (or --check for a dry run) (this overwrites KERN-A p2, backup: ~/duet/backups/boot-20261024)"; exit 2; }
B=/home/linux/duet/backups/boot-20261024; W=/home/linux/duet/basecampos/work; D=/dev/mmcblk0
[ -s $B/KERN-A-p2.img ] && (cd $B && sha256sum -c SHA256SUMS >/dev/null) || { echo "backup missing/corrupt"; exit 1; }
[ "$(cgpt show -i 4 -P $D | tail -1)" = 5 ] && [ "$(cgpt show -i 4 -S $D | tail -1)" = 1 ] || { echo "KERN-B not prio 5/successful"; exit 1; }
futility vbutil_kernel --verify $W/KERN-test.bin >/dev/null || { echo "blob does not verify"; exit 1; }
[ "$(stat -c %s $W/KERN-test.bin)" -lt 33554432 ] || { echo "blob too big for p2"; exit 1; }
[ -d /home/@basecampos/nix/store ] || { echo "rootfs not unpacked in /home/@basecampos"; exit 1; }
[ "$1" = "--check" ] && { echo "all checks pass (dry run, nothing written)"; exit 0; }
dd if=$W/KERN-test.bin of=${D}p2 bs=1M conv=fsync status=none
cgpt add -i 2 -P 6 -T 1 -S 0 $D
echo "armed: p2 prio 6 tries 1 success 0; KERN-B untouched (prio 5, success 1). Reboot to try. Revert: revert.sh"
cgpt show -i 2 -P $D | tail -1; cgpt show -i 2 -T $D | tail -1
