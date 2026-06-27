#!/usr/bin/env bash
# Ideation Dashboard launcher (macOS / Linux)
set -euo pipefail

cd "$(dirname "$0")/.."

URL="http://localhost:8765/dashboard/index.html"

# Open URL in default browser
if   command -v open      >/dev/null 2>&1; then open "$URL" &
elif command -v xdg-open  >/dev/null 2>&1; then xdg-open "$URL" &
elif command -v gnome-open>/dev/null 2>&1; then gnome-open "$URL" &
fi

python3 -m http.server 8765
