#!/bin/sh
# Copy the live copies of every tracked file back into this repo (run on the Duet), then review `git diff`.
set -e
cd "$(dirname "$0")"
for f in $(find home -type f | sed 's|^home/||'); do [ -f "$HOME/$f" ] && cp -a "$HOME/$f" "home/$f"; done
for f in $(find etc usr -type f); do [ -f "/$f" ] && cp -a "/$f" "$f"; done
git status --short 2>/dev/null || true
