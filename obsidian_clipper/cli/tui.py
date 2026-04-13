"""TUI for configuration management."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Button, Footer, Header, Input, Label, Static


class ConfigTUI(App[None]):
    """A TUI for editing .env configuration."""

    CSS = """
    Container {
        padding: 1;
        width: 100%;
        height: auto;
    }

    Horizontal {
        height: auto;
        margin-bottom: 1;
    }

    Label {
        width: 25;
        content-align: right middle;
        margin-right: 2;
    }

    Input {
        width: 1fr;
    }

    #buttons {
        margin-top: 2;
        content-align: center middle;
    }

    Button {
        margin: 0 1;
    }
    """

    TITLE = "Obsidian Clipper Configuration"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+s", "save", "Save"),
    ]

    def __init__(self, env_path: Path):
        super().__init__()
        self.env_path = env_path
        self.config_data: dict[str, str] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load config from .env file."""
        if not self.env_path.exists():
            # Default values
            self.config_data = {
                "OBSIDIAN_API_KEY": "",
                "OBSIDIAN_BASE_URL": "http://127.0.0.1:27124",
                "OBSIDIAN_DEFAULT_NOTE": "00-Inbox/",
                "OBSIDIAN_ATTACHMENT_DIR": "Attachments/",
            }
            return

        with open(self.env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    self.config_data[key.strip()] = value.strip()

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Container(
            Static("Edit your Obsidian Clipper configuration below:"),
            Horizontal(
                Label("API Key:"),
                Input(
                    value=self.config_data.get("OBSIDIAN_API_KEY", ""),
                    placeholder="Enter your Local REST API key",
                    id="api_key",
                    password=True,
                ),
            ),
            Horizontal(
                Label("Base URL:"),
                Input(
                    value=self.config_data.get(
                        "OBSIDIAN_BASE_URL", "http://127.0.0.1:27124"
                    ),
                    placeholder="http://127.0.0.1:27124",
                    id="base_url",
                ),
            ),
            Horizontal(
                Label("Default Note Path:"),
                Input(
                    value=self.config_data.get("DEFAULT_NOTE_PATH", "00-Inbox/"),
                    placeholder="e.g. 00-Inbox/ or Daily/{{date}}.md",
                    id="note_path",
                ),
            ),
            Horizontal(
                Label("Attachment Dir:"),
                Input(
                    value=self.config_data.get("ATTACHMENT_DIR", "Attachments/"),
                    placeholder="e.g. Attachments/",
                    id="attachment_dir",
                ),
            ),
            Horizontal(
                Button("Save", variant="primary", id="save"),
                Button("Cancel", variant="error", id="cancel"),
                id="buttons",
            ),
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save":
            self.action_save()
        elif event.button.id == "cancel":
            self.exit()

    def action_save(self) -> None:
        """Save the configuration to .env file."""
        api_key = self.query_one("#api_key", Input).value
        base_url = self.query_one("#base_url", Input).value
        note_path = self.query_one("#note_path", Input).value
        attachment_dir = self.query_one("#attachment_dir", Input).value

        new_config = {
            "OBSIDIAN_API_KEY": api_key,
            "OBSIDIAN_BASE_URL": base_url,
            "OBSIDIAN_DEFAULT_NOTE": note_path,
            "OBSIDIAN_ATTACHMENT_DIR": attachment_dir,
        }

        # Ensure directory exists
        self.env_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.env_path, "w") as f:
            for key, value in new_config.items():
                f.write(f"{key}={value}\n")

        self.notify("Configuration saved successfully!")
        self.exit()


def launch_config_ui() -> None:
    """Launch the configuration TUI."""
    config_dir = Path.home() / ".config" / "obsidian-clipper"
    env_path = config_dir / ".env"
    app = ConfigTUI(env_path)
    app.run()
