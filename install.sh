#!/bin/bash
# Obsidian Clipper - Full Auto-Installer
# Targets: Ubuntu/Debian (GNOME)

set -e

echo "🚀 Starting Obsidian Clipper Installation..."

# 1. Install System Dependencies
echo "📦 Installing system dependencies (requires sudo)..."
sudo apt update
sudo apt install -y xclip flameshot tesseract-ocr libnotify-bin python3-pip xdotool

# 2. Install Python Dependencies
echo "🐍 Installing Python dependencies..."
pip3 install requests --break-system-packages 2>/dev/null || pip3 install requests

# 3. Setup Binary
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
echo "📂 Copying clipper to $BIN_DIR..."
cp clipper.py "$BIN_DIR/clipper"
chmod +x "$BIN_DIR/clipper"

# 4. Configure API Key
echo ""
read -p "🔑 Enter your Obsidian Local REST API Key: " USER_API_KEY
if [ -n "$USER_API_KEY" ]; then
    sed -i "s/API_KEY = \".*\"/API_KEY = \"$USER_API_KEY\"/" "$BIN_DIR/clipper"
    echo "✅ API Key configured."
else
    echo "⚠️ No API Key entered. Please edit $BIN_DIR/clipper manually later."
fi

# 5. Configure GNOME Keyboard Shortcuts
echo "⌨️ Configuring GNOME Keyboard Shortcuts..."

# Base paths
PATH_PREFIX="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings"
CUSTOM0="$PATH_PREFIX/custom0/"
CUSTOM1="$PATH_PREFIX/custom1/"

# Set Shortcut 0: Capture Text (Ctrl+Alt+C)
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$CUSTOM0 name 'Obsidian Clipper: Text'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$CUSTOM0 command "$BIN_DIR/clipper"
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$CUSTOM0 binding '<Primary><Alt>c'

# Set Shortcut 1: Capture Screenshot + OCR (Ctrl+Alt+S)
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$CUSTOM1 name 'Obsidian Clipper: Screenshot'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$CUSTOM1 command "$BIN_DIR/clipper -s"
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$CUSTOM1 binding '<Primary><Alt>s'

# Register the custom bindings
gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "['$CUSTOM0', '$CUSTOM1']"

echo ""
echo "✨ Installation Complete!"
echo "-----------------------------------"
echo "Shortcuts Ready:"
echo "  [Ctrl+Alt+C] -> Capture Text"
echo "  [Ctrl+Alt+S] -> Screenshot + OCR"
echo "-----------------------------------"
echo "Note: Ensure Obsidian is running with 'Local REST API' plugin enabled."
