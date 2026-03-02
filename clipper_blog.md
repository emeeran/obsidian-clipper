# Obsidian Clipper: Fast Desktop Capture with Auto-Citations

If you use Obsidian for note-taking, you know the friction of capturing content from elsewhere on your desktop. Copy, switch windows, paste, format—it adds up. I wanted something faster: highlight text, hit a hotkey, done. Here's how I built it.

## The Goal

A capture system that:
- Grabs any highlighted text instantly
- Auto-detects citations from PDF readers and browsers
- Screenshots with OCR for image text extraction
- Works with Obsidian's Local REST API
- Integrates with Linux desktop shortcuts

## The Solution

A modular Python tool that leverages the [Local REST API plugin](https://github.com/czottmann/obsidian-local-rest-api) for Obsidian. The plugin exposes a REST API that lets you read, create, and modify notes programmatically.

### Key Features

**Text Selection**: Uses `xclip` (X11) or `wl-paste` (Wayland) to read the primary selection—text you've highlighted but haven't copied:

```python
def get_selected_text() -> str:
    # Try xclip first (X11 primary selection)
    try:
        result = subprocess.run(
            ["xclip", "-o", "-selection", "primary"],
            capture_output=True, text=True, check=True, timeout=5,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Fallback to wl-paste (Wayland)
    try:
        result = subprocess.run(
            ["wl-paste", "-p"],
            capture_output=True, text=True, check=True, timeout=5,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return ""
```

**Auto-Citations**: Detects the source window and extracts metadata. For PDFs, it parses page numbers from common readers:

```python
def parse_pdf_citation(window_title: str) -> Citation | None:
    # Evince: "Document.pdf — Page 42"
    evince_match = re.match(
        r"(.+\.pdf)\s*[—\-–]\s*Page\s*(\d+)", window_title, re.IGNORECASE
    )
    if evince_match:
        return Citation(
            title=evince_match.group(1).strip(),
            page=evince_match.group(2),
            source="Evince",
        )

    # Zathura: "Document.pdf (42/100)"
    zathura_match = re.match(r"(.+\.pdf)\s*\((\d+)/\d+\)", window_title)
    if zathura_match:
        return Citation(
            title=zathura_match.group(1).strip(),
            page=zathura_match.group(2),
            source="Zathura",
        )
    # ... supports Okular, generic PDF patterns too
```

**Screenshots + OCR**: Integrates Flameshot or grim/slurp with Tesseract for text extraction:

```python
def ocr_image(img_path: Path, language: str = "eng") -> str:
    result = subprocess.run(
        ["tesseract", str(img_path), "stdout", "-l", language],
        capture_output=True, timeout=30, check=True,
    )
    return result.stdout.strip()
```

**REST API Client**: Connection pooling with retry logic for reliability:

```python
class ObsidianClient:
    def _get_session(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=3, backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        return session

    def append_to_note(self, note_path: str, content: str) -> bool:
        response = self._request("POST", note_path,
            headers={"Content-Type": "text/markdown"},
            data=content.encode("utf-8"))
        return response.status_code in (200, 201, 204)
```

## Setting Up Keyboard Shortcuts

On GNOME, register global hotkeys via `gsettings`:

```bash
# Text capture: Ctrl+Alt+C
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/ name 'Obsidian Clipper Text'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/ command 'obsidian-clipper'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/ binding '<Primary><Alt>c'

# Screenshot + OCR: Ctrl+Alt+S
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom1/ name 'Obsidian Clipper Screenshot'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom1/ command 'obsidian-clipper -s'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom1/ binding '<Primary><Alt>s'
```

## The Result

Highlight any text, press `Ctrl+Alt+C`, and it appears in your vault with an auto-detected citation:

```markdown
---

**2026-02-26 14:32:10**

> The best capture system is the one you actually use.

 — *Research_Paper.pdf, p. 42* · Evince
```

With the `-s` flag, you get a screenshot plus OCR'd text embedded in the note.

## Requirements

- **Obsidian** with Local REST API plugin enabled
- **Python 3** + `requests` library
- **X11**: `xclip`, `flameshot`, `xdotool`, `tesseract-ocr`, `libnotify-bin`
- **Wayland**: `wl-clipboard`, `grim`, `slurp`, `tesseract-ocr`

```bash
# Ubuntu/Debian (X11)
sudo apt install xclip flameshot tesseract-ocr libnotify-bin xdotool
pip install requests
```

## Why This Matters

The best capture system is the one you actually use. By reducing friction to a single hotkey—and automatically adding citations—I find myself capturing more: interesting quotes from PDFs, code snippets, web articles. Everything flows into a single inbox note for later processing.

The full source code and documentation are available on GitHub.

Happy capturing!
