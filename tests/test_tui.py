"""Tests for the TUI configuration module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from obsidian_clipper.cli.tui import ConfigTUI, launch_config_ui


class TestConfigTUILoad:
    """Tests for ConfigTUI config loading."""

    def test_load_config_reads_env_file(self, tmp_path: Path):
        """Test loading a valid .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "OBSIDIAN_API_KEY=testkey123\n"
            "OBSIDIAN_BASE_URL=http://localhost:27124\n"
            "OBSIDIAN_DEFAULT_NOTE=Inbox/\n"
            "OBSIDIAN_ATTACHMENT_DIR=Attachments/\n"
        )
        app = ConfigTUI(env_file)
        assert app.config_data["OBSIDIAN_API_KEY"] == "testkey123"
        assert app.config_data["OBSIDIAN_BASE_URL"] == "http://localhost:27124"

    def test_load_config_missing_file(self, tmp_path: Path):
        """Test loading when .env file doesn't exist."""
        env_file = tmp_path / "nonexistent.env"
        app = ConfigTUI(env_file)
        assert app.config_data["OBSIDIAN_API_KEY"] == ""
        assert "OBSIDIAN_BASE_URL" in app.config_data

    def test_load_config_skips_comments(self, tmp_path: Path):
        """Test that comment lines are skipped."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "# This is a comment\n"
            "OBSIDIAN_API_KEY=key123\n"
            "# Another comment\n"
        )
        app = ConfigTUI(env_file)
        assert app.config_data["OBSIDIAN_API_KEY"] == "key123"
        assert len([k for k in app.config_data if k.startswith("#")]) == 0

    def test_load_config_skips_blank_lines(self, tmp_path: Path):
        """Test that blank lines are skipped."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "\n\nOBSIDIAN_API_KEY=key123\n\n"
        )
        app = ConfigTUI(env_file)
        assert app.config_data["OBSIDIAN_API_KEY"] == "key123"

    def test_load_config_handles_equals_in_value(self, tmp_path: Path):
        """Test values containing '=' are parsed correctly."""
        env_file = tmp_path / ".env"
        env_file.write_text("OBSIDIAN_API_KEY=abc=def=ghi\n")
        app = ConfigTUI(env_file)
        assert app.config_data["OBSIDIAN_API_KEY"] == "abc=def=ghi"


class TestConfigTUISave:
    """Tests for ConfigTUI save action."""

    def test_save_writes_env_file(self, tmp_path: Path):
        """Test that saving writes all config keys to .env."""
        env_file = tmp_path / ".env"
        env_file.write_text("OBSIDIAN_API_KEY=oldkey\n")

        app = ConfigTUI(env_file)
        # Mock the Textual query_one and exit
        mock_api_key = MagicMock()
        mock_api_key.value = "newkey123"
        mock_base_url = MagicMock()
        mock_base_url.value = "http://localhost:9999"
        mock_note_path = MagicMock()
        mock_note_path.value = "Inbox/"
        mock_attach_dir = MagicMock()
        mock_attach_dir.value = "Files/"

        def mock_query(selector, widget_type=None):
            mapping = {
                "#api_key": mock_api_key,
                "#base_url": mock_base_url,
                "#note_path": mock_note_path,
                "#attachment_dir": mock_attach_dir,
            }
            return mapping[selector]

        app.query_one = mock_query
        app.exit = MagicMock()
        app.notify = MagicMock()

        app.action_save()

        content = env_file.read_text()
        assert "OBSIDIAN_API_KEY=newkey123" in content
        assert "OBSIDIAN_BASE_URL=http://localhost:9999" in content
        assert "OBSIDIAN_DEFAULT_NOTE=Inbox/" in content
        assert "OBSIDIAN_ATTACHMENT_DIR=Files/" in content

    def test_save_creates_parent_directory(self, tmp_path: Path):
        """Test that save creates missing parent directories."""
        env_file = tmp_path / "subdir" / "config" / ".env"
        # Don't create the parent dirs

        app = ConfigTUI(env_file)
        mock_api_key = MagicMock()
        mock_api_key.value = ""
        mock_base_url = MagicMock()
        mock_base_url.value = "http://127.0.0.1:27124"
        mock_note_path = MagicMock()
        mock_note_path.value = ""
        mock_attach_dir = MagicMock()
        mock_attach_dir.value = ""

        def mock_query(selector, widget_type=None):
            mapping = {
                "#api_key": mock_api_key,
                "#base_url": mock_base_url,
                "#note_path": mock_note_path,
                "#attachment_dir": mock_attach_dir,
            }
            return mapping[selector]

        app.query_one = mock_query
        app.exit = MagicMock()
        app.notify = MagicMock()

        app.action_save()
        assert env_file.exists()


class TestLaunchConfigUI:
    """Tests for launch_config_ui function."""

    @patch("obsidian_clipper.cli.tui.ConfigTUI")
    def test_launch_creates_correct_path(self, mock_tui_cls):
        """Test that launch_config_ui uses ~/.config/obsidian-clipper/.env."""
        launch_config_ui()
        args, _ = mock_tui_cls.call_args
        env_path = args[0]
        assert env_path == Path.home() / ".config" / "obsidian-clipper" / ".env"

    @patch("obsidian_clipper.cli.tui.ConfigTUI")
    def test_launch_calls_run(self, mock_tui_cls):
        """Test that launch_config_ui calls app.run()."""
        launch_config_ui()
        mock_tui_cls.return_value.run.assert_called_once()
