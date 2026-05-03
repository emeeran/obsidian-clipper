"""Capture session data structure."""

from __future__ import annotations

import datetime
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..capture import Citation


@dataclass
class CaptureSession:
    """Represents a capture session with all captured content.

    Attributes:
        timestamp: Timestamp string for the capture.
        text: Captured text from selection.
        screenshot_path: Path to screenshot file if captured.
        ocr_text: OCR text extracted from screenshot.
        citation: Citation information if captured.
        screenshot_success: Whether screenshot was successfully uploaded.
    """

    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    text: str = ""
    screenshot_path: Path | None = None
    ocr_text: str = ""
    citation: Citation | None = None
    screenshot_success: bool = False
    img_filename: str | None = None
    tags: list[str] = field(default_factory=list)
    template: str | None = None

    def get_note_filename(self, directory: str = "") -> str:
        """Generate a filename for the note.

        Args:
            directory: Target directory (e.g., "00-Inbox/").

        Returns:
            Note path like "00-Inbox/Capture_abc123.md"
        """
        preview = self.get_preview(40)
        safe_preview = re.sub(r'[<>:"/\\|?*\n\r]', "", preview)
        safe_preview = re.sub(r"\s+", " ", safe_preview).strip()

        # Add short hash to prevent collisions
        content_hash = hashlib.md5(
            (self.text or self.ocr_text or self.timestamp).encode()
        ).hexdigest()[:6]
        filename = f"{safe_preview}_{content_hash}.md"

        if directory:
            directory = directory.rstrip("/") + "/"
            return f"{directory}{filename}"
        return filename

    def has_content(self) -> bool:
        """Check if any content was captured."""
        return bool(
            self.text
            or self.screenshot_path
            or self.screenshot_success
            or self.ocr_text
        )

    def _resolve_template(self) -> str:
        """Resolve template from file path or named template.

        Resolution order:
        1. If template starts with '@': read file at path after '@'
        2. If template has no '{{' and exists in config templates dir: load it
        3. Otherwise: use template as-is (inline string)
        """
        raw = self.template or ""
        if not raw:
            return ""

        # '@' prefix: load from file path
        if raw.startswith("@"):
            path = Path(raw[1:].strip())
            try:
                return path.read_text(encoding="utf-8")
            except OSError as e:
                import logging
                logging.getLogger(__name__).warning("Template file not found: %s", e)
                return ""

        # Named template: check config templates dir
        if "{{" not in raw:
            config_dir = Path.home() / ".config" / "obsidian-clipper" / "templates"
            named_path = config_dir / f"{raw}.md"
            if named_path.exists():
                try:
                    return named_path.read_text(encoding="utf-8")
                except OSError:
                    pass

        return raw

    def _render_template(self) -> str:
        """Render template with placeholders and conditionals.

        Supported placeholders: {{text}}, {{ocr}}, {{citation}}, {{timestamp}},
        {{tags}}, {{source}}, {{source_type}}, {{date}}, {{time}}.

        Supported conditionals:
        - {{#if field}}...{{/if}} — content when field is truthy
        - {{#unless field}}...{{/unless}} — content when field is falsy
        - {{#each tags}}..{{this}}..{{/each}} — iterate over tag list
        """
        content = self._resolve_template()
        if not content:
            return ""

        # Build substitution map
        ts_parts = self.timestamp.split(" ")
        subs: dict[str, str] = {
            "text": self.text or "",
            "ocr": self.ocr_text or "",
            "citation": self.citation.format_markdown() if self.citation else "",
            "timestamp": self.timestamp,
            "tags": ", ".join(self.tags) if self.tags else "",
            "source": (self.citation.source if self.citation and self.citation.source else ""),
            "source_type": (self.citation.source_type.value if self.citation else ""),
            "date": ts_parts[0] if ts_parts else "",
            "time": ts_parts[1] if len(ts_parts) > 1 else "",
        }

        # Process {{#each field}}...{{this}}...{{/each}} loops
        def _eval_each(match: re.Match[str]) -> str:
            field = match.group(1).strip()
            body = match.group(2)
            items: list[str]
            if field == "tags":
                items = self.tags
            else:
                return ""
            return "".join(body.replace("{{this}}", item) for item in items)

        content = re.sub(r"\{\{#each\s+(\w+)\}\}(.*?)\{\{/each\}\}", _eval_each, content, flags=re.DOTALL)

        # Process {{#if field}}...{{/if}}
        def _eval_if(match: re.Match[str]) -> str:
            field = match.group(1).strip()
            body = match.group(2)
            value = subs.get(field, "")
            return body if value else ""

        content = re.sub(r"\{\{#if\s+(\w+)\}\}(.*?)\{\{/if\}\}", _eval_if, content, flags=re.DOTALL)

        # Process {{#unless field}}...{{/unless}}
        def _eval_unless(match: re.Match[str]) -> str:
            field = match.group(1).strip()
            body = match.group(2)
            value = subs.get(field, "")
            return body if not value else ""

        content = re.sub(r"\{\{#unless\s+(\w+)\}\}(.*?)\{\{/unless\}\}", _eval_unless, content, flags=re.DOTALL)

        # Replace all placeholders
        for key, value in subs.items():
            content = content.replace("{{" + key + "}}", value)

        return content

    def _render_frontmatter(self, tags: list[str]) -> str:
        if not tags:
            return ""
        tag_lines = "\n".join(f"  - {t.strip().lstrip('#')}" for t in tags if t.strip())
        return f"---\ntags:\n{tag_lines}\n---\n\n"

    def _render_source_label(self) -> str:
        """Render source label for callout title."""
        if not self.citation:
            return ""
        title = self.citation.title or ""
        source = self.citation.source or ""
        page = self.citation.page
        # These are internal labels, not meaningful to the user
        if source in ("PDF Reader", "Browser", "Unknown", "Window"):
            source = ""
        parts = []
        if title:
            display = title
            if page:
                display += f", p.{page}"
            parts.append(display)
        if source:
            parts.append(source)
        return " — " + " · ".join(parts) if parts else ""

    def _render_callout(self, callout_type: str, body_lines: list[str]) -> str:
        """Render an Obsidian callout block.

        Args:
            callout_type: Callout type (e.g., "quote", "image").
            body_lines: Lines to render inside the callout body.
        """
        source_label = self._render_source_label()
        lines = [f"> [!{callout_type}]{source_label}", ">"]
        for body_line in body_lines:
            lines.append(f"> {body_line}")
        if body_lines:
            lines.append(">")
        if self.ocr_text:
            for line in self.ocr_text.split("\n"):
                lines.append(f"> {line}")
            lines.append(">")
        return "\n".join(lines) + "\n"

    def to_markdown(self, include_frontmatter: bool = True) -> str:
        """Convert captured content to markdown string."""
        all_tags = list(self.tags)
        if self.citation:
            for tag in self.citation.get_auto_tags():
                if tag not in all_tags:
                    all_tags.append(tag)

        parts: list[str] = []

        if include_frontmatter:
            parts.append(self._render_frontmatter(all_tags))

        date = self.timestamp.split(" ")[0] if " " in self.timestamp else self.timestamp
        parts.append(f"### {date}\n\n")

        rendered_template = self._render_template() if self.template else ""
        if rendered_template:
            parts.append(rendered_template)
            parts.append("\n")
        elif self.screenshot_success and self.img_filename:
            body = [f"![[{self.img_filename}]]"]
            if self.text:
                body.append("")
                body.extend(self.text.split("\n"))
            parts.append(self._render_callout("image", body))
        else:
            body = self.text.split("\n") if self.text else []
            parts.append(self._render_callout("quote", body))

        return "".join(parts)

    def get_preview(self, max_length: int = 50) -> str:
        """Get a short preview of captured content."""
        if self.text:
            preview = self.text[:max_length]
            return preview + "..." if len(self.text) > max_length else preview
        if self.ocr_text:
            preview = self.ocr_text[:max_length]
            return preview + "..." if len(self.ocr_text) > max_length else preview
        return "Screenshot"
