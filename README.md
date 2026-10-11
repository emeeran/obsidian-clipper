# Obsidian Clipper

A fast, secure Linux CLI for capturing highlighted text, screenshots, and OCR
content directly into your [Obsidian](https://obsidian.md) vault via the
[Local REST API](https://github.com/cpbotha/obsidian-local-rest-api) plugin —
with automatic citations from PDFs, EPUBs, browsers, and code editors.

Bind it to a hotkey, highlight something, press the key, and it's in your vault
with a citation before your finger leaves the keyboard.

```bash
obsidian-clipper        # capture highlighted text + auto citation
obsidian-clipper -s     # screenshot + OCR + citation
```

> 📖 **[Full user manual → docs/manual.md](docs/manual.md)** — every flag,
> template, profile, and the Python API.

---

## Features

- **Text capture** — primary selection (X11) or clipboard, with `--selection`
- **Screenshot capture** — flameshot / grim+slurp / scrot, with annotation
- **Auto-OCR** — Tesseract text extraction, multi-language (`eng+deu`)
- **Citation detection** — PDFs, EPUBs, browsers, JetBrains/VSCode, Zotero, LibreOffice
- **Capture profiles** — built-in `research` / `quick` / `code` / `web` + your own via TOML
- **Templates** — `{{placeholders}}`, `{{#if}}`/`{{#unless}}`/`{{#each}}`, `@file` & named templates
- **Multi-vault** — `--vault work` reads `OBSIDIAN_WORK_*` config
- **Daily notes** — `--daily` appends to today's note
- **Resilient** — transport retries, `obsidian://` URI fallback, no-display detection
- **Secure** — path-traversal protection on every API path, no shell injection, env-based keys
- **Desktop notifications** — feedback on every capture

---

## Requirements

**Python 3.10+** and the Obsidian **Local REST API** plugin.

**System dependencies (Debian/Ubuntu):**

| X11                                  | Wayland                |
| ------------------------------------ | ---------------------- |
| `xclip`                              | `wl-clipboard`         |
| `flameshot` (recommended) or `scrot` | `grim` + `slurp`       |
| `xdotool`                            | `hyprctl` or `swaymsg` |
| `tesseract-ocr`                      | `tesseract-ocr`        |
| `libnotify-bin`                      | `libnotify-bin`        |

```bash
# X11
sudo apt install xclip flameshot tesseract-ocr libnotify-bin xdotool

# Wayland
sudo apt install wl-clipboard grim slurp tesseract-ocr libnotify-bin
```

---

## Installation

**Option A — uv (recommended)**

```bash
uv sync
uv pip install -e .
# or, for an isolated global install on PATH:
uv tool install .
```

**Option B — pip**

```bash
pip install -e .
```

**Option C — self-contained `.deb`** (bundles all Python deps; pulls system tools)

```bash
scripts/build-deb.sh                                  # → dist/obsidian-clipper_<ver>_all.deb
sudo apt install ./dist/obsidian-clipper_*.deb        # installs + recommended tools
```

Verify:

```bash
obsidian-clipper --version    # obsidian-clipper 1.0.1
```

---

## Quick Start

**1. Set up Obsidian** — install & enable the **Local REST API** community
plugin, then copy its **API Key**.

**2. Configure**

```bash
mkdir -p ~/.config/obsidian-clipper
cp .env.example ~/.config/obsidian-clipper/.env
# edit …/.env and set OBSIDIAN_API_KEY
```

**3. Capture**

```bash
obsidian-clipper        # highlight text, then run
obsidian-clipper -s     # select a screen area → OCR → save
```

---

## Usage

```bash
# Text + auto citation
obsidian-clipper

# Screenshot + OCR + citation
obsidian-clipper -s

# Clipboard instead of primary selection (handy on Wayland)
obsidian-clipper --selection clipboard

# Append to a specific note
obsidian-clipper --append -n "Journal.md"

# Use the research profile (auto-tags, OCR, append mode)
obsidian-clipper --profile research

# Append to today's daily note
obsidian-clipper --daily

# German OCR on a screenshot
obsidian-clipper -s --ocr-lang deu

# Interactive note picker (fzf / rofi)
obsidian-clipper --pick

# Custom template
obsidian-clipper --template "{{#if citation}}*{{citation}}*\n{{/if}}{{text}}"

# Annotate before saving (flameshot)
obsidian-clipper -s --annotate

# Preview without saving
obsidian-clipper --dry-run
```

---

## Global Shortcuts (GNOME)

| Action                      | Shortcut     | Command               |
| --------------------------- | ------------ | --------------------- |
| Capture text + citation     | `Ctrl+Alt+C` | `obsidian-clipper`    |
| Screenshot + OCR + citation | `Ctrl+Alt+S` | `obsidian-clipper -s` |

```bash
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom3/ name 'Obsidian Clipper Text'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom3/ command 'obsidian-clipper'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom3/ binding '<Primary><Alt>c'

gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom2/ name 'Obsidian Clipper Screenshot'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom2/ command 'obsidian-clipper -s'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom2/ binding '<Primary><Alt>s'
```

Sway / Hyprland bindings are in the [manual](docs/manual.md#keyboard-shortcuts).

---

## Configuration

Set via environment variables or `.env`. Loaded from `.env` in the current
directory, then `~/.config/obsidian-clipper/.env`. See the
[manual](docs/manual.md#configuration) for full detail.

| Variable                  | Default                      | Description                                  |
| ------------------------- | ---------------------------- | -------------------------------------------- |
| `OBSIDIAN_API_KEY`        | —                            | API key (**required**)                       |
| `OBSIDIAN_BASE_URL`       | `https://127.0.0.1:27124`    | API base URL                                 |
| `OBSIDIAN_DEFAULT_NOTE`   | `00-Inbox/Quick Captures.md` | Default target note                          |
| `OBSIDIAN_ATTACHMENT_DIR` | `Attachments/`               | Directory for uploaded images                |
| `OBSIDIAN_VERIFY_SSL`     | `true`                       | Verify TLS certificates                      |
| `OBSIDIAN_TIMEOUT`        | `10`                         | API request timeout (seconds)                |
| `OBSIDIAN_OCR_LANGUAGE`   | `eng`                        | Tesseract OCR language (`eng+deu` supported) |
| `LOG_FILE`                | —                            | Optional rotating log file                   |
| `LOG_FORMAT`              | `text`                       | `json` for structured logs                   |

Interactive setup: `obsidian-clipper --config-ui`

---

## Built-in Profiles

| Profile    | Tags              | Target                      | OCR | Append |
| ---------- | ----------------- | --------------------------- | --- | ------ |
| `research` | research, reading | `00-Inbox/Research Note.md` | yes | yes    |
| `quick`    | quick-capture     | `00-Inbox/`                 | no  | no     |
| `code`     | code, snippet     | `Code Snippets/`            | no  | no     |
| `web`      | web, article      | `Web Clippings/`            | yes | no     |

Define your own in `~/.config/obsidian-clipper/profiles.toml` — see
[Capture Profiles](docs/manual.md#capture-profiles).

---

## Project Structure

```
obsidian_clipper/
├── __init__.py            # Public API exports
├── _version.py            # Version
├── config.py              # Config, profiles, vaults
├── exceptions.py          # Exception hierarchy
├── capture/
│   ├── citation.py        # Citation parsing (PDF/EPUB/browser/editors)
│   ├── screenshot.py      # Screenshot capture + OCR
│   └── text.py            # Selection + active-window title
├── cli/
│   ├── args.py            # Argument parsing
│   ├── main.py            # Entry point / orchestration
│   └── tui.py             # Configuration TUI
├── obsidian/
│   └── api.py             # Obsidian REST API client
├── workflow/
│   ├── capture.py         # Capture session preparation
│   └── session.py         # Session data + markdown rendering
└── utils/
    ├── command.py         # Safe subprocess execution
    ├── logging.py         # Colored / JSON logging with rotation
    ├── notification.py    # Desktop notifications
    └── retry.py           # Retry with backoff
```

---

## Development

```bash
uv sync --all-extras
uv run pytest                       # 390+ tests
uv run ruff check . && uv run mypy obsidian_clipper
```

See [Development](docs/manual.md#development) and the
[Python API reference](docs/manual.md#python-api-reference).

---

## License

[MIT](LICENSE) © Meeran E Mandhini
