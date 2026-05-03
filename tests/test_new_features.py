"""Tests for new features: profiles, vault, dry-run, append, template conditionals, etc."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from obsidian_clipper.capture import Citation, SourceType
from obsidian_clipper.cli.args import parse_args
from obsidian_clipper.config import PROFILES, Config, get_profile, get_vault_config
from obsidian_clipper.workflow.session import CaptureSession


class TestProfiles:
    """Tests for capture profiles."""

    def test_get_builtin_profile(self):
        profile = get_profile("research")
        assert profile["tags"] == "research,reading"
        assert profile["note"] == "00-Inbox/Research Note.md"
        assert profile["ocr"] is True
        assert profile["append"] is True

    def test_get_quick_profile(self):
        profile = get_profile("quick")
        assert profile["ocr"] is False

    def test_unknown_profile_raises(self):
        with pytest.raises(ValueError, match="Unknown profile"):
            get_profile("nonexistent")

    def test_all_profiles_have_required_keys(self):
        for name, profile in PROFILES.items():
            assert "tags" in profile, f"Profile '{name}' missing 'tags'"
            assert "note" in profile, f"Profile '{name}' missing 'note'"

    def test_profile_env_override(self):
        with patch.dict(os.environ, {"OBSIDIAN_PROFILE_RESEARCH_TAGS": "custom,tags"}):
            profile = get_profile("research")
            assert profile["tags"] == "custom,tags"


class TestUserProfiles:
    """Tests for user-defined profiles via TOML."""

    def test_load_user_profiles_from_toml(self, tmp_path):
        """Test loading user profiles from profiles.toml."""
        from obsidian_clipper.config import _load_user_profiles

        config_dir = tmp_path / ".config" / "obsidian-clipper"
        config_dir.mkdir(parents=True)
        (config_dir / "profiles.toml").write_text(
            '[profiles.academic]\ntags = "academic,paper"\nnote = "Academic/"\nocr = true\n'
        )

        with patch.object(Path, "home", return_value=tmp_path):
            profiles = _load_user_profiles()

        assert "academic" in profiles
        assert profiles["academic"]["tags"] == "academic,paper"
        assert profiles["academic"]["ocr"] is True

    def test_user_profiles_merge_with_builtins(self, tmp_path):
        """Test user profiles are accessible via get_profile."""
        config_dir = tmp_path / ".config" / "obsidian-clipper"
        config_dir.mkdir(parents=True)
        (config_dir / "profiles.toml").write_text(
            '[profiles.meeting]\ntags = "meeting"\nnote = "Meetings/"\n'
        )

        with patch.object(Path, "home", return_value=tmp_path):
            profile = get_profile("meeting")

        assert profile["tags"] == "meeting"
        assert profile["note"] == "Meetings/"

    def test_missing_toml_file_returns_empty(self, tmp_path):
        """Test graceful handling when profiles.toml doesn't exist."""
        from obsidian_clipper.config import _load_user_profiles

        with patch.object(Path, "home", return_value=tmp_path):
            profiles = _load_user_profiles()
        assert profiles == {}

    def test_invalid_toml_returns_empty(self, tmp_path):
        """Test graceful handling of malformed TOML."""
        from obsidian_clipper.config import _load_user_profiles

        config_dir = tmp_path / ".config" / "obsidian-clipper"
        config_dir.mkdir(parents=True)
        (config_dir / "profiles.toml").write_text("this is not valid toml [[[[")

        with patch.object(Path, "home", return_value=tmp_path):
            profiles = _load_user_profiles()
        assert profiles == {}


