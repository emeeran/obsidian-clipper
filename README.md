# Obsidian Clipper

A streamlined Linux tool for capturing highlighted text, screenshots, and OCR'ed content directly into your Obsidian vault via the Local REST API.

## Features

- **Text Capture**: Instantly save any highlighted text (X11/Wayland).
- **Screenshot Capture**: Select an area and save it as an image in your vault.
- **Auto-OCR**: Automatically extracts text from captured screenshots using Tesseract.
- **Citation Detection**: Automatically extracts PDF page numbers and browser titles.
- **Desktop Notifications**: Visual feedback for every capture.
- **Note Integration**: Appends content to a specific note with timestamps.
- **Secure Configuration**: Environment variables and .env file support.
- **Modular Architecture**: Clean, testable, and extensible codebase.

## Quick Setup

### 1. Requirements

**System Dependencies (Ubuntu/Debian):**
```bash
# X11 (Default)
sudo apt install xclip flameshot tesseract-ocr libnotify-bin xdotool

# Wayland
sudo apt install wl-clipboard grim slurp tesseract-ocr
```

**Python Dependencies:**
```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

### 2. Obsidian Configuration

1. Install the **Local REST API** plugin in Obsidian.
2. Enable it and copy your **API Key**.
3. Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```
4. Edit `.env` and paste your API key:
   ```
   OBSIDIAN_API_KEY=your_api_key_here
   ```

### 3. Installation

**Option A: Install with uv (recommended)**
```bash
uv sync
uv pip install -e .
```

**Option B: Manual installation**
```bash
mkdir -p ~/.local/bin
cp obsidian-clipper.py ~/.local/bin/obsidian-clipper
chmod +x ~/.local/bin/obsidian-clipper
```

## Global Shortcuts (GNOME)

| Action | Shortcut | Command |
|--------|----------|---------|
| Capture Text + Citation | `Ctrl+Alt+C` | `obsidian-clipper` |
| Screenshot + OCR + Citation | `Ctrl+Alt+S` | `obsidian-clipper -s` |

### Setting shortcuts via CLI:
```bash
# Register screenshot shortcut (Flameshot → OCR → Citation → Note)
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom2/ name 'Obsidian Clipper Screenshot'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom2/ command '/home/em/.local/bin/uv run --directory /home/em/code/wip/Obsidian-Clipper obsidian-clipper -s'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom2/ binding '<Primary><Alt>s'

# Register text capture shortcut (Selection → Citation → Note)
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom3/ name 'Obsidian Clipper Text'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom3/ command '/home/em/.local/bin/uv run --directory /home/em/code/wip/Obsidian-Clipper obsidian-clipper'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom3/ binding '<Primary><Alt>c'
```

## Usage

```bash
# Capture selected text with citation (default)
obsidian-clipper

# Screenshot → OCR → Citation → Note
# (No text selection needed for screenshots go directly to Obsidian)
obsidian-clipper -s

# Capture without citation
obsidian-clipper --no-cite

# Save to a specific note
obsidian-clipper -n "Research/Machine Learning.md"

# Use German OCR language
obsidian-clipper -s --ocr-lang deu

# Skip OCR processing
obsidian-clipper -s --no-ocr

# Show help
obsidian-clipper --help
```

## Configuration

Configuration is managed via environment variables. Create a `.env` file in your working directory or set environment variables directly:

| Variable | Description | Default |
|----------|-------------|---------|
| `OBSIDIAN_API_KEY` | Obsidian Local REST API key (required) | - |
| `OBSIDIAN_BASE_URL` | API base URL | `https://127.0.0.1:27124` |
| `OBSIDIAN_DEFAULT_NOTE` | Default note for captures | `00-Inbox/Quick Captures.md` |
| `OBSIDIAN_ATTACHMENT_DIR` | Directory for attachments | `Attachments/` |
| `OBSIDIAN_VERIFY_SSL` | Verify SSL certificates | `false` |
| `OBSIDIAN_TIMEOUT` | API timeout in seconds | `10` |
| `OBSIDIAN_OCR_LANGUAGE` | Default OCR language | `eng` |

## Vault Structure

The tool expects/creates:
- `00-Inbox/Quick Captures.md` (Inbox)
- `Attachments/` (Screenshots)

## Development

### Setup Development Environment

```bash
# Clone and install with dev dependencies
uv sync --all-extras

# Install pre-commit hooks
uv run pre-commit install
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=obsidian_clipper --cov-report=html
```

### Code Quality

```bash
# Format code
uv run black obsidian_clipper tests
uv run isort obsidian_clipper tests

# Lint
uv run ruff check obsidian_clipper tests

# Type check
uv run mypy obsidian_clipper
```

### Run All Checks

```bash
uv run black . && uv run isort . && uv run ruff check . && uv run mypy obsidian_clipper && uv run pytest
```

## Project Structure

```
obsidian_clipper/
├── __init__.py          # Package exports
├── __main__.py          # Module entry point
├── clipper.py           # CLI application
├── config.py            # Configuration management
├── exceptions.py        # Custom exceptions
├── capture/
│   ├── __init__.py
│   ├── text.py          # Text capture utilities
│   ├── screenshot.py    # Screenshot and OCR
│   └── citation.py      # Citation parsing
├── obsidian/
│   ├── __init__.py
│   └── api.py           # Obsidian REST API client
└── utils/
    ├── __init__.py
    ├── command.py       # Safe command execution
    └── notification.py  # Desktop notifications
tests/
├── test_capture.py
├── test_api.py
├── test_config.py
├── test_utils.py
└── test_clipper.py
```

## Security

- **API keys** are loaded from environment variables, not hardcoded
- **Path validation** prevents directory traversal attacks
- **No shell injection** - commands use argument lists, not shell strings
- **SSL verification** can be enabled for production use

## License

MIT License
