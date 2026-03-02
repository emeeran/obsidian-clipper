#!/bin/bash
# Obsidian Clipper - Full Auto-Installer
# Targets: Ubuntu/Debian (GNOME)

set -e

echo "🚀 Starting Obsidian Clipper Installation..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Install System Dependencies
echo "📦 Installing system dependencies (requires sudo)..."
sudo apt update
sudo apt install -y xclip flameshot tesseract-ocr libnotify-bin xdotool uv

# 2. Setup Binary Wrapper
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
echo "📂 Creating clipper wrapper in $BIN_DIR..."

cat > "$BIN_DIR/clipper" << 'WRAPPER_EOF'
#!/usr/bin/env python3
"""
Wrapper script for Obsidian Clipper.
This allows running from GNOME keyboard shortcuts.
"""

import subprocess
import sys

WRAPPER_EOF

# Append the project directory path
echo "PROJECT_DIR = \"$SCRIPT_DIR\"" >> "$BIN_DIR/clipper"

cat >> "$BIN_DIR/clipper" << 'WRAPPER_EOF'

subprocess.run(
    ["uv", "run", "--directory", PROJECT_DIR, "obsidian-clipper"] + sys.argv[1:],
    cwd=PROJECT_DIR,
)
WRAPPER_EOF

chmod +x "$BIN_DIR/clipper"
echo "✅ Wrapper created."

# 3. Configure API Key (store in .env file)
ENV_FILE="$SCRIPT_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo ""
    read -p "🔑 Enter your Obsidian Local REST API Key: " USER_API_KEY
    if [ -n "$USER_API_KEY" ]; then
        echo "OBSIDIAN_API_KEY=\"$USER_API_KEY\"" > "$ENV_FILE"
        echo "✅ API Key configured in $ENV_FILE"
    else
        echo "⚠️ No API Key entered. Please create $ENV_FILE manually later."
    fi
else
    echo "✅ Found existing .env file at $ENV_FILE"
fi

# 4. Configure GNOME Keyboard Shortcuts
echo "⌨️ Configuring GNOME Keyboard Shortcuts..."

# Use unique paths to avoid conflicts
PATH_PREFIX="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings"
CUSTOM_TEXT="$PATH_PREFIX/obsidian-clipper-text/"
CUSTOM_SCREENSHOT="$PATH_PREFIX/obsidian-clipper-screenshot/"

# Set Shortcut: Capture Text (Ctrl+Alt+C)
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$CUSTOM_TEXT name 'Obsidian Clipper: Text'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$CUSTOM_TEXT command "$BIN_DIR/clipper"
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$CUSTOM_TEXT binding '<Primary><Alt>c'

# Set Shortcut: Capture Screenshot + OCR (Ctrl+Alt+S)
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$CUSTOM_SCREENSHOT name 'Obsidian Clipper: Screenshot'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$CUSTOM_SCREENSHOT command "$BIN_DIR/clipper -s"
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$CUSTOM_SCREENSHOT binding '<Primary><Alt>s'

# Register the custom bindings (preserving existing ones)
CURRENT_BINDINGS=$(gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings)
# Remove trailing ] and add new bindings
if [[ "$CURRENT_BINDINGS" == *"obsidian-clipper"* ]]; then
    echo "✅ Shortcuts already registered"
else
    NEW_BINDINGS="${CURRENT_BINDINGS%]}, '$CUSTOM_TEXT', '$CUSTOM_SCREENSHOT']"
    gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "$NEW_BINDINGS"
    echo "✅ Shortcuts registered"
fi

echo ""
echo "✨ Installation Complete!"
echo "-----------------------------------"
echo "Shortcuts Ready:"
echo "  [Ctrl+Alt+C] -> Capture Text"
echo "  [Ctrl+Alt+S] -> Screenshot + OCR"
echo "-----------------------------------"
echo "Project directory: $SCRIPT_DIR"
echo "Note: Ensure Obsidian is running with 'Local REST API' plugin enabled."