class TestVaultConfig:
    """Tests for multi-vault support."""

    def test_vault_config_reads_env_vars(self):
        with patch.dict(
            os.environ,
            {
                "OBSIDIAN_WORK_API_KEY": "vault-api-key-1234567890",
                "OBSIDIAN_WORK_BASE_URL": "http://work-vault:27124",
            },
        ):
            config = get_vault_config("work")
            assert config.api_key == "vault-api-key-1234567890"
            assert config.base_url == "http://work-vault:27124"

    def test_vault_config_falls_back_to_defaults(self):
        with patch.dict(os.environ, {}, clear=False):
            # Remove any vault-specific vars
            for key in list(os.environ):
                if key.startswith("OBSIDIAN_WORK_"):
                    del os.environ[key]
            config = get_vault_config("work")
            # Should fall back to default base_url (may have trailing /)
            assert "127.0.0.1:27124" in config.base_url

    def test_vault_config_restores_env(self):
        """Verify vault config loading doesn't pollute the environment."""
        original_key = os.environ.get("OBSIDIAN_API_KEY")
        with patch.dict(
            os.environ,
            {"OBSIDIAN_PERSONAL_API_KEY": "personal-key-1234567890"},
        ):
            config = get_vault_config("personal")
            assert config.api_key == "personal-key-1234567890"
        # Original env should be restored
        assert os.environ.get("OBSIDIAN_API_KEY") == original_key


class TestTemplateIfConditionals:
    """Tests for {{#if field}} conditionals."""

    def test_conditional_included_when_truthy(self):
        session = CaptureSession(
            text="Hello",
            citation=Citation(title="Test", source="Browser", source_type=SourceType.BROWSER),
        )
        session.template = "{{#if citation}}Source: {{source}}{{/if}}"
        md = session.to_markdown()
        assert "Source: Browser" in md

    def test_conditional_excluded_when_falsy(self):
        session = CaptureSession(text="Hello")
        session.template = "{{#if citation}}Source: {{source}}{{/if}}"
        md = session.to_markdown()
        assert "Source:" not in md

    def test_multiple_conditionals(self):
        session = CaptureSession(text="Hello", tags=["web"])
        session.template = "{{#if text}}Text: {{text}}{{/if}}\n{{#if tags}}Tags: {{tags}}{{/if}}"
        md = session.to_markdown()
        assert "Text: Hello" in md
        assert "Tags: web" in md

    def test_conditional_with_empty_tags_excluded(self):
        session = CaptureSession(text="Hello")
        session.template = "{{#if tags}}Tags: {{tags}}{{/if}}"
        md = session.to_markdown()
        assert "Tags:" not in md


class TestTemplatePlaceholders:
    """Tests for expanded template placeholders."""

    def test_tags_placeholder(self):
        session = CaptureSession(text="Hello", tags=["web", "article"])
        session.template = "Tags: {{tags}}"
        md = session.to_markdown()
        assert "Tags: web, article" in md

    def test_source_placeholder(self):
        session = CaptureSession(
            text="Hello",
            citation=Citation(title="Test", source="Chrome", source_type=SourceType.BROWSER),
        )
        session.template = "From: {{source}}"
        md = session.to_markdown()
        assert "From: Chrome" in md

    def test_source_type_placeholder(self):
        session = CaptureSession(
            text="Hello",
            citation=Citation(title="Test", source_type=SourceType.PDF),
        )
        session.template = "Type: {{source_type}}"
        md = session.to_markdown()
        assert "Type: pdf" in md

    def test_date_time_placeholders(self):
        session = CaptureSession(
            timestamp="2024-01-15 10:30:00",
            text="Hello",
        )
        session.template = "Date: {{date}}, Time: {{time}}"
        md = session.to_markdown()
        assert "Date: 2024-01-15" in md
        assert "Time: 10:30:00" in md

    def test_timestamp_placeholder(self):
        session = CaptureSession(timestamp="2024-01-15 10:30:00", text="Hello")
        session.template = "At: {{timestamp}}"
        md = session.to_markdown()
        assert "At: 2024-01-15 10:30:00" in md


