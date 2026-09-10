#!/usr/bin/env bash
# Muse Bridge installer (macOS). Run:  bash install/macos-install.sh
# Requires: python3 and Muse Code CLI logged in.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRIDGE="$REPO/muse_bridge.py"

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found. Install it first (e.g. brew install python)."
  exit 1
fi

# launchd agent (starts the bridge at login and keeps it alive)
mkdir -p "$HOME/Library/LaunchAgents"
PLIST="$HOME/Library/LaunchAgents/com.muse-bridge.plist"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.muse-bridge</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/env</string>
    <string>python3</string>
    <string>$BRIDGE</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
</dict>
</plist>
EOF

launchctl unload "$PLIST" >/dev/null 2>&1 || true
launchctl load "$PLIST"
echo "OK: launchd agent installed: $PLIST"
echo "OK: bridge started."
echo "Test it:  curl http://127.0.0.1:11471/health"
echo "Next: in your app add an OpenAI-compatible provider with"
echo "      base URL  http://127.0.0.1:11471/v1  (no API key)."
