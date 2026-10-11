# Obsidian Clipper — User Manual

> Complete reference for Obsidian Clipper v1.0.1

Obsidian Clipper is a Linux command-line tool that captures content —
highlighted text, screenshots, and OCR-extracted text — and saves it directly to
your Obsidian vault using the [Local REST API](https://github.com/cpbotha/obsidian-local-rest-api)
plugin. It automatically detects your active window to build citations from PDF
readers, EPUB readers, browsers, and code editors.

---

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
- [Fallbacks & Resilience](#fallbacks--resilience)
- [Packaging & Deployment](#packaging--deployment)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Python API Reference](#python-api-reference)

---

## Introduction

### How a capture works

1. Highlight text in any application (or skip this for screenshots).
2. Press your keyboard shortcut (e.g. `Ctrl+Alt+C`).
3. Obsidian Clipper reads the selection, detects the source window, and builds a citation.
4. Content is formatted as an Obsidian callout block and saved to your vault.
5. A desktop notification confirms the capture.

### Design principles

- **Fast** — runs in your graphical session; text and citation detection happen concurrently.
- **Secure** — path-traversal protection on every API path, no shell injection (all subprocess
  calls use arg lists), API keys kept in the environment.
- **Resilient** — automatic retries with backoff, an `obsidian://` URI fallback when the API is
  unreachable, and actionable errors (e.g. when no display server is detected).
- **Scriptable** — usable as a CLI *and* as a Python library.

---

## Installation

### Requirements

- **Python 3.10+**
- The Obsidian **Local REST API** community plugin
- A handful of system tools, depending on your display server

### System dependencies (Debian/Ubuntu)

**X11 (most desktops):**

```bash
sudo apt install xclip flameshot tesseract-ocr libnotify-bin xdotool
```

| Package | Purpose |
|---------|---------|
| `xclip` | Read the primary selection (highlighted text) |
| `flameshot` | Screenshot capture with annotation (recommended) |
| `scrot` | Alternative, simpler screenshot tool |
| `xdotool` | Detect the active window title |
| `tesseract-ocr` | OCR text extraction |
| `libnotify-bin` | Desktop notifications (`notify-send`) |

**Wayland (Sway, Hyprland, etc.):**

```bash
sudo apt install wl-clipboard grim slurp tesseract-ocr libnotify-bin
```

| Package | Purpose |
|---------|---------|
| `wl-clipboard` | Read clipboard / primary selection (`wl-paste`) |
| `grim` | Screenshot capture |
| `slurp` | Area selection for `grim` |
| `tesseract-ocr` | OCR text extraction |
| `libnotify-bin` | Desktop notifications |

Window-title detection on Wayland additionally requires your compositor's tool:
`hyprctl` (Hyprland) or `swaymsg` (Sway).

### Python package

```bash
# Using uv (recommended)
uv sync
uv pip install -e .

# Using pip
pip install -e .
```

For a stable, isolated install that puts `obsidian-clipper` on `PATH`:

```bash
uv tool install .     # or: pipx install .
```

### Verify

```bash
obsidian-clipper --version
# obsidian-clipper 1.0.1
```

---

## Obsidian Setup

### 1. Install the Local REST API plugin

1. Obsidian → **Settings → Community plugins**
2. Browse and install **Local REST API**
3. Enable the plugin

### 2. Copy your API key

1. **Settings → Community plugins → Local REST API**
2. Copy the **API Key** shown in the settings

### 3. Configure the clipper

```bash
mkdir -p ~/.config/obsidian-clipper
cp .env.example ~/.config/obsidian-clipper/.env
nano ~/.config/obsidian-clipper/.env     # paste your API key
```

You can also place a `.env` in your project directory (it takes precedence over
the user config dir).

### 4. Test the connection

```bash
obsidian-clipper --dry-run
```

If the connection works you'll see a markdown preview of the capture. If not,
check your API key and base URL (see [Troubleshooting](#troubleshooting)).

---

## Configuration

All configuration is done via environment variables or `.env` files.

### Environment variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OBSIDIAN_API_KEY` | string | — | **Required.** Local REST API key (hex string, 10+ chars). |
| `OBSIDIAN_BASE_URL` | string | `https://127.0.0.1:27124` | API base URL. Must start with `http://` or `https://`. |
| `OBSIDIAN_DEFAULT_NOTE` | string | `00-Inbox/Quick Captures.md` | Default target note. |
| `OBSIDIAN_ATTACHMENT_DIR` | string | `Attachments/` | Directory for uploaded images. |
| `OBSIDIAN_VERIFY_SSL` | bool | `true` | Verify TLS certificates. Set `false` for self-signed certs. |
| `OBSIDIAN_TIMEOUT` | int | `10` | API request timeout (seconds). |
| `OBSIDIAN_OCR_LANGUAGE` | string | `eng` | Tesseract language code. Supports combos: `eng+deu`. |
| `OBSIDIAN_OCR_PSM` | int | auto | Pin Tesseract page-segmentation mode (e.g. `6`). Default tries 3 and 6, keeping the higher-confidence result. |
| `OBSIDIAN_VAULT_NAME` | string | — | Vault name used by the `obsidian://` URI fallback. |
| `LOG_FILE` | path | — | Optional log file (rotated, 5 MB × 3). |
| `LOG_FORMAT` | string | `text` | Set to `json` for structured JSON log lines. |

> **Log level** is controlled by the `--verbose` (INFO) and `--debug` (DEBUG)
> flags, not an env var. The default level is `WARNING`.

### Config file locations

Config is loaded in order (later files do **not** override values already set):

1. `.env` in the current working directory
2. `~/.config/obsidian-clipper/.env`

### Example `.env`

```bash
# Required
OBSIDIAN_API_KEY=a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4

# Connection
OBSIDIAN_BASE_URL=https://127.0.0.1:27124
OBSIDIAN_VERIFY_SSL=false
OBSIDIAN_TIMEOUT=15

# Targets
OBSIDIAN_DEFAULT_NOTE=00-Inbox/Quick Captures.md
OBSIDIAN_ATTACHMENT_DIR=Attachments/

# OCR
OBSIDIAN_OCR_LANGUAGE=eng

# Vault name (used by the obsidian:// URI fallback)
OBSIDIAN_VAULT_NAME=My Vault

# Logging
LOG_FILE=/tmp/obsidian-clipper.log
LOG_FORMAT=text
```

### Configuration TUI

```bash
obsidian-clipper --config-ui
```

An interactive terminal UI to set your API key, base URL, default note, and
attachment directory. Saved files are mode `0600` (owner-only).

### Validation rules

- **API key** — required, must be hexadecimal, ≥ 10 characters
- **Base URL** — required, must start with `http://` or `https://`
- **Timeout** — must be a positive integer
- **OCR language** — must be non-empty (defaults to `eng`)

---

## Capture Modes

### Text capture (default)

Reads currently highlighted text and saves it with an auto-detected citation.

```bash
obsidian-clipper
```

**How it works:**

1. Reads the selection via `xclip` (X11) or `wl-paste` (Wayland)
2. Detects the active window title to build a citation
3. Formats the result as an Obsidian callout block
4. Saves (creates a new note or appends — see [CLI Reference](#cli-reference))

Steps 1 and 2 run **concurrently** to minimise latency.

### Selection source — `--selection`

By default the clipper reads the **primary selection** (what you highlight with
the mouse). Many Wayland applications never populate the primary selection; use
`--selection clipboard` to read the clipboard instead.

```bash
obsidian-clipper                        # primary selection (default)
obsidian-clipper --selection clipboard  # clipboard (Ctrl+C content)
```

| Selection | X11 tool | Wayland tool |
|-----------|----------|--------------|
| `primary` (default) | `xclip -selection primary` | `wl-paste -p` |
| `clipboard` | `xclip -selection clipboard` | `wl-paste` |

### Screenshot capture — `-s`

Captures a screen area, optionally runs OCR, uploads the image, and embeds it.

```bash
obsidian-clipper -s
```

**How it works:**

1. Captures the active window title *before* the screenshot tool grabs focus.
2. Launches your screenshot tool (`flameshot`, `grim`+`slurp`, or `scrot`).
3. You select an area on screen.
4. The image is optimised (format conversion + compression) and uploaded.
5. If OCR is on, Tesseract extracts text from the image.

**Screenshot tools:**

| Tool | Display server | Features |
|------|---------------|----------|
| `flameshot` | X11 | Area selection, annotation, GUI editor |
| `scrot` | X11 | Simple area selection |
| `grim` + `slurp` | Wayland | Area selection |

Override the auto-detected tool:

```bash
obsidian-clipper -s --screenshot-tool grim
```

### OCR

OCR runs automatically on screenshots (on by default).

```bash
obsidian-clipper -s              # OCR on (default)
obsidian-clipper -s --no-ocr     # OCR off
obsidian-clipper -s --ocr-lang deu        # German
obsidian-clipper -s --ocr-lang eng+deu    # Multi-language
```

The OCR language must match an installed Tesseract pack:

```bash
sudo apt install tesseract-ocr-deu tesseract-ocr-fra
tesseract --list-langs          # verify installed languages
```

### Annotation — `--annotate`

Opens the screenshot in Flameshot's editor before saving (requires flameshot):

```bash
obsidian-clipper -s --annotate
```

### Image format & quality

```bash
obsidian-clipper -s --image-format webp --image-quality 80
obsidian-clipper -s --image-format jpeg --image-quality 90
```

| Format | Default quality | Notes |
|--------|----------------|-------|
| `png` (default) | lossless | Best for text screenshots |
| `webp` | 85 | Strong compression, smaller files (uploaded as `image/webp`) |
| `jpeg` | 85 | Smallest files, lossy |

### Append vs. create — `--append`

By default a new note is created inside the target directory. Pass `--append`
(with a note path) to append to an existing note instead:

```bash
obsidian-clipper --append -n "Journal.md"
```

### Daily / periodic notes — `--daily`

Appends the capture to today's **daily note** via the periodic-notes API
(requires Obsidian's **Daily notes** core plugin, or the **Periodic Notes**
community plugin):

```bash
obsidian-clipper --daily
```

The Python API exposes `append_periodic_note(period, content)` for
`daily`, `weekly`, `monthly`, `quarterly`, and `yearly` periods (validated).

### Open after capture — `--open`

Open the created/appended note in Obsidian immediately:

```bash
obsidian-clipper -n "Inbox/Note.md" --open
```

### Interactive note picker — `--pick`

Choose the target note interactively with `fzf` (or `rofi` as fallback):

```bash
obsidian-clipper --pick
```

The picker lists every `.md` file in your vault.

### Preview without saving — `--dry-run`

Prints the markdown that *would* be saved, then exits:

```bash
obsidian-clipper --dry-run
```

---

## Citation Detection

Obsidian Clipper reads the active window title and parses it to build a citation.
The source type drives auto-tagging (`pdf`+`research`, `epub`+`reading`,
`web`+`article`).

### Supported PDF readers

| Reader | Window-title format |
|--------|-------------------|
| Evince | `Document.pdf — Page 42` |
| Zathura | `Document.pdf (42/100)` |
| Okular | `Doc.pdf : Page 42 - Okular` · `Title — Page 42 — Okular` |
| Atril / Xreader / MuPDF / Acrobat / Foxit | Recognised via the `.pdf` extension + page number |
| Generic | Any window containing `.pdf` with a page number |

### Supported EPUB readers

| Reader | Notes |
|--------|-------|
| Foliate · Calibre · Thorium · FBReader · Atril · Xreader · MuPDF | Title + page extraction |
| Generic | Any window containing `.epub` with a page number |

### Supported browsers

`Chrome` · `Chromium` · `Firefox` · `Edge` · `Brave` · `Vivaldi` — detected as
`Page Title — Browser`.

### Supported editors / IDEs

`VSCode`, JetBrains IDEs (IntelliJ, PyCharm, WebStorm, …), Sublime Text, TeXstudio,
Zotero, and LibreOffice (Writer/Calc/Impress/Draw/Math/Base) are recognised.
A generic `filename.ext - Project` fallback covers many other editors.

### Page-number formats recognised

`page 42` · `p. 42` · `pg. 42` · `(42/100)` · `42/100` · `42 of 100`

### Hotkey focus recovery

When triggered via a global hotkey, focus can briefly jump to a transient window
(Flameshot's launcher, GNOME Shell). The clipper retries citation detection up
to **6 times** with a 0.12 s delay so focus returns to the original window before
parsing. Titles from Flameshot / GNOME Shell / the clipper itself are ignored.

### Citation fallback

If no structured citation is parsed but a window title is available, the title is
used as a best-effort citation (source type `unknown`). If the title can't be
parsed at all, the capture still saves — just without a citation.

---

## Capture Profiles

Profiles are presets bundling tags, target note, OCR, and append mode behind one
flag.

### Built-in profiles

| Profile | Tags | Target | OCR | Append |
|---------|------|--------|-----|--------|
| `research` | research, reading | `00-Inbox/Research Note.md` | on | yes |
| `quick` | quick-capture | `00-Inbox/` | off | no |
| `code` | code, snippet | `Code Snippets/` | off | no |
| `web` | web, article | `Web Clippings/` | on | no |

```bash
obsidian-clipper --profile research        # OCR + append + tags
obsidian-clipper -s --profile web          # web clipping with OCR
obsidian-clipper --profile quick           # fast text capture, no OCR
```

Explicit CLI flags always override the profile.

### User-defined profiles

Define your own profiles in `~/.config/obsidian-clipper/profiles.toml`:

```toml
[recipes]
tags = "cooking,recipes"
note = "30-Recipes/Inbox/"
ocr = true
append = false

[meetings]
tags = "work,meeting-notes"
note = "Work/Meetings.md"
ocr = false
append = true
```

Then use them like the built-ins:

```bash
obsidian-clipper --profile recipes
```

### Per-profile environment overrides

Override any field via env vars of the form
`OBSIDIAN_PROFILE_{NAME}_{FIELD}` (field lowercase: `tags`, `note`, `ocr`,
`append`):

```bash
OBSIDIAN_PROFILE_RESEARCH_TAGS="ml,papers" \
OBSIDIAN_PROFILE_RESEARCH_NOTE="Research/ML Papers.md" \
obsidian-clipper --profile research
```

---

## Multi-Vault Support

Configure vault-specific settings with a `OBSIDIAN_{VAULT}_*` prefix. Any field
not set for the vault falls back to the global default.

```bash
# Work vault
OBSIDIAN_WORK_API_KEY=abc123...
OBSIDIAN_WORK_BASE_URL=https://127.0.0.1:27124

# Personal vault
OBSIDIAN_PERSONAL_API_KEY=def456...
OBSIDIAN_PERSONAL_BASE_URL=https://127.0.0.1:27125
```

```bash
obsidian-clipper --vault work                    # capture to "work" vault
obsidian-clipper --vault personal --profile research -s
```

---

## Template System

Customise the capture body with templates. A template is resolved in this order:

1. **`@path`** — if it starts with `@`, the rest is a file path to read.
2. **Named** — if it contains no `{{`, the clipper looks for
   `~/.config/obsidian-clipper/templates/<name>.md`.
3. **Inline** — otherwise the string is used verbatim.

```bash
obsidian-clipper --template "@~/templates/research.md"   # from file
obsidian-clipper --template research                     # named (templates/research.md)
obsidian-clipper --template "{{text}}"                   # inline
```

### Placeholders

| Placeholder | Value |
|-------------|-------|
| `{{text}}` | Captured selected text |
| `{{ocr}}` | OCR text from the screenshot |
| `{{citation}}` | Formatted citation string |
| `{{timestamp}}` | Full timestamp (`2024-01-15 10:30:00`) |
| `{{date}}` | Date (`2024-01-15`) |
| `{{time}}` | Time (`10:30:00`) |
| `{{tags}}` | Comma-separated tags |
| `{{source}}` | Source application (e.g. `Chrome`, `Evince`) |
| `{{source_type}}` | `pdf` · `epub` · `browser` · `unknown` |

### Conditionals & loops

| Block | Behaviour |
|-------|-----------|
| `{{#if field}}…{{/if}}` | Include when `field` is truthy |
| `{{#unless field}}…{{/unless}}` | Include when `field` is falsy |
| `{{#each tags}}…{{this}}…{{/each}}` | Iterate over tags |

### Examples

**Research note with citation:**

```bash
obsidian-clipper --template "{{#if citation}}Source: {{citation}}\n{{/if}}{{text}}\n\nCaptured: {{date}} at {{time}}"
```

**Per-tag list:**

```bash
obsidian-clipper --template "{{text}}\n\n{{#each tags}}- {{this}}\n{{/each}}"
```

**OCR-focused (screenshot):**

```bash
obsidian-clipper -s --template "{{#if ocr}}## OCR\n{{ocr}}{{/if}}{{#if text}}\n## Notes\n{{text}}{{/if}}"
```

---

## CLI Reference

### Flags

| Flag | Short | Type | Default | Description |
|------|-------|------|---------|-------------|
| `--screenshot` | `-s` | flag | off | Capture a screenshot (in addition to / instead of text) |
| `--ocr` | `-o` | flag | on | Run OCR on the screenshot (default on) |
| `--no-ocr` | | flag | off | Disable OCR |
| `--selection` | | choice | `primary` | Text source: `primary` or `clipboard` |
| `--note PATH` | `-n` | string | config | Target note / directory |
| `--tags TAGS` | `-t` | string | — | Comma-separated tags |
| `--template TMPL` | | string | — | Inline / named / `@file` template |
| `--ocr-lang LANG` | | string | config | Tesseract language code |
| `--image-format` | | choice | `png` | `png` · `webp` · `jpeg` |
| `--image-quality` | | int | `85` | Image quality (1–100) |
| `--screenshot-tool` | | choice | `auto` | `auto` · `flameshot` · `grim` · `scrot` |
| `--profile NAME` | `-p` | string | — | Use a capture profile |
| `--append` | `-a` | flag | off | Append to an existing note |
| `--annotate` | | flag | off | Open in the Flameshot editor first |
| `--daily` | | flag | off | Append to today's daily note |
| `--pick` | | flag | off | Interactive note picker (`fzf`/`rofi`) |
| `--open` | | flag | off | Open the note in Obsidian after saving |
| `--vault NAME` | | string | — | Use a named vault config |
| `--dry-run` | | flag | off | Preview as markdown without saving |
| `--config-ui` | | flag | off | Launch the configuration TUI |
| `--verbose` | `-v` | flag | off | INFO-level logging |
| `--debug` | | flag | off | DEBUG-level logging |
| `--log-file PATH` | | path | — | Write logs to a file (rotated) |
| `--json-logs` | | flag | off | Emit structured JSON log lines |
| `--version` | | — | — | Show version |
| `--help` | `-h` | — | — | Show help |

### Note-target resolution

- A path ending in `.md` → the **parent directory** is used (a new note is created there),
  unless `--append` is set (then it's treated as the note to append to).
- A path ending in `/` → a directory; a new note is created inside it.
- A bare name without `/` or `.md` → treated as a directory (a hint is logged).

### Examples

```bash
obsidian-clipper                              # text + citation → default note
obsidian-clipper -n "Research/ML.md"          # target a specific note
obsidian-clipper --append -n "Journal.md"     # append
obsidian-clipper -s                           # screenshot + OCR + citation
obsidian-clipper -s --no-ocr                  # screenshot only
obsidian-clipper -s --annotate --image-format webp
obsidian-clipper --profile research           # preset
obsidian-clipper --vault work --daily         # daily note in a vault
obsidian-clipper --pick                       # choose target with fzf
obsidian-clipper --dry-run                    # preview
obsidian-clipper --debug --json-logs --log-file /tmp/clipper.log
```

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Error (connection failure, no content, validation/capture error) |
| `130` | Interrupted (`Ctrl+C`) |

---

## Output Format

### Text capture

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

### Screenshot capture

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

YAML frontmatter with tags is added when **creating** new notes (not when
appending). Tags come from:

1. The `--tags` flag or profile
2. Auto-tags derived from the citation's source type

### File naming

When the target is a directory, a new note is named from a content preview plus a
6-character hash (BLAKE2b) to prevent collisions:

```
00-Inbox/Captured text preview a1b2c3.md
```

---

## Fallbacks & Resilience

### `obsidian://` URI fallback

If the Local REST API is unreachable, the clipper retries via the
`obsidian://new` URI scheme (opened with `xdg-open`) as a last resort. Long
captures may exceed URI length limits — a warning is logged when that's likely.

### No-display detection

If no X11/Wayland display server is detected (e.g. you're on a plain SSH
session), the "no text selected" error message includes a hint explaining that
capture requires a graphical session.

### Transport-level retries

The HTTP client retries transient failures (`429`, `5xx`) with exponential
backoff (3 attempts). Citation detection retries to survive hotkey focus jitter.

---

## Packaging & Deployment

### Self-contained `.deb`

Build a single `.deb` that bundles the app and **all** Python dependencies, with
system capture tools pulled in automatically:

```bash
scripts/build-deb.sh
# → dist/obsidian-clipper_<version>_all.deb

sudo apt install ./dist/obsidian-clipper_*.deb   # installs + Recommends (xclip, flameshot, …)
```

- **Architecture:** `all` (pure Python) — works on any Debian/Ubuntu arch.
- **Hard runtime dep:** `python3 (>= 3.10)` only.
- **Recommends:** `xclip`, `tesseract-ocr`, `libnotify-bin`, `xdotool`, `flameshot`.
- **Suggests:** `wl-clipboard`, `grim`, `slurp`, `scrot` (Wayland / alternatives).

The installed `/usr/bin/obsidian-clipper` wrapper execs the bundled module, so
keyboard shortcuts just call `obsidian-clipper`.

### Distribution to others

For sharing with other users, publish to PyPI (`uv build` → `twine upload`) so
they can install with `uv tool install obsidian-clipper`. The `.deb` is the
lowest-friction option for Debian/Ubuntu users since `apt` resolves the system
dependencies automatically.

---

## Keyboard Shortcuts

### GNOME (X11 / Wayland)

Register global shortcuts with `gsettings` (text: `Ctrl+Alt+C`, screenshot:
`Ctrl+Alt+S`):

```bash
# Text capture
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom3/ name 'Obsidian Clipper Text'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom3/ command 'obsidian-clipper'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom3/ binding '<Primary><Alt>c'

# Screenshot
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom2/ name 'Obsidian Clipper Screenshot'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom2/ command 'obsidian-clipper -s'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom2/ binding '<Primary><Alt>s'
```

### Sway

```
# ~/.config/sway/config
bindsym Ctrl+Alt+c exec obsidian-clipper
bindsym Ctrl+Alt+s exec obsidian-clipper -s
```

### Hyprland

```
# ~/.config/hypr/hyprland.conf
bind = CTRL_ALT, c, exec, obsidian-clipper
bind = CTRL_ALT, s, exec, obsidian-clipper -s
```

---

## Troubleshooting

### "Cannot connect to Obsidian at …"

- Ensure Obsidian is running and the **Local REST API** plugin is enabled.
- Check your API key in `.env`.
- Verify the base URL matches the plugin settings (default `https://127.0.0.1:27124`).
- For self-signed HTTPS certs, set `OBSIDIAN_VERIFY_SSL=false`.
- The clipper automatically falls back to the `obsidian://` URI scheme if the API
  is unreachable.

### "No text selected"

- Highlight text before pressing the shortcut, **or** use `--selection clipboard`
  if your app doesn't set the primary selection (common on Wayland).
- If the message adds "(No display server detected…)", you're likely on a plain
  SSH session — run the clipper from inside your graphical session.

### OCR not working

- Verify Tesseract: `tesseract --version`
- Check installed languages: `tesseract --list-langs`
- Try a language explicitly: `obsidian-clipper -s --ocr-lang eng`
- Run with debug: `obsidian-clipper -s --debug`

### Screenshot tool not found / blank screenshots

- Verify the tool is installed and on `PATH`.
- Force a tool: `obsidian-clipper -s --screenshot-tool flameshot`
- For corrupted output, try `--image-format png --image-quality 100`.

### Citation not detected

- Make sure the source window is focused when you trigger the capture.
- The window title must contain the filename or a recognised pattern.
- Run with `--debug` to see the detected window title.

### Getting more detail

```bash
obsidian-clipper --debug                              # console debug output
obsidian-clipper --debug --log-file /tmp/clipper.log  # debug to a file
obsidian-clipper --debug --json-logs                  # structured JSON logs
```

---

## Development

### Setup

```bash
uv sync --all-extras          # install with dev dependencies
uv run pre-commit install     # optional: install hooks
```

### Tests

```bash
uv run pytest                              # all tests
uv run pytest -m "not integration"        # skip live-API tests
uv run pytest --cov=obsidian_clipper --cov-report=html
OBSIDIAN_API_KEY=your_key uv run pytest -m integration   # live-API tests
```

### Code quality

```bash
uv run ruff check .          # lint
uv run mypy obsidian_clipper # type check
uv run black obsidian_clipper tests && uv run isort obsidian_clipper tests
uv run bandit -r obsidian_clipper/ -ll     # security (Medium+)
```

### CI

The GitHub Actions pipeline (`.github/workflows/ci.yml`) runs on every push/PR:

1. **Test matrix** — Python 3.10, 3.11, 3.12
2. **Lint** — ruff
3. **Type check** — mypy
4. **Security** — pip-audit (dependencies), bandit (code)

---

## Python API Reference

Obsidian Clipper can also be used as a library. Top-level imports:

```python
from obsidian_clipper import (
    ObsidianClient, Config, get_config, set_config,
    get_selected_text, get_citation, Citation, SourceType,
)
```

### `ObsidianClient`

Client for the Obsidian Local REST API.

```python
from obsidian_clipper import ObsidianClient
from obsidian_clipper.config import Config

config = Config(api_key="your_key")
client = ObsidianClient(config)

# Connection & vault
client.check_connection()                              # → bool
client.list_vault_files()                              # → list[str]  (all files)

# Notes
client.create_note("Notes/New.md", "# Hello")          # → bool
client.append_to_note("Notes/New.md", "more")          # → bool
client.ensure_note_exists("Notes/New.md")              # → bool (creates if missing)

# Images
client.upload_image("/tmp/screenshot.png",
                    dest_filename="capture.png",
                    dest_dir="Attachments/")           # → bool

# Search & metadata
client.search("query", context_length=200)             # → list[dict]
client.search_simple("query")                          # → list[str]
client.get_tags()                                      # → dict[str, dict]
client.list_directory("Notes/")                        # → list[str]

# Obsidian interaction
client.open_note("Notes/New.md", new_leaf=False)       # → bool
client.get_active_file()                               # → str | None

# Periodic notes (period validated: daily/weekly/monthly/quarterly/yearly)
client.get_periodic_note("daily")                      # → str | None
client.append_periodic_note("daily", "- captured item")# → bool

# Context manager ensures the HTTP session is closed
with ObsidianClient(config) as c:
    c.append_to_note("Notes.md", "Content")
```

#### Path validation

Every API path is validated to block traversal and Windows drive letters:

```python
from obsidian_clipper import validate_path
validate_path("../etc/passwd")   # raises PathSecurityError
```

### `Config`

```python
from obsidian_clipper.config import Config, get_config, set_config

config = get_config()                                   # global singleton
config = Config(api_key="...", base_url="http://127.0.0.1:27124")
errors = config.validate()                              # → list[str] (empty if valid)
set_config(config)                                      # replace the singleton
```

### Capture utilities

```python
from obsidian_clipper import (
    get_selected_text, get_active_window_title, copy_to_clipboard,
    take_screenshot, ocr_image, ScreenshotCapture, create_temp_screenshot,
)

text = get_selected_text()                  # primary selection
text = get_selected_text("clipboard")       # clipboard
title = get_active_window_title()           # focused window title
copy_to_clipboard("hello", clipboard="primary")

# Screenshots
take_screenshot("/tmp/shot.png", tool="auto")
ocr_image("/tmp/shot.png", language="eng")  # → str

with ScreenshotCapture(perform_ocr=True) as cap:
    path, ocr_text = cap.capture()
```

### `Citation`

```python
from obsidian_clipper import get_citation, Citation, SourceType

citation = get_citation()                   # auto-detect from active window
if citation:
    citation.title           # "Book.pdf"
    citation.page            # "42"
    citation.source          # "Evince"
    citation.source_type     # SourceType.PDF
    citation.format_markdown()  # " — *Book.pdf, p. 42* · Evince"
    citation.get_auto_tags()    # ["pdf", "research"]
```

Individual parsers are also available: `parse_pdf_citation`,
`parse_epub_citation`, `parse_browser_citation`, `parse_jetbrains_citation`,
`parse_code_editor_citation`, `parse_sublime_citation`, `parse_zotero_citation`,
`parse_libreoffice_citation`, `parse_texstudio_citation`, and
`parse_generic_citation`.

### `CaptureSession`

Holds a capture and renders markdown:

```python
from obsidian_clipper.workflow.session import CaptureSession
from obsidian_clipper import Citation, SourceType

session = CaptureSession(
    text="Captured text",
    citation=Citation(title="Book.pdf", page="42", source="Evince", source_type=SourceType.PDF),
    tags=["research"],
)
print(session.to_markdown())

# Templates resolve @file / named / inline and support {{#if}} {{#unless}} {{#each}}
session.template = "{{#if citation}}>{{citation}}\n{{/if}}{{text}}"
print(session.to_markdown())
```

### Exceptions

All errors derive from `ClipperError`:

| Exception | Raised when |
|-----------|-------------|
| `ConfigurationError` | Config is invalid/missing |
| `APIConnectionError` | Can't reach the Local REST API |
| `APIRequestError` | An API request failed |
| `CaptureError` | Content capture failed |
| `ScreenshotError` | Screenshot capture failed |
| `OCRError` | OCR processing failed |
| `PathSecurityError` | A path failed security validation |

```python
from obsidian_clipper import ClipperError, ConfigurationError, APIConnectionError

try:
    ...
except ConfigurationError as e:
    print(e.message, e.context)
```

---

*Obsidian Clipper is MIT-licensed. See [LICENSE](../LICENSE) and the
[README](../README.md).*