class TestTemplateConditionals:
    """Tests for {{#unless}} and {{#each}} template features."""

    def test_unless_shows_content_when_empty(self):
        """{{#unless}} renders body when field is empty."""
        session = CaptureSession(text="Hello")
        session.template = "{{#unless citation}}No source{{/unless}}"
        md = session.to_markdown()
        assert "No source" in md

    def test_unless_hides_content_when_present(self):
        """{{#unless}} hides body when field has value."""
        session = CaptureSession(
            text="Hello",
            citation=Citation(title="Test", source_type=SourceType.BROWSER),
        )
        session.template = "{{#unless text}}No text{{/unless}}"
        md = session.to_markdown()
        assert "No text" not in md

    def test_each_tags(self):
        """{{#each tags}} iterates over tags."""
        session = CaptureSession(text="Hello", tags=["research", "paper"])
        session.template = "{{#each tags}}#{{this}} {{/each}}"
        md = session.to_markdown()
        assert "#research" in md
        assert "#paper" in md

    def test_each_tags_empty(self):
        """{{#each tags}} renders nothing when no tags."""
        session = CaptureSession(text="Hello")
        session.template = "Tags: {{#each tags}}#{{this}} {{/each}}"
        md = session.to_markdown()
        assert "Tags: " in md
        # The {{#each}} block should render nothing — no tag names after #
        assert "#research" not in md
        assert "#paper" not in md

    def test_if_and_unless_combined(self):
        """Test using both {{#if}} and {{#unless}} in same template."""
        session = CaptureSession(text="Hello")
        session.template = "{{#if text}}Has text{{/if}} {{#unless ocr}}No OCR{{/unless}}"
        md = session.to_markdown()
        assert "Has text" in md
        assert "No OCR" in md


class TestExternalTemplateFiles:
    """Tests for file-based template resolution."""

    def test_template_from_file_with_at_prefix(self, tmp_path):
        """Test '@path' loads template from file."""
        template_file = tmp_path / "my_template.md"
        template_file.write_text("Custom: {{text}}")

        session = CaptureSession(text="Hello")
        session.template = f"@{template_file}"
        md = session.to_markdown()
        assert "Custom: Hello" in md

    def test_template_from_missing_file_returns_empty(self, tmp_path):
        """Test '@' with missing file gracefully returns empty."""
        session = CaptureSession(text="Hello")
        session.template = f"@{tmp_path / 'nonexistent.md'}"
        md = session.to_markdown()
        # Falls through to default callout rendering since template resolves to empty
        assert "> [!quote]" in md

    def test_template_from_named_file(self, tmp_path):
        """Test named template loads from config dir."""
        templates_dir = tmp_path / ".config" / "obsidian-clipper" / "templates"
        templates_dir.mkdir(parents=True)
        (templates_dir / "research.md").write_text("Research: {{text}}")

        session = CaptureSession(text="Paper notes")
        session.template = "research"

        with patch("obsidian_clipper.workflow.session.Path.home", return_value=tmp_path):
            md = session.to_markdown()
        assert "Research: Paper notes" in md

    def test_inline_template_unchanged(self):
        """Test inline templates with {{ still work as before."""
        session = CaptureSession(text="Hello")
        session.template = "Text: {{text}}"
        md = session.to_markdown()
        assert "Text: Hello" in md

    def test_named_template_falls_back_to_inline(self, tmp_path):
        """Test non-matching named template is used as-is."""
        session = CaptureSession(text="Hello")
        session.template = "just-a-string"
        # No {{ in template, no file in config dir — used as literal
        md = session.to_markdown()
        assert "just-a-string" in md


class TestDryRunMode:
    """Tests for --dry-run CLI flag."""

    def test_dry_run_flag_parsed(self):
        with patch("sys.argv", ["clipper", "--dry-run"]):
            args = parse_args()
            assert args.dry_run is True

    def test_dry_run_default_false(self):
        with patch("sys.argv", ["clipper"]):
            args = parse_args()
            assert args.dry_run is False


class TestAppendMode:
    """Tests for --append CLI flag."""

    def test_append_flag_parsed(self):
        with patch("sys.argv", ["clipper", "--append", "-n", "Journal.md"]):
            args = parse_args()
            assert args.append is True

    def test_append_default_false(self):
        with patch("sys.argv", ["clipper"]):
            args = parse_args()
            assert args.append is False


