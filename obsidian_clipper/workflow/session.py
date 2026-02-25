"""Capture session data structure."""

from __future__ import annotations

import datetime
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

    def has_content(self) -> bool:
        """Check if any content was captured."""
        return bool(
            self.text
            or self.screenshot_path
            or self.screenshot_success
            or self.ocr_text
        )

    def to_markdown(self) -> str:
        """Convert captured content to markdown string.

        Format (Clean & Minimal):
        - H3 header with timestamp and pin emoji
        - Blockquote with text + OCR
        - Citation line outside blockquote (italics, bullet separator)
        - Screenshot embed (if captured)
        """
        parts = ["\n", f"### 📌 {self.timestamp}\n"]

        # Build blockquote with text and OCR using list comprehensions
        if self.text:
            parts.extend(f"> {line}\n" for line in self.text.split("\n"))

        if self.ocr_text:
            if self.text:
                parts.append(">\n")
            parts.extend(f"> {line}\n" for line in self.ocr_text.split("\n"))

        # Citation line (outside blockquote, with italics)
        # Reuse Citation.format_markdown() to avoid duplication
        if self.citation:
            citation_md = self.citation.format_markdown()
            if citation_md:
                parts.append("> \n")
                parts.append(citation_md)
                parts.append("\n")

        # Screenshot embed
        if self.screenshot_success and self.img_filename:
            parts.append(f"\n![[{self.img_filename}]]\n")

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
