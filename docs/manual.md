# Obsidian Clipper — User Manual

> Complete reference for Obsidian Clipper v1.0.1

## Table of Contents

- [Introduction](#introduction)
- [Installation](#installation)
- [Obsidian Setup](#obsidian-setup)
- [Configuration](#configuration)
- [Capture Modes](#capture-modes)
- [Citation Detection](#citation-detection)
- [Capture Profiles](#capture-profiles)
- [Multi-Vault Support](#multi-vault-support)
- [Template System](#template-system)
- [CLI Reference](#cli-reference)
- [Output Format](#output-format)
- [Docker](#docker)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Python API Reference](#python-api-reference)

---

## Introduction

Obsidian Clipper is a Linux command-line tool that captures content — highlighted text, screenshots, and OCR-extracted text — and saves it directly to your Obsidian vault using the Local REST API plugin. It automatically detects your active window to create citations from PDF readers, browsers, and EPUB readers.

**How a typical capture works:**

1. Highlight text in any application (or skip this for screenshots)
2. Press your keyboard shortcut (e.g., `Ctrl+Alt+C`)
3. Obsidian Clipper reads the selection, detects the source window, and creates a citation
4. Content is formatted as an Obsidian callout block and saved to your vault
5. A desktop notification confirms the capture

---

## Installation

### System Dependencies

Obsidian Clipper needs a few system tools depending on your display server.

**X11 (most Linux desktops):**

```bash
sudo apt install xclip flameshot tesseract-ocr libnotify-bin xdotool
```

| Package | Purpose |
|---------|---------|
| `xclip` | Read primary selection (highlighted text) |
| `flameshot` | Screenshot capture with annotation |
| `scrot` | Alternative screenshot tool |
| `xdotool` | Detect active window title |
| `tesseract-ocr` | OCR text extraction |
| `libnotify-bin` | Desktop notifications |

**Wayland (Sway, Hyprland):**

```bash
sudo apt install wl-clipboard grim slurp tesseract-ocr libnotify-bin
```

| Package | Purpose |
|---------|---------|
| `wl-clipboard` | Read clipboard (Wayland) |
| `grim` | Screenshot capture |
| `slurp` | Area selection for grim |
| `tesseract-ocr` | OCR text extraction |
| `libnotify-bin` | Desktop notifications |

Window title detection on Wayland requires your compositor's tool: `hyprctl` (Hyprland) or `swaymsg` (Sway).

### Python Package

**Requires Python 3.10 or later.**

```bash
# Using uv (recommended)
uv sync
uv pip install -e .

# Using pip
pip install -e .
```

### Verifying Installation

```bash
obsidian-clipper --version
# obsidian-clipper 1.0.1
```

---

## Obsidian Setup

### 1. Install the Local REST API Plugin

1. Open Obsidian Settings → Community Plugins
2. Browse and install **Local REST API**
3. Enable the plugin

### 2. Get Your API Key

1. Open Obsidian Settings → Community Plugins → Local REST API
2. Copy the **API Key** shown in the settings

### 3. Configure the Clipper

```bash
# Create config directory
mkdir -p ~/.config/obsidian-clipper

# Copy the example config
cp .env.example ~/.config/obsidian-clipper/.env

# Edit with your API key
nano ~/.config/obsidian-clipper/.env
```

Or create a `.env` file in your project directory:

```bash
cp .env.example .env
# Edit .env and set OBSIDIAN_API_KEY=your_key_here
```

### 4. Test the Connection

```bash
obsidian-clipper --dry-run
```

If the connection works, you'll see a markdown preview. If not, check your API key and base URL.

---

## Configuration

### Environment Variables

All configuration is done via environment variables or `.env` files.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OBSIDIAN_API_KEY` | string | — | **Required.** Your Local REST API key. Must be a hex string (10+ characters). |
| `OBSIDIAN_BASE_URL` | string | `https://127.0.0.1:27124` | API base URL. Must start with `http://` or `https://`. |
| `OBSIDIAN_DEFAULT_NOTE` | string | `00-Inbox/Quick Captures.md` | Default target note for captures. |
| `OBSIDIAN_ATTACHMENT_DIR` | string | `Attachments/` | Directory for uploaded images. |
| `OBSIDIAN_VERIFY_SSL` | bool | `true` | Verify SSL certificates. Set to `false` for self-signed certs. |
| `OBSIDIAN_TIMEOUT` | int | `10` | API request timeout in seconds. |
| `OBSIDIAN_OCR_LANGUAGE` | string | `eng` | Tesseract language code. Supports multiple: `eng+deu`. |

### Config File Locations

Configuration is loaded from these locations (in order, later values override earlier):

1. `.env` in the current working directory
2. `~/.config/obsidian-clipper/.env`

### Example .env File

```bash
# Required
OBSIDIAN_API_KEY=a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4

# API connection
OBSIDIAN_BASE_URL=https://127.0.0.1:27124
OBSIDIAN_VERIFY_SSL=false
OBSIDIAN_TIMEOUT=15

# Note targets
OBSIDIAN_DEFAULT_NOTE=00-Inbox/Quick Captures.md
OBSIDIAN_ATTACHMENT_DIR=Attachments/

# OCR
OBSIDIAN_OCR_LANGUAGE=eng

# Logging (optional)
LOG_LEVEL=INFO
# LOG_FILE=/tmp/obsidian-clipper.log
```

### Configuration TUI

Launch an interactive terminal UI to edit your configuration:

```bash
obsidian-clipper --config-ui
```

The TUI lets you set your API key, base URL, default note, and attachment directory without editing files manually.

### Validation Rules

- **API Key**: Required, must be a hexadecimal string of at least 10 characters
- **Base URL**: Required, must start with `http://` or `https://`
- **Timeout**: Must be a positive integer
- **OCR Language**: Must be non-empty (defaults to `eng`)

---

## Capture Modes

### Text Capture (Default)

Reads the currently highlighted text (X11 primary selection or Wayland clipboard) and saves it with a citation.

```bash
obsidian-clipper
```

**How it works:**
1. Reads the primary selection via `xclip` (X11) or `wl-paste` (Wayland)
2. Detects the active window title to generate a citation
3. Formats as an Obsidian callout block
4. Appends to the target note

### Screenshot Capture (`-s`)

Captures a screen area, optionally runs OCR, and uploads the image.

```bash
obsidian-clipper -s
```

**How it works:**
1. Captures the active window title *before* the screenshot tool takes over
2. Launches your screenshot tool (flameshot, grim, or scrot)
3. Select an area on screen
4. The image is optimized (format conversion, compression) and uploaded to your vault
5. If OCR is enabled, Tesseract extracts text from the image

**Screenshot tools:**

| Tool | Display Server | Features |
|------|---------------|----------|
| `flameshot` | X11 | Area selection, annotation, GUI editor |
| `scrot` | X11 | Simple area selection |
| `grim` + `slurp` | Wayland | Area selection |

Override the auto-detected tool:

```bash
obsidian-clipper -s --screenshot-tool grim
```

### OCR Processing

OCR runs automatically on screenshots when enabled (the default). Tesseract extracts text from the captured image.

```bash
# OCR on (default)
obsidian-clipper -s

# OCR off
obsidian-clipper -s --no-ocr

# Different language
obsidian-clipper -s --ocr-lang deu
```

**Multi-language OCR:**

```bash
obsidian-clipper -s --ocr-lang eng+deu
```

The OCR language must match a Tesseract language pack installed on your system. Install additional languages:

```bash
sudo apt install tesseract-ocr-deu tesseract-ocr-fra
```

### Annotation Mode (`--annotate`)

Opens the screenshot in Flameshot's editor before saving. Requires flameshot.

```bash
obsidian-clipper -s --annotate
```

### Image Format and Quality

```bash
# Save as WebP (smaller files)
obsidian-clipper -s --image-format webp --image-quality 80

# Save as JPEG
obsidian-clipper -s --image-format jpeg --image-quality 90
```

| Format | Default Quality | Notes |
|--------|----------------|-------|
| `png` | lossless | Best for text screenshots |
| `webp` | 85 | Good compression, smaller files |
| `jpeg` | 85 | Smallest files, lossy |

---

## Citation Detection

Obsidian Clipper automatically detects the active window title and parses it to create citations. This works by reading the window title before or after the capture.

### Supported PDF Readers

| Reader | Window Title Format |
|--------|-------------------|
| Evince | `Document.pdf — Page 42` |
| Zathura | `Document.pdf (42/100)` |
| Okular | `Doc.pdf : Page 42 - Okular` or `Title — Page 42 — Okular` |
| Generic | Any window containing `.pdf` with a page number |

### Supported EPUB Readers

| Reader | Notes |
|--------|-------|
| Foliate | Title and page extraction |
| Calibre | Title and page extraction |
| Thorium | Title and page extraction |
| FBReader | Title and page extraction |
| Generic | Any window containing `.epub` with a page number |

### Supported Browsers

| Browser | Window Title Format |
|---------|-------------------|
| Chrome / Chromium | `Page Title — Google Chrome` |
| Firefox | `Page Title — Mozilla Firefox` |
| Edge | `Page Title — Microsoft Edge` |
| Brave | `Page Title — Brave` |
| Vivaldi | `Page Title — Vivaldi` |

### Code Editors

| Editor | Window Title Format |
|--------|-------------------|
| VSCode | `filename.py - project - Visual Studio Code` |
| Generic | `filename.ext - ProjectName` |

### How Page Numbers Are Detected

The citation parser recognizes these page number formats:

- `page 42`, `p. 42`, `pg. 42`
- `(42/100)` or `42/100`
- `42 of 100`

### Retry Mechanism

When triggered via a global hotkey, the window focus may briefly shift to a transient window (like Flameshot's launcher or GNOME Shell). The clipper retries citation detection up to 6 times with a 0.12-second delay to let the focus return to the original window.

---

## Capture Profiles

Profiles are presets that configure tags, target note, OCR, and append mode in one flag.

### Built-in Profiles

| Profile | Tags | Target Note | OCR | Append |
|---------|------|-------------|-----|--------|
| `research` | research, reading | `00-Inbox/Research Note.md` | on | yes |
| `quick` | quick-capture | `00-Inbox/` | off | no |
| `code` | code, snippet | `Code Snippets/` | off | no |
| `web` | web, article | `Web Clippings/` | on | no |

### Using a Profile

```bash
# Research mode: appends to Research Note with auto-tags and OCR
obsidian-clipper --profile research

# Quick capture: no OCR, saves to inbox
obsidian-clipper --profile quick -s

# Code snippet
obsidian-clipper --profile code
```

### Profile Environment Overrides

Override any profile field with environment variables:

```bash
OBSIDIAN_PROFILE_RESEARCH_TAGS="ml,papers"
OBSIDIAN_PROFILE_RESEARCH_NOTE="Research/ML Papers.md"
```

Format: `OBSIDIAN_PROFILE_{PROFILE_NAME}_{FIELD}` where field is lowercase (`tags`, `note`, `ocr`, `append`).

---

## Multi-Vault Support

If you use multiple Obsidian vaults, you can configure vault-specific settings.

### Configuration

Set environment variables with the vault name as a prefix:

```bash
# Work vault
OBSIDIAN_WORK_API_KEY=abc123...
OBSIDIAN_WORK_BASE_URL=https://127.0.0.1:27124

# Personal vault
OBSIDIAN_PERSONAL_API_KEY=def456...
OBSIDIAN_PERSONAL_BASE_URL=https://127.0.0.1:27125
```

Any missing vault-specific variable falls back to the global default.

### Using a Vault

```bash
# Capture to the "work" vault
obsidian-clipper --vault work

# Screenshot to the "personal" vault with research profile
obsidian-clipper --vault personal --profile research -s
```

---

## Template System

Customize the output format using templates with placeholders and conditional blocks.

### Placeholders

| Placeholder | Description |
|-------------|-------------|
| `{{text}}` | Captured selected text |
| `{{ocr}}` | OCR text from screenshot |
| `{{citation}}` | Formatted citation string |
| `{{timestamp}}` | Full timestamp (`2024-01-15 10:30:00`) |
| `{{date}}` | Date only (`2024-01-15`) |
| `{{time}}` | Time only (`10:30:00`) |
| `{{tags}}` | Comma-separated tags |
| `{{source}}` | Source application name (e.g., `Chrome`, `Evince`) |
| `{{source_type}}` | Source type: `pdf`, `epub`, `browser`, or `unknown` |

### Conditional Blocks

Include content only when a field has a value:

```
{{#if field}}content{{/if}}
```

### Example Templates

**Research note with citation:**

```bash
obsidian-clipper --template "{{#if citation}}Source: {{citation}}\n{{/if}}{{text}}\n\nCaptured: {{date}} at {{time}}"
```

**Web clipping with source type:**

```bash
obsidian-clipper --template "[{{source_type}}] {{text}}\n{{#if source}}From: {{source}}{{/if}}"
```

**OCR-focused template:**

```bash
obsidian-clipper -s --template "{{#if ocr}}## OCR Text\n{{ocr}}{{/if}}{{#if text}}\n## Notes\n{{text}}{{/if}}"
```

---

## CLI Reference

### Complete Flag List

| Flag | Short | Type | Default | Description |
|------|-------|------|---------|-------------|
| `--screenshot` | `-s` | flag | off | Capture screenshot in addition to text |
| `--ocr` | `-o` | flag | on | Perform OCR on screenshot (default: on) |
| `--no-ocr` | | flag | off | Disable OCR processing |
| `--note PATH` | `-n` | string | config default | Target note path |
| `--tags TAGS` | `-t` | string | — | Comma-separated tags |
| `--template TMPL` | | string | — | Custom template string |
| `--ocr-lang LANG` | | string | config default | OCR language code |
| `--image-format` | | choice | `png` | Image format: `png`, `webp`, `jpeg` |
| `--image-quality` | | int | `85` | Image quality (1–100) |
| `--screenshot-tool` | | choice | `auto` | Tool: `auto`, `flameshot`, `grim`, `scrot` |
| `--profile NAME` | `-p` | string | — | Use a capture profile |
| `--append` | `-a` | flag | off | Append to existing note |
| `--annotate` | | flag | off | Open in flameshot editor first |
| `--pick` | | flag | off | Interactive note picker (fzf) |
| `--vault NAME` | | string | — | Use a named vault config |
| `--dry-run` | | flag | off | Preview without saving |
| `--config-ui` | | flag | off | Launch configuration TUI |
| `--verbose` | `-v` | flag | off | Verbose output (INFO level) |
| `--debug` | | flag | off | Debug output (DEBUG level) |
| `--log-file PATH` | | path | — | Write logs to file |
| `--json-logs` | | flag | off | JSON log format |
| `--version` | | — | — | Show version |
| `--help` | `-h` | — | — | Show help |

### Usage Examples

**Basic text capture:**
```bash
obsidian-clipper                        # Default: text + citation → Quick Captures.md
obsidian-clipper -n "Notes.md"          # Save to specific note
obsidian-clipper --append               # Append mode
```

**Screenshot capture:**
```bash
obsidian-clipper -s                     # Screenshot + OCR + citation
obsidian-clipper -s --no-ocr            # Screenshot without OCR
obsidian-clipper -s --annotate          # Annotate before saving
obsidian-clipper -s --image-format webp # WebP format
```

**Profiles:**
```bash
obsidian-clipper --profile research     # Research mode (OCR + append)
obsidian-clipper -s --profile web       # Web clipping with OCR
obsidian-clipper --profile quick        # Quick text capture, no OCR
```

**Multi-vault:**
```bash
obsidian-clipper --vault work           # Use "work" vault config
obsidian-clipper --vault personal -s    # Screenshot to personal vault
```

**Advanced:**
```bash
obsidian-clipper --dry-run              # Preview capture as markdown
obsidian-clipper --pick                 # Pick target note with fzf
obsidian-clipper --config-ui            # Configure interactively
obsidian-clipper --template "..."       # Custom template
obsidian-clipper --debug --log-file /tmp/clipper.log  # Debug logging
```

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Error (connection failure, no content, validation error) |

---

## Output Format

### Text Capture

Content is formatted as an Obsidian callout block:

```markdown
---
tags:
  - research
  - pdf
---

### 2024-01-15

> [!quote] — Book.pdf, p.42 · Evince
>
> The captured text appears here
>
```

### Screenshot Capture

Screenshots use an image callout:

```markdown
---
tags:
  - web
  - article
---

### 2024-01-15

> [!image] — Page Title · Chrome
>
> ![[Attachments/capture_20240115_abc123.png]]
>
```

### Frontmatter

YAML frontmatter is added when creating new notes (not when appending). Tags come from:
1. The `--tags` flag or profile
2. Auto-generated tags based on source type (`pdf`, `research`, `web`, `article`, etc.)

### File Naming

When the target is a directory (ends with `/`), a new note is created with a name derived from the captured content:

```
00-Inbox/Captured text preview abc123.md
```

The filename includes a 6-character hash to prevent collisions.

---

## Docker

### Building the Image

```bash
docker compose build
```

The Dockerfile uses a multi-stage build:
1. **Builder stage**: Python 3.12-slim with uv to install dependencies
2. **Runtime stage**: Minimal image with a non-root user

### Running with Docker Compose

The `docker-compose.yml` reads your `.env` file automatically:

```bash
docker compose run clipper obsidian-clipper --help
docker compose run clipper obsidian-clipper -s
```

### Configuration

Set environment variables in `.env` or pass them directly:

```bash
docker compose run -e OBSIDIAN_API_KEY=your_key clipper obsidian-clipper
```

### Health Check

The compose file includes a health check that runs `obsidian-clipper --help` every 30 seconds.

---

## Keyboard Shortcuts

### GNOME (X11)

Register global shortcuts using `gsettings`:

```bash
# Text capture: Ctrl+Alt+C
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom3/ name 'Obsidian Clipper Text'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom3/ command 'obsidian-clipper'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom3/ binding '<Primary><Alt>c'

# Screenshot: Ctrl+Alt+S
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom2/ name 'Obsidian Clipper Screenshot'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom2/ command 'obsidian-clipper -s'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom2/ binding '<Primary><Alt>s'
```

### Sway / Hyprland

Add keybindings to your config:

```
# Sway (config)
bindsym Ctrl+Alt+c exec obsidian-clipper
bindsym Ctrl+Alt+s exec obsidian-clipper -s
```

```
# Hyprland (hyprland.conf)
bind = CTRL_ALT, c, exec, obsidian-clipper
bind = CTRL_ALT, s, exec, obsidian-clipper -s
```

---

## Troubleshooting

### Connection Errors

**"Failed to connect to Obsidian API"**

- Ensure Obsidian is running and the Local REST API plugin is enabled
- Check your API key in `.env`
- Verify the base URL matches your plugin settings (default: `https://127.0.0.1:27124`)
- If using HTTPS with a self-signed cert, set `OBSIDIAN_VERIFY_SSL=false`

### OCR Not Working

**No text extracted from screenshots**

- Verify Tesseract is installed: `tesseract --version`
- Check that the correct language pack is installed: `tesseract --list-langs`
- Try a different language: `obsidian-clipper -s --ocr-lang eng`
- Run with debug logging: `obsidian-clipper -s --debug`

### Screenshot Capture Issues

**Screenshot tool not found**

- Verify your screenshot tool is installed and in your PATH
- Explicitly specify the tool: `obsidian-clipper -s --screenshot-tool flameshot`

**Blank or corrupted screenshots**

- Try a different image format: `--image-format png`
- Check the image quality setting: `--image-quality 100`

### Citation Not Detected

**No citation from PDF reader**

- Make sure the PDF reader window is focused when you trigger the capture
- The window title must contain the filename or a recognized pattern
- Run with `--debug` to see the detected window title

### Debug Mode

```bash
# Console debug output
obsidian-clipper --debug

# Debug to file
obsidian-clipper --debug --log-file /tmp/clipper.log

# JSON-formatted logs
obsidian-clipper --debug --json-logs
```

---

## Development

### Setup

```bash
# Clone and install with dev dependencies
uv sync --all-extras

# Install pre-commit hooks
uv run pre-commit install
```

### Running Tests

```bash
# All tests
uv run pytest

# With coverage report
uv run pytest --cov=obsidian_clipper --cov-report=html

# Skip integration tests
uv run pytest -m "not integration"

# Only integration tests (requires running Obsidian)
OBSIDIAN_API_KEY=your_key uv run pytest -m integration
```

### Code Quality

```bash
# Lint
uv run ruff check .

# Type check
uv run mypy obsidian_clipper

# Format
uv run black obsidian_clipper tests
uv run isort obsidian_clipper tests
```

### CI Pipeline

The GitHub Actions pipeline runs on every push:

1. **Tests**: Python 3.10, 3.11, 3.12 matrix
2. **Linting**: ruff
3. **Type checking**: mypy
4. **Security**: pip-audit (dependency vulnerabilities), bandit (code security)

---

## Python API Reference

Obsidian Clipper can also be used as a Python library.

### Quick Example

```python
from obsidian_clipper import ObsidianClient, get_config, get_selected_text, get_citation

# Create a client
client = ObsidianClient()

# Capture text and citation
text = get_selected_text()
citation = get_citation()

# Build content and save
content = f"> {text}\n{citation.format_markdown()}"
client.append_to_note("Notes.md", content)
```

### Key Classes

#### `ObsidianClient`

API client for Obsidian Local REST API.

```python
from obsidian_clipper import ObsidianClient
from obsidian_clipper.config import Config

config = Config(api_key="your_key")
client = ObsidianClient(config)

# Check connection
client.check_connection()  # → bool

# Note operations
client.create_note("Notes/New.md", "# Hello")
client.append_to_note("Notes/New.md", "More content")
client.ensure_note_exists("Notes/New.md")

# Image upload
client.upload_image("/tmp/screenshot.png", dest_filename="capture.png")

# Context manager
with ObsidianClient(config) as client:
    client.append_to_note("Notes.md", "Content")
```

#### `Config`

Configuration dataclass.

```python
from obsidian_clipper.config import Config, get_config, set_config

# Get the global singleton
config = get_config()

# Create a custom config
config = Config(api_key="your_key", base_url="http://127.0.0.1:27124")

# Validate
errors = config.validate()
if errors:
    print("Config errors:", errors)
```

#### `Citation`

Represents a citation from a source document.

```python
from obsidian_clipper.capture import Citation, SourceType, get_citation

# Auto-detect from active window
citation = get_citation()
if citation:
    print(citation.title)        # "Book.pdf"
    print(citation.page)         # "42"
    print(citation.source)       # "Evince"
    print(citation.source_type)  # SourceType.PDF
    print(citation.format_markdown())  # "*Book.pdf, p. 42* — Evince"
    print(citation.get_auto_tags())    # ["pdf", "research"]
```

#### `CaptureSession`

Data structure for a capture with markdown rendering.

```python
from obsidian_clipper.workflow.session import CaptureSession
from obsidian_clipper.capture import Citation, SourceType

session = CaptureSession(
    text="Captured text here",
    citation=Citation(title="Book.pdf", page="42", source="Evince", source_type=SourceType.PDF),
    tags=["research"],
)

md = session.to_markdown()
print(md)
```

#### Template Rendering

```python
session = CaptureSession(text="Hello", tags=["web"])
session.template = "{{#if tags}}Tags: {{tags}}\n{{/if}}{{text}}"
md = session.to_markdown()
# Tags: web
# Hello
```
