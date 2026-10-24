# Duet kernel provenance (for the BasecampOS build)
Running kernel: 6.12.50-stb-cbm-cam (see uname-a.txt). Base = hexdump0815's mainline MediaTek mt81xx kernel (the velvet-os kukui image
chromebook_kukui-aarch64-trixie-251007.img.gz from release 251115-01 ships 6.12.50-stb-cbm+), rebuilt on 2026-10-07 on the Atlas machine with
the camera drivers: config fragment config/mt8183-camera.config and patches/linux/v6.12 + dts from https://github.com/vpavlin/mt8183-camera
(camera modules are out-of-tree .ko, the sensors come from a DT fragment; see that repo's docs/kexec-dt.md and docs/userspace.md).
NOT on the Duet: the exact hexdump0815 repo commit and the full .config (the Duet has no /proc/config.gz / CONFIG_IKCONFIG, no kernel headers). They exist on Atlas
(~/duet-camera/HANDOFF.md, NOTES.md has secrets - never publish). Atlas is currently offline; ask it for: source commit, .config, packing recipe.
Files: uname-a.txt, cmdline-running.txt, cmdline-kern-b-blob.txt, lsmod.txt, firmware-dmesg.txt, dt-compatible.txt, dt-model.txt, fit-structure.txt.
Boot facts: cros_secure root=LABEL=rootpart ... console=tty1 (tty1 is the panel). `crossystem dev_boot_usb` reads as (error) from userspace, so the USB boot flag is unverified.
