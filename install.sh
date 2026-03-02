#!/bin/bash
# Obsidian Clipper Installer - Ubuntu/Debian (GNOME)

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Install dependencies
sudo apt update && sudo apt install -y xclip flameshot tesseract-ocr libnotify-bin xdotool uv

# Create wrapper
mkdir -p ~/.local/bin
cat > ~/.local/bin/clipper << EOF
#!/usr/bin/env python3
import subprocess, sys
subprocess.run(["uv", "run", "--directory", "$SCRIPT_DIR", "obsidian-clipper"] + sys.argv[1:], cwd="$SCRIPT_DIR")
EOF
chmod +x ~/.local/bin/clipper

# API key
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    read -p "Obsidian API Key: " key
    [ -n "$key" ] && echo "OBSIDIAN_API_KEY=\"$key\"" > "$SCRIPT_DIR/.env"
fi

# Shortcuts
BIND="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings"
TEXT="$BIND/obsidian-clipper-text/"
SHOT="$BIND/obsidian-clipper-screenshot/"

gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$TEXT name 'Clipper: Text'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$TEXT command "$HOME/.local/bin/clipper"
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$TEXT binding '<Primary><Alt>c'

gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$SHOT name 'Clipper: Screenshot'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$SHOT command "$HOME/.local/bin/clipper -s"
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$SHOT binding '<Primary><Alt>s'

CURRENT=$(gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings)
[[ "$CURRENT" != *"obsidian-clipper"* ]] && gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "${CURRENT%]}, '$TEXT', '$SHOT']"

echo "
Ctrl+Alt+C  Copy selected text → Quick Captures
Ctrl+Alt+S  Screenshot area → OCR → Quick Captures"
