#!/usr/bin/env bash
# Muse Bridge installer (Linux). Run:  bash install/linux-install.sh
# Requires: python3 and Muse Code CLI logged in.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRIDGE="$REPO/muse_bridge.py"

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found. Install it first (e.g. apt install python3)."
  exit 1
fi

# Freedesktop autostart (works on GNOME, KDE, XFCE, most desktops)
mkdir -p "$HOME/.config/autostart"
DESKTOP="$HOME/.config/autostart/muse-bridge.desktop"
cat > "$DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Name=Muse Bridge
Comment=Muse subscription bridge (OpenAI-compatible local API)
Exec=/usr/bin/env python3 "$BRIDGE"
X-GNOME-Autostart-enabled=true
EOF
echo "OK: autostart created: $DESKTOP"

# Start it now
nohup python3 "$BRIDGE" >/dev/null 2>&1 &
echo "OK: bridge started."
echo "Test it:  curl http://127.0.0.1:11471/health"
echo "Next: in your app add an OpenAI-compatible provider with"
echo "      base URL  http://127.0.0.1:11471/v1  (no API key)."
