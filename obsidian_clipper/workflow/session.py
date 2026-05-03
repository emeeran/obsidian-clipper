"""Capture session data structure."""

from __future__ import annotations

import datetime
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
            Note path like "00-Inbox/Capture.md"
        """
        preview = self.get_preview(40)
        safe_preview = re.sub(r'[<>:"/\\|?*\n\r]', "", preview)
        safe_preview = re.sub(r"\s+", " ", safe_preview).strip()

        filename = f"{safe_preview}.md"

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

    def _render_template(self) -> str:
        """Render template with placeholders and conditionals.

        Supported placeholders: {{text}}, {{ocr}}, {{citation}}, {{timestamp}},
        {{tags}}, {{source}}, {{source_type}}, {{date}}, {{time}}.

        Supported conditionals: {{#if field}}...{{/if}} — content is included
        only when the field is truthy. Nested placeholders inside conditionals
        are also expanded.
        """
        content = self.template or ""

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

        # Process conditionals: {{#if field}}...{{/if}}
        def _eval_conditional(match: re.Match) -> str:
            field = match.group(1).strip()
            body = match.group(2)
            value = subs.get(field, "")
            if value:
                return body
            return ""

        content = re.sub(r"\{\{#if\s+(\w+)\}\}(.*?)\{\{/if\}\}", _eval_conditional, content, flags=re.DOTALL)

        # Replace all placeholders
        for key, value in subs.items():
            content = content.replace("{{" + key + "}}", value)

        return content

    def _render_frontmatter(self, tags: list[str]) -> str:
        """Render YAML frontmatter with tags."""
        if not tags:
            return ""
        parts = ["---\n", "tags:\n"]
        for tag in tags:
            tag = tag.strip()
            if tag:
                parts.append(f"  - {tag.lstrip('#')}\n")
        parts.append("---\n\n")
        return "".join(parts)

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

    def _render_text_callout(self) -> str:
        """Render text capture as Obsidian callout."""
        body = self.text.split("\n") if self.text else []
        return self._render_callout("quote", body)

    def _render_screenshot_callout(self) -> str:
        """Render screenshot capture as Obsidian callout."""
        body = []
        if self.screenshot_success and self.img_filename:
            body.append(f"![[{self.img_filename}]]")
        # Include text alongside screenshot when both exist
        if self.text:
            if body:
                body.append("")
            body.extend(self.text.split("\n"))
        return self._render_callout("image", body)

    def to_markdown(self, include_frontmatter: bool = True) -> str:
        """Convert captured content to markdown string.

        Args:
            include_frontmatter: If True, include YAML frontmatter (for new notes).
                False for append mode to avoid repeated frontmatter.
        """
        # Merge user tags with auto-generated tags from citation source
        all_tags = list(self.tags)
        if self.citation:
            for tag in self.citation.get_auto_tags():
                if tag not in all_tags:
                    all_tags.append(tag)

        parts: list[str] = []

        # Frontmatter only for new notes, not appends
        if include_frontmatter:
            parts.append(self._render_frontmatter(all_tags))

        # Date header (just date, no seconds)
        date, time = self.timestamp.split(" ") if " " in self.timestamp else (self.timestamp, "")
        parts.append(f"### {date}\n\n")

        if self.template:
            parts.append(self._render_template())
            parts.append("\n")
        elif self.screenshot_success and self.img_filename:
            parts.append(self._render_screenshot_callout())
        else:
            parts.append(self._render_text_callout())

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
