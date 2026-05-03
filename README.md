# Obsidian Clipper

A Linux command-line tool for capturing highlighted text, screenshots, and OCR content directly into your Obsidian vault via the Local REST API plugin.

## Features

- **Text Capture** — Save any highlighted text (X11 primary selection or Wayland clipboard)
- **Screenshot Capture** — Select an area and save it as an image in your vault
- **Auto-OCR** — Extract text from screenshots using Tesseract
- **Citation Detection** — Auto-detect PDF page numbers, browser titles, and EPUB sources from the active window
- **Capture Profiles** — Built-in profiles for research, quick capture, code, and web clipping
- **Multi-Vault** — Switch between Obsidian vaults with a single flag
- **Templates** — Custom note templates with placeholders and conditionals
- **Desktop Notifications** — Visual feedback for every capture
- **Secure** — Path traversal protection, no shell injection, env-based API keys

## Requirements

**Python 3.10+** and the Obsidian [Local REST API](https://github.com/cpbotha/obsidian-local-rest-api) plugin.

**System Dependencies (Debian/Ubuntu):**

| X11 | Wayland |
|-----|---------|
| `xclip` | `wl-clipboard` |
| `flameshot` (recommended) or `scrot` | `grim` + `slurp` |
| `xdotool` | `hyprctl` or `swaymsg` |
| `tesseract-ocr` | `tesseract-ocr` |
| `libnotify-bin` | `libnotify-bin` |

```bash
# X11
sudo apt install xclip flameshot tesseract-ocr libnotify-bin xdotool

# Wayland
sudo apt install wl-clipboard grim slurp tesseract-ocr libnotify-bin
```

## Installation

**Option A: Install with uv (recommended)**
```bash
uv sync
uv pip install -e .
```

**Option B: Install with pip**
```bash
pip install -e .
```

**Option C: Docker**
```bash
docker compose build
```

## Quick Start

### 1. Set up Obsidian

1. Install the **Local REST API** community plugin in Obsidian
2. Enable the plugin and copy the **API Key** from its settings

### 2. Configure

```bash
cp .env.example .env
# Edit .env and paste your API key
```

### 3. Capture

```bash
# Highlight text anywhere, then run:
obsidian-clipper

# Select a screen area, OCR it, and save to Obsidian:
obsidian-clipper -s
```

## Usage

```bash
# Text capture with auto-detected citation
obsidian-clipper

# Screenshot + OCR + citation
obsidian-clipper -s

# Save to a specific note
obsidian-clipper -n "Research/Machine Learning.md"

# Append to an existing note
obsidian-clipper --append -n "Journal.md"

# Use the research profile (auto-tags, OCR, append mode)
obsidian-clipper --profile research

# Screenshot with German OCR
obsidian-clipper -s --ocr-lang deu

# Preview capture without saving
obsidian-clipper --dry-run

# Interactive note picker (requires fzf)
obsidian-clipper --pick

# Use a custom template
obsidian-clipper --template "{{#if citation}}*{{citation}}*{{/if}}\n\n{{text}}"

# Annotate screenshot before saving (requires flameshot)
obsidian-clipper -s --annotate
```

## Global Shortcuts (GNOME)

| Action | Shortcut | Command |
|--------|----------|---------|
| Capture Text + Citation | `Ctrl+Alt+C` | `obsidian-clipper` |
| Screenshot + OCR + Citation | `Ctrl+Alt+S` | `obsidian-clipper -s` |

```bash
# Register text capture shortcut
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom3/ name 'Obsidian Clipper Text'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom3/ command 'obsidian-clipper'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom3/ binding '<Primary><Alt>c'

# Register screenshot shortcut
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom2/ name 'Obsidian Clipper Screenshot'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom2/ command 'obsidian-clipper -s'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom2/ binding '<Primary><Alt>s'
```

## Configuration

Set via environment variables or `.env` file. See the [full manual](docs/manual.md) for details.

| Variable | Default | Description |
|----------|---------|-------------|
| `OBSIDIAN_API_KEY` | — | API key (required) |
| `OBSIDIAN_BASE_URL` | `https://127.0.0.1:27124` | API base URL |
| `OBSIDIAN_DEFAULT_NOTE` | `00-Inbox/Quick Captures.md` | Default target note |
| `OBSIDIAN_ATTACHMENT_DIR` | `Attachments/` | Directory for uploaded images |
| `OBSIDIAN_VERIFY_SSL` | `true` | Verify SSL certificates |
| `OBSIDIAN_TIMEOUT` | `10` | API request timeout (seconds) |
| `OBSIDIAN_OCR_LANGUAGE` | `eng` | Tesseract OCR language |

Config files are loaded from (in order): `.env` in current directory, then `~/.config/obsidian-clipper/.env`.

## Built-in Profiles

| Profile | Tags | Target | OCR | Append |
|---------|------|--------|-----|--------|
| `research` | research, reading | `00-Inbox/Research Note.md` | yes | yes |
| `quick` | quick-capture | `00-Inbox/` | no | no |
| `code` | code, snippet | `Code Snippets/` | no | no |
| `web` | web, article | `Web Clippings/` | yes | no |

## Project Structure

```
obsidian_clipper/
├── __init__.py            # Package exports
├── _version.py            # Version (1.0.1)
├── config.py              # Configuration, profiles, vaults
├── exceptions.py          # Custom exceptions
├── capture/
│   ├── citation.py        # Citation parsing (PDF, EPUB, browser)
│   ├── screenshot.py      # Screenshot capture and OCR
│   └── text.py            # Text selection and window title
├── cli/
│   ├── args.py            # CLI argument parsing
│   ├── main.py            # Main entry point
│   └── tui.py             # Configuration TUI
├── obsidian/
│   └── api.py             # Obsidian REST API client
├── workflow/
│   ├── capture.py         # Capture session preparation
│   └── session.py         # Session data, markdown rendering
└── utils/
    ├── command.py          # Safe subprocess execution
    ├── logging.py          # Colored console + file logging
    ├── notification.py     # Desktop notifications
    └── retry.py            # Retry with backoff
```

## License

MIT License
