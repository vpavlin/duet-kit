# Duet kit — what the files don't capture

Collected on 2026-10-06 (sections 0-5) and extended on 2026-10-08 (sections 6-11) from the first Duet (Lenovo IdeaPad Duet Chromebook, krane / MT8183) after a day of setup.
The `home/` and `etc/` trees in this repo are the exact config files; this document is everything else, in the order it was done.
Atlas (vpavlin's x86 box) still has the bring-up helpers referenced below in `~/duet/` (scripts, serve/, img/).

## 0. Base image and boot (manual, per device — ChromeOS dev mode required)
- Image: velvet-os (hexdump0815 imagebuilder) `chromebook_kukui-aarch64-trixie-251007.img.gz` from release `251115-01`
  (Debian 13, kernel 6.12.50-stb-cbm+, default user `linux` / `changeme`, XFCE + lightdm).
- No USB stick was used. Installed from ChromeOS itself into the unused **slot B**:
  1. ChromeOS: enable dev mode; Powerwash if VT2 asks for an unknown password; VT2 (Ctrl+Alt+→) login `chronos`;
     `sudo crossystem dev_boot_usb=1 dev_boot_signed_only=0`. (crosh `shell` cannot sudo on M117+; `sh file` from /tmp is blocked — pipe scripts into `sudo sh`.)
  2. Prepared on a PC from the image: KERN = image p1 (the kpart *with* initrd, 31.4 MB), ROOT = image p4 (btrfs LABEL=rootpart, 3.05 GiB).
     Patched root before shipping: fstab `/boot` → `nofail,x-systemd.device-timeout=3s` (no bootpart in slot B), pre-placed
     `/etc/X11/xorg.conf.d/31-monitor-rotate-left.conf` (avoids the first-boot rotation reboot, which would burn the single try),
     `chmod -x /scripts/extend-rootfs.sh` (it repartitions — never run it), hostname, SSH authorized_keys.
  3. ChromeOS writes them with a checked script (Atlas `~/duet/serve/install-b.sh`): verifies p4=KERN-B, p5=ROOT-B, running from ROOT-A,
     streams both, sha256-verifies, then `cgpt add -i 4 -P 3 -T 1 -S 0`.
  4. After first good boot in Debian: `cgpt add -i 4 -P 3 -T 0 -S 1`; `btrfs filesystem resize max /`.
- **Take over the 50 GB ChromeOS STATE partition (p1) as /home** — only after disabling ChromeOS, or ChromeOS will wipe it:
  `cgpt add -i 2 -P 0 -S 0` (KERN-A off), `cgpt add -i 1 -l DEBIAN-HOME`, `wipefs -a p1; mkfs.btrfs -L home p1`, rsync /home, fstab
  `LABEL=home /home btrfs defaults,ssd,compress=zstd,noatime,nodiratime 0 0`.
- **IPv6 kernel (needed by Shrooms):** the image kernel boots with `ipv6.disable=1`. Re-sign the same kpart without it and put it in KERN-A:
  `vbutil_kernel --verify kern.bin --verbose` (cmdline is the line *after* `Config:`), `vbutil_kernel --repack new.bin --oldblob kern.bin
  --keyblock /usr/share/vboot/devkeys/kernel.keyblock --signprivate /usr/share/vboot/devkeys/kernel_data_key.vbprivk --config cmdline.txt`,
  write to p2, `cgpt add -i 2 -P 4 -T 1 -S 0`, boot, then `-S 1`. KERN-B stays as the fallback.

## 1. Packages
- Remove: XFCE (`xfce4*`, `xfwm4`, `xfdesktop4`, `xfconf`, `thunar`, `mousepad`, `ristretto`, `parole`, `xfburn`, `task-xfce*`) with `--autoremove`,
  firmware for other hardware (`firmware-qcom-soc firmware-iwlwifi firmware-amd-graphics firmware-nvidia-graphics firmware-marvell-prestera
  firmware-intel-graphics firmware-sof-signed`). KEEP firmware-atheros (Wi-Fi is ath10k_sdio) and firmware-mediatek.
  Mark manual first so autoremove keeps them: lightdm slick-greeter network-manager network-manager-gnome blueman bluez pulseaudio
  pulseaudio-module-bluetooth pulseaudio-utils iio-sensor-proxy libfuse2t64 policykit-1 polkitd dbus-user-session
  **libopengl0 libglu1-mesa** (Basecamp needs libOpenGL.so.0 — autoremove took it once) fonts-symbola fonts-noto-color-emoji.
  Blueman needs a notification daemon → install mako-notifier before removing xfce4-notifyd.
- Install (`--no-install-recommends`): sway swaybg swayidle swaylock waybar foot fuzzel wvkbd xwayland libfuse2t64 brightnessctl
  network-manager-gnome wlr-randr iio-sensor-proxy fonts-font-awesome xdg-desktop-portal-wlr grim wtype libnotify-bin mako-notifier
  portfolio-filemanager loupe gvfs systemd-resolved ffmpeg htop iw libinput-tools evtest.
- Brave: repo key `https://brave-browser-apt-release.s3.brave.com/brave-browser-archive-keyring.gpg` → `/usr/share/keyrings/`, list in etc/, `brave-browser`. Firefox ESR purged.
- After installing systemd-resolved: `systemctl reload dbus`, restart systemd-resolved, then NetworkManager (otherwise resolved never registers on D-Bus and DNS dies).
- Then `apt full-upgrade`.

## 2. Services and system settings
- `systemctl disable --now ModemManager` (no modem).
- User: `systemctl --user mask pipewire.socket pipewire.service filter-chain.service` (PulseAudio does the sound).
- `usermod -aG video linux` (backlight); groups `autologin` (+ add user) for lightdm.
- `timedatectl set-timezone Europe/Prague`.
- GTK: `gsettings set org.gnome.desktop.interface color-scheme prefer-dark`, `gtk-theme Adwaita`, `org.gnome.desktop.wm.preferences button-layout 'appmenu:'`.
- `xdg-mime default org.gnome.Loupe.desktop image/png image/jpeg image/webp image/gif image/bmp image/svg+xml image/tiff`.
- PulseAudio: internal DMIC is quiet → `pactl set-source-volume alsa_input.platform-mt8183-sound.HiFi__Mic__source 300%` (device-restore keeps it).
- `systemctl --user enable basecamp.service brave.service foot.service` (WantedBy sway-session.target, started by `session-start`).

## 3. Things built or downloaded (not in Debian)
- **Tabler outline icon font** (MIT) v3.49.0 → `~/.local/share/fonts/tabler-icons.ttf` (`https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.49.0/dist/fonts/tabler-icons.ttf`), `fc-cache -f`.
  waybar/quick-settings use raw codepoints (e.g. ec38 adjustments, eb30 sun, ed30 aspect-ratio, eb51 volume, eaf0 microphone, ea54 camera …).
- **wvkbd with a Czech row**: wvkbd v0.15 source + `wvkbd_czech_layer.py` patch (on Atlas `~/duet/scripts/`) adds a `czech` landscape layer
  (ě š č ř ž ý á í é ú ů as Copy keys). Built on the device originally (`make`; deps libwayland-dev libxkbcommon-dev libpango1.0-dev libcairo2-dev);
  installed to `/usr/local/bin/wvkbd-mobintl`. Must target plain armv8-a.
- **Logos Basecamp** 0.3.1 aarch64 AppImage → `~/Apps/Basecamp.AppImage` (logos-co/logos-basecamp releases).
- **Shrooms** native arm64 package (`shrooms-dist-arm64.tar.gz`, `install.sh` + `install-agent.sh`), config needs `socket_group = "<user>"`,
  `mode = "Edge"`; joined with `shrooms invite` / `shrooms join`. The mesh network key is a SECRET — never commit `/etc/shrooms/`.
- **parakeet-cli** (whisper.cpp 60c0be6, armv8-a) → `~/.local/bin/`, model `ggml-parakeet-tdt-0.6b-v3-q4_k.bin` (sha256 8b205b8b…5e) → `~/.local/share/whisper/` for shrooms-agent voice notes.
- Optional: Basecamp CA bundle for a self-signed LAN repo → `~/.config/basecamp/env` (see basecamp.service).

## 4. Hardware notes (krane on mainline 6.12)
- Panel DSI-1 is portrait-native: `transform 270`; autorotate via iio-sensor-proxy (`normal`=270, `bottom-up`=90, `left-up`=180, `right-up`=0).
- Touch (Goodix 27C6:0E30) + USI pen device exist; pen untested (needs AAAA battery).
- Idle: DIM, never `output power off` — the touch controller dies with the panel and a tap can't wake it. Suspend after 10 min on battery only.
- Suspend (deep) works only with the keyboard cover's USB wakeup disabled (udev rule) — otherwise mtu3 "ip sleep failed" aborts it.
- Brave on Wayland via systemd needs `XDG_SESSION_TYPE` imported (session-start) and `--ozone-platform=wayland --use-gl=angle --use-angle=gles`;
  `--password-store=basic` avoids an un-unlockable gnome-keyring prompt (autologin).
- Wi-Fi power save off (NM conf), else the tablet stops answering ARP. Mesh churns after Wi-Fi changes; `systemctl restart shrooms` settles it.
- Not working on mainline: cameras (no seninf/ISP driver — being worked on), BT headset mic (SCO routed over PCM/I2S, see duet-camera notes).
- CPU: ARMv8.0, no LSE atomics — every native binary must be built for plain armv8-a.

## 5. Startup ordering: the portal stall (found 2026-10-06)
With PipeWire masked (section 2), `xdg-desktop-portal-wlr` can't start (no PipeWire) and crash-loops; the portal frontend then needs ~51 s to come up, and
waybar (which reads the colour scheme from the portal at start) blocks on it, times out after 25 s and restarts — so the bar showed up ~50 s after Brave/foot/Basecamp.
Fix: `~/.config/xdg-desktop-portal/sway-portals.conf` (ScreenCast=none), `systemctl --user mask xdg-desktop-portal-wlr.service`, and
`waybar.service.d/portal.conf` (Wants/After=xdg-desktop-portal.service). Portal cold start 51 s → 0.5 s, bar draws ~1 s after start.
When PipeWire is enabled (camera via libcamera/PipeWire, screen sharing): unmask pipewire + xdg-desktop-portal-wlr and set ScreenCast=wlr.

## 6. Cameras (added 2026-10-07; mainline has no driver)
- Kernel: the out-of-tree MT8183 seninf / camsv / csi-phy drivers live in **https://github.com/vpavlin/mt8183-camera** (patches + build notes). The camera kernel
  (`6.12.50-stb-cbm-cam`) was signed with devkeys into **KERN-B (p4, priority 5)**, so slot B is now the camera kernel and KERN-A (p2, IPv6 kernel) is the fallback;
  `cgpt show /dev/mmcblk0` to check. Kernel changes: try a spare slot first with `-T 1`, mark `-S 1` after a good boot.
- Userspace: libcamera 0.7.1 (software ISP, CPU debayer) → PipeWire 1.6.9 → Brave (`--enable-features=WebRtcPipeWireCamera`, in brave.service).
  PipeWire runs only as the camera graph: `camera-pipewire.service` + `camera-wireplumber.service` (user units, video only; PulseAudio keeps audio).
  `LIBCAMERA_IPA_CONFIG_PATH=~/.config/libcamera/ipa` (drop-ins) → `ov02a10.yaml` (front, colour matrix tuned by eye) and `ov8856.yaml` (rear).
- Rule: after restarting the camera services, close Brave cleanly (the service restarts it) or it keeps "no camera access".
- `duet-web.service` serves `~/.local/share/duet/` on http://127.0.0.1:8765 (camera.html photo page; file:// pages lose camera permission).
  `duet-camera-settings` is the V4L2/PipeWire controls app (desktop entry included).
- Open: front-camera colour cast (fix pending in libcamera 0.7.2 / a patched build); Bluetooth headset mic (SCO over PCM/I2S) untested.

## 7. Keyboard layout (added 2026-10-07/08)
- sway: `xkb_layout cz,us` (Alt+Shift switches). `kbd-layout-keeper` (exec from sway) remembers the layout you last chose in `~/.cache/kbd-layout-index` and re-applies it
  when the keyboard cover is re-attached or a new session starts (otherwise sway resets to Czech).
- waybar `custom/layout` runs `kbd-layout-label` every second: it prints cz/us of the real keyboards and ignores virtual ones. The stock `sway/language` module
  went blank whenever the on-screen keyboard (`wvkbd`, layout "wvkbd") or `wtype` was the last active device.

## 8. Battery charge limit (added 2026-10-08)
- `battery-limit.service` (root; `/usr/local/sbin/battery-limit`) keeps the battery between LOWER and UPPER percent while on AC. Config `/etc/default/battery-limit`
  (`UPPER=80`, `LOWER=75`; UPPER=100 = off; owned by the user so the quick-settings slider can write it; the daemon clamps what it reads, re-reads every 20 s).
- Mechanism: ChromeOS EC `EC_CMD_CHARGE_CONTROL` (0x96) **version 1** over `/dev/cros_ec` (mode 0 normal, 1 idle). The kernel has no cros_charge-control driver.
  In idle this EC stops charging and the battery carries the load, so the level saws between UPPER and LOWER.
- DANGER: never call 0x96 **version 2** (even a "GET"): on this EC firmware it is executed as a SET idle and silently stops charging.
  If charging looks stuck: `sudo /usr/local/sbin/battery-limit --normal`.
- quick-settings has a "Charge limit" slider (50-100, step 5, 100 = off; LOWER = UPPER-5).

## 9. Swap, disk
- 4 GB swapfile on /home: `btrfs filesystem mkswapfile --size 4g /home/swapfile`, fstab `/home/swapfile none swap sw,pri=10,nofail 0 0`
  (the old 512 MB swap on the small root partition is commented out). Root (p5) has only ~2 GB free: keep big things in /home.

## 10. Basecamp modules and the Shrooms agent
- Basecamp modules are installed by hand from `.lgx` (tar.gz, not zip) into `~/.local/share/Logos/LogosBasecamp/{modules,plugins}/<name>`: copy
  `variants/linux-arm64/*` + `manifest.json` into the dir, add a `variant` file containing `linux-arm64`; UI views also need `assets/icon.png`
  (copy `icon.png` there) or the launcher shows two letters. Core modules load only when their view is opened. Logs: `~/.local/share/Logos/LogosBasecamp/logs/*.log`,
  `journalctl --user -u basecamp`. Restart: `systemctl --user restart basecamp`.
- The basecamp-0.3 set must be installed together (scala 0.11.0, loam_core 0.6.1, delivery_module 0.3.0, ble_mesh 0.2.1, keycard 1.1.0); an old delivery_module 0.9.0 crashes (SIGSEGV).
- shrooms-board (board_core + board view, from Jimmy/pi5, `https://github.com/jimmy-claw/shrooms-board`): events persist in
  `~/.local/share/Logos/LogosBasecamp/module_data/board_core/*/board-events.json` and survive restarts and upgrades. The Qt bundled with Basecamp differs from a dev Qt
  (assigning to an undeclared property throws; focus does not propagate into a wrapper's child) — test views on the device.
- Native arm64 binaries must avoid LSE: inline `swp/cas/ldadd/...` outside the `__aarch64_*` helpers means SIGILL here (`QEMU_CPU=cortex-a53` to test).
- shrooms-agent runs sessions on Sonnet: `shrooms-agent.service.d/model.conf` execs `~/.local/bin/claude-sonnet` (wrapper around the `claude` CLI, which is not in this kit).

## 11. Keeping this kit current
`./install.sh` copies the trees to the device; `./sync-from-device.sh` copies the live files back into the repo (run it after changing any tracked file, then commit and push).
Not tracked on purpose: `/etc/shrooms/` (mesh key), SSH keys, the `claude` binary and `parakeet-cli`, anything under `~/.local/share/Logos`, camera kernel images.
The default password `changeme` of the velvet-os image is public; change it (`passwd`) and the SSH key list on every new device.

## 12. Wi-Fi panel (added 2026-10-08)
`wifi-settings` (GTK4/libadwaita, same look as quick-settings; waybar network icon on-click, app id `duet.wifi` floats via app-tabs): on/off switch, refresh, list of
visible networks (connected one outlined, saved ones with a forget button), tap a saved/open network to connect, tap a secured new one for an inline password field.
Scanning takes ~6-7 s on this radio (the cache is empty while it scans), so the app triggers `nmcli dev wifi rescan`, waits, then lists. Uses nmcli only.
Both popup panels (`duet.wifi`, `duet.quicksettings`) share the same behaviour: sway rule `for_window [app_id="duet\\.(wifi|quicksettings)"] floating enable, move position center`,
fixed size (Wi-Fi 560x480 so it still fits above the on-screen keyboard), they close when focus leaves them, and opening one kills the other (`one_panel()` in both scripts).

## 13. External screen / projector (added 2026-10-10)
USB-C hub with HDMI shows up as sway output `DP-1` (works out of the box on 6.12; this hub only gives 1080p at 30 Hz, 720p at 60 Hz).
Only mirroring makes sense on a touch tablet where windows can't be dragged to the other screen: `display-mirror on|off|status|mode` runs `wl-mirror` (apt: wl-mirror)
fullscreen on the external output via a transient user unit `display-mirror.service`; sway rule `no_focus` for app_id `at.yrlf.wl_mirror`, and app-tabs ignores it.
`display-settings` is the GTK panel (switch + quality 1080p30 / 720p60, app id `duet.display`, floated/centred like the other panels); waybar `custom/display`
(`display-icon`, polls every 2 s) shows the icon only while an external screen is connected, green while mirroring. Unplugging stops the mirror automatically (the output disappears).
