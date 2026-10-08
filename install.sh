#!/bin/sh
# Install the kit on a Duet that already runs the Debian image (see docs/SETUP-NOTES.md for packages and one-off steps).
# User files go to $HOME, system files to /, then the services are enabled. Run as the normal user; sudo is asked for.
set -e
cd "$(dirname "$0")"
cp -a home/. "$HOME"/
sudo cp -a etc/. /etc/
sudo cp -a usr/. /usr/
sudo chmod 755 /usr/local/sbin/battery-limit
sudo chown "$USER:$USER" /etc/default/battery-limit
sudo systemctl daemon-reload
sudo systemctl enable --now battery-limit.service
systemctl --user daemon-reload
systemctl --user enable basecamp.service brave.service foot.service waybar.service duet-web.service
systemctl --user enable camera-pipewire.service   # camera graph; needs the camera kernel (docs section 6)
echo "Done. Log out/in (or reboot) to start the session."
