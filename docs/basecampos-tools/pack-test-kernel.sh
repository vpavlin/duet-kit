#!/bin/bash
# Build a signed kernel blob (FIT: our lzma kernel + the two krane dtbs, NO initrd) for the BasecampOS slot test.
# Output: ~/duet/basecampos/work/KERN-test.bin (a FILE, nothing is written to the disk).
# usage: pack-test-kernel.sh ["extra cmdline words"]
set -e
W=$HOME/duet/basecampos/work; cd "$W"
KD=/usr/share/vboot/devkeys
# no initrd: the kernel cannot resolve LABEL=, so name the partition (p1 = btrfs LABEL=home) directly
echo "root=/dev/mmcblk0p1 rootfstype=btrfs rootflags=subvol=${SUBVOL:-@basecampos} rootwait rw console=tty1 panic=10 net.ifnames=0 $1 init=${INIT:-/nix/var/nix/profiles/system/init}" > cmdline-test.txt
mkimage -f test.its fit-test.itb >/dev/null
futility vbutil_kernel --pack KERN-test.bin --keyblock $KD/kernel.keyblock --signprivate $KD/kernel_data_key.vbprivk \
  --version 1 --vmlinuz fit-test.itb --bootloader bootloader.bin --config cmdline-test.txt --arch arm --kloadaddr 0x100000 >/dev/null
futility vbutil_kernel --verify KERN-test.bin | sed -n '/Body verification/,$p'
ls -la KERN-test.bin