class TestProfileFlag:
    """Tests for --profile CLI flag."""

    def test_profile_flag_parsed(self):
        with patch("sys.argv", ["clipper", "--profile", "research"]):
            args = parse_args()
            assert args.profile == "research"

    def test_profile_default_none(self):
        with patch("sys.argv", ["clipper"]):
            args = parse_args()
            assert args.profile is None


class TestVaultFlag:
    """Tests for --vault CLI flag."""

    def test_vault_flag_parsed(self):
        with patch("sys.argv", ["clipper", "--vault", "work"]):
            args = parse_args()
            assert args.vault == "work"

    def test_vault_default_none(self):
        with patch("sys.argv", ["clipper"]):
            args = parse_args()
            assert args.vault is None


class TestAnnotateFlag:
    """Tests for --annotate CLI flag."""

    def test_annotate_flag_parsed(self):
        with patch("sys.argv", ["clipper", "-s", "--annotate"]):
            args = parse_args()
            assert args.annotate is True

    def test_annotate_default_false(self):
        with patch("sys.argv", ["clipper"]):
            args = parse_args()
            assert args.annotate is False


class TestPickFlag:
    """Tests for --pick CLI flag."""

    def test_pick_flag_parsed(self):
        with patch("sys.argv", ["clipper", "--pick"]):
            args = parse_args()
            assert args.pick is True


class TestSessionRefactor:
    """Tests for the refactored session rendering methods."""

    def test_render_frontmatter_with_tags(self):
        session = CaptureSession(tags=["web", "article"])
        result = session._render_frontmatter(["web", "article"])
        assert "---" in result
        assert "  - web" in result
        assert "  - article" in result

    def test_render_frontmatter_empty(self):
        session = CaptureSession()
        assert session._render_frontmatter([]) == ""

    def test_render_source_label(self):
        session = CaptureSession(
            citation=Citation(title="Book", source="Chrome", source_type=SourceType.BROWSER),
        )
        result = session._render_source_label()
        assert "Book" in result
        assert "Chrome" in result

    def test_render_source_label_none(self):
        session = CaptureSession()
        assert session._render_source_label() == ""

    def test_to_markdown_text_callout(self):
        session = CaptureSession(text="Line 1\nLine 2")
        md = session.to_markdown(include_frontmatter=False)
        assert "> [!quote]" in md
        assert "> Line 1" in md
        assert "> Line 2" in md

    def test_to_markdown_text_callout_with_ocr(self):
        session = CaptureSession(text="Text", ocr_text="OCR")
        md = session.to_markdown(include_frontmatter=False)
        assert "> Text" in md
        assert "> OCR" in md

    def test_to_markdown_screenshot_callout(self):
        session = CaptureSession(screenshot_success=True, img_filename="img.png")
        md = session.to_markdown(include_frontmatter=False)
        assert "![[img.png]]" in md


class TestConfigValidation:
    """Tests for enhanced config validation."""

    def test_short_api_key_warns(self):
        config = Config.__new__(Config)
        config._loaded = False
        config.api_key = "short"
        config.base_url = "https://127.0.0.1:27124"
        config.default_note = "Notes.md"
        config.timeout = 10
        config.ocr_language = "eng"
        errors = config.validate()
        assert any("too short" in e for e in errors)

    def test_invalid_base_url_scheme(self):
        config = Config.__new__(Config)
        config._loaded = False
        config.api_key = "abcdef1234567890abcdef1234567890"
        config.base_url = "ftp://example.com"
        config.default_note = "Notes.md"
        config.timeout = 10
        config.ocr_language = "eng"
        errors = config.validate()
        assert any("http://" in e or "https://" in e for e in errors)

    def test_valid_config_no_errors(self):
        config = Config.__new__(Config)
        config._loaded = False
        config.api_key = "abcdef1234567890abcdef1234567890"
        config.base_url = "https://127.0.0.1:27124"
        config.default_note = "Notes.md"
        config.timeout = 10
        config.ocr_language = "eng"
        errors = config.validate()
        assert errors == []
