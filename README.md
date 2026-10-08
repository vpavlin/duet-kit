# duet-kit

Everything to turn a Lenovo IdeaPad Duet Chromebook (krane, MT8183) running the velvet-os Debian 13 image into a touch-first Sway tablet:
Shrooms-coloured waybar, quick settings (brightness, scale, volume, mic, battery charge limit), on-screen keyboard with a Czech row, auto-rotate,
app tabs, Basecamp + Brave + foot, cameras, battery limit.

- `home/`, `etc/`, `usr/` — the exact config files and scripts (paths relative to `$HOME` and `/`).
- `docs/SETUP-NOTES.md` — everything the files don't capture: base install without USB, packages, boot slots, cameras, services, gotchas.
- `install.sh` / `sync-from-device.sh` — copy to the device / back into the repo.

Related: https://github.com/vpavlin/mt8183-camera (camera kernel drivers).
No secrets belong here (mesh keys, SSH keys, tokens).
