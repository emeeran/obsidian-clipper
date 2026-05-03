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
        # Get preview for filename
        preview = self.get_preview(40)
        # Sanitize for filename: remove/replace unsafe chars
        safe_preview = re.sub(r'[<>:"/\\|?*\n\r]', "", preview)
        safe_preview = re.sub(r"\s+", " ", safe_preview).strip()

        filename = f"{safe_preview}.md"

        if directory:
            # Ensure directory ends with /
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
            # Check if the field value is truthy
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

    def _render_blockquote(self) -> str:
        """Render text and OCR content as blockquote."""
        parts = []
        if self.text:
            parts.extend(f"> {line}\n" for line in self.text.split("\n"))
        if self.ocr_text:
            if self.text:
                parts.append(">\n")
            parts.extend(f"> {line}\n" for line in self.ocr_text.split("\n"))
        return "".join(parts)

    def _render_citation(self) -> str:
        """Render citation as markdown line."""
        if not self.citation:
            return ""
        citation_md = self.citation.format_markdown()
        if not citation_md:
            return ""
        return f"> \n{citation_md}\n"

    def _render_screenshot(self) -> str:
        """Render screenshot embed."""
        if self.screenshot_success and self.img_filename:
            return f"\n![[{self.img_filename}]]\n"
        return ""

    def to_markdown(self) -> str:
        """Convert captured content to markdown string.

        Format (Standalone Note):
        - YAML frontmatter (if tags present)
        - H1 title with timestamp
        - Blockquote with text + OCR
        - Citation line outside blockquote (italics, bullet separator)
        - Screenshot embed (if captured)
        """
        # Merge user tags with auto-generated tags from citation source
        all_tags = list(self.tags)
        if self.citation:
            for tag in self.citation.get_auto_tags():
                if tag not in all_tags:
                    all_tags.append(tag)

        parts = [self._render_frontmatter(all_tags)]
        parts.append(f"### 📌 {self.timestamp}\n\n")

        if self.template:
            parts.append(self._render_template())
            parts.append("\n")
        else:
            parts.append(self._render_blockquote())
            parts.append(self._render_citation())

        parts.append(self._render_screenshot())

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
