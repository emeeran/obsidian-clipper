"""Citation parsing utilities."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum

from .text import get_active_window_title

logger = logging.getLogger(__name__)

IGNORED_WINDOW_TITLE_PATTERNS = (
    r"flameshot",
    r"obsidian\s*clipper",
    r"gnome\s*shell",
)


def _looks_like_pdf_or_epub_context(window_title: str) -> bool:
    """Check whether a title appears to come from PDF/EPUB context."""
    return bool(
        re.search(
            r"(\.pdf\b|\.epub\b|Okular|Evince|Zathura|Foliate|Calibre|Thorium|FBReader)",
            window_title,
            re.IGNORECASE,
        )
    )


def _extract_page_number(text: str) -> str | None:
    """Extract page number from common reader title patterns."""
    patterns = [
        r"\b(?:page|p\.|pg\.)\s*(\d+)\b",
        r"\((\d+)\s*/\s*\d+\)",
        r"\b(\d+)\s*/\s*\d+\b",
        r"\b(\d+)\s+of\s+\d+\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _strip_trailing_page_segment(title: str) -> str:
    """Strip trailing page markers such as '— 44/320' from title."""
    patterns = [
        r"\s*[—\-–]\s*(?:page|p\.|pg\.)\s*\d+\s*$",
        r"\s*[—\-–]\s*\d+\s*/\s*\d+\s*$",
        r"\s*[—\-–]\s*\d+\s+of\s+\d+\s*$",
    ]
    cleaned = title
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


class SourceType(Enum):
    """Type of citation source."""

    PDF = "pdf"
    EPUB = "epub"
    BROWSER = "browser"
    UNKNOWN = "unknown"


@dataclass
class Citation:
    """Represents a citation from a source document.

    Attributes:
        title: Document or page title.
        page: Page number (for PDFs).
        url: URL (for web sources).
        source: Source application name.
        source_type: Type of source (PDF, browser, etc.).
    """

    title: str
    page: str | None = None
    url: str | None = None
    source: str | None = None
    source_type: SourceType = SourceType.UNKNOWN
    extra: dict = field(default_factory=dict)

    def format_markdown(self) -> str:
        """Format citation as markdown string.

        Returns:
            Formatted citation string with em-dash prefix.
        """
        parts = []

        if self.title:
            citation_title = self.title
            if self.page:
                citation_title = f"{citation_title}, p. {self.page}"
            parts.append(f"*{citation_title}*")

        if self.source and self.source not in ("PDF Reader", "Browser", "Unknown"):
            parts.append(self.source)

        return " — " + " · ".join(parts) if parts else ""

    def __str__(self) -> str:
        return self.format_markdown()


def parse_pdf_citation(window_title: str) -> Citation | None:
    """Parse window title to extract PDF citation info.

    Supports:
    - Evince: "Document.pdf — Page 42"
    - Zathura: "Document.pdf (42/100)"
    - Generic PDF patterns

    Args:
        window_title: Window title string.

    Returns:
        Citation object if PDF detected, None otherwise.
    """
    if not window_title:
        return None

    page_number = _extract_page_number(window_title)

    # Evince: "Document.pdf — Page 42"
    evince_match = re.match(
        r"(.+\.pdf)\s*[—\-–]\s*Page\s*(\d+)", window_title, re.IGNORECASE
    )
    if evince_match:
        return Citation(
            title=evince_match.group(1).strip(),
            page=evince_match.group(2),
            source="Evince",
            source_type=SourceType.PDF,
        )

    # Zathura: "Document.pdf (42/100)"
    zathura_match = re.match(r"(.+\.pdf)\s*\((\d+)/\d+\)", window_title, re.IGNORECASE)
    if zathura_match:
        return Citation(
            title=zathura_match.group(1).strip(),
            page=zathura_match.group(2),
            source="Zathura",
            source_type=SourceType.PDF,
        )

    # Okular: "Document.pdf : Page 42 - Okular" or "Document Title — Okular"
    okular_match = re.match(
        r"(.+\.pdf)\s*:\s*Page\s*(\d+)\s*-\s*Okular", window_title, re.IGNORECASE
    )
    if okular_match:
        return Citation(
            title=okular_match.group(1).strip(),
            page=okular_match.group(2),
            source="Okular",
            source_type=SourceType.PDF,
        )

    # Okular: "Document Title — Page 42 — Okular"
    okular_title_page_match = re.match(
        r"(.+?)\s*[—\-–]\s*Page\s*(\d+)\s*[—\-–]\s*Okular",
        window_title,
        re.IGNORECASE,
    )
    if okular_title_page_match:
        return Citation(
            title=okular_title_page_match.group(1).strip(),
            page=okular_title_page_match.group(2),
            source="Okular",
            source_type=SourceType.PDF,
        )

    # Okular without .pdf in title: "Document Title — Okular"
    okular_generic = re.match(r"(.+?)\s*[—\-–]\s*Okular", window_title, re.IGNORECASE)
    if okular_generic:
        title = _strip_trailing_page_segment(okular_generic.group(1).strip())
        # Only match if it looks like a document title and page was detected.
        if title and len(title) > 3 and page_number:
            return Citation(
                title=title,
                page=page_number,
                source="Okular",
                source_type=SourceType.PDF,
            )

    # Generic PDF pattern - prefer longer matches (e.g., full filename with spaces)
    # Match any non-newline characters before .pdf
    generic_match = re.search(r"([^\n]+\.pdf)", window_title, re.IGNORECASE)
    if generic_match:
        if not page_number:
            return None

        return Citation(
            title=generic_match.group(1).strip(),
            page=page_number,
            source="PDF Reader",
            source_type=SourceType.PDF,
        )

    # Reader-style title without .pdf but with explicit page and known PDF app
    reader_match = re.search(r"(Okular|Evince|Zathura)", window_title, re.IGNORECASE)
    if reader_match and page_number:
        title = re.sub(
            r"\s*[—\-–]\s*(Okular|Evince|Zathura).*",
            "",
            window_title,
            flags=re.IGNORECASE,
        ).strip()
        title = _strip_trailing_page_segment(title)
        if title and len(title) > 3:
            return Citation(
                title=title,
                page=page_number,
                source=reader_match.group(1),
                source_type=SourceType.PDF,
            )

    return None


def parse_epub_citation(window_title: str) -> Citation | None:
    """Parse window title to extract EPUB citation info with required page.

    Supports patterns such as:
    - "Book Title.epub — Page 12"
    - "Book Title — Page 12 — Foliate"
    - "Book Title - Page 12 - Calibre"
    """
    if not window_title:
        return None

    if "epub" not in window_title.lower() and not re.search(
        r"(Foliate|Calibre|Thorium|FBReader)", window_title, re.IGNORECASE
    ):
        return None

    page_number = _extract_page_number(window_title)
    if not page_number:
        return None

    source_match = re.search(
        r"(Foliate|Calibre|Thorium|FBReader)", window_title, re.IGNORECASE
    )
    source = source_match.group(1) if source_match else "EPUB Reader"

    title_match = re.match(
        r"(.+?)\s*[—\-–]\s*(?:Page|p\.)\s*\d+", window_title, re.IGNORECASE
    )
    if title_match:
        title = title_match.group(1).strip()
    else:
        title = re.sub(
            r"\s*[—\-–]\s*(Foliate|Calibre|Thorium|FBReader).*",
            "",
            window_title,
            flags=re.IGNORECASE,
        ).strip()
    title = _strip_trailing_page_segment(title)

    return Citation(
        title=title,
        page=page_number,
        source=source,
        source_type=SourceType.EPUB,
    )


def parse_browser_citation(window_title: str) -> Citation | None:
    """Parse window title to extract browser source info.

    Supports Chrome, Firefox, Edge, Brave, and other browsers.

    Args:
        window_title: Window title string.

    Returns:
        Citation object if browser detected, None otherwise.
    """
    if not window_title:
        return None

    # Browser match: "Page Title - Google Chrome"
    browser_patterns = [
        r"(.+?)\s*[—\-–]\s*(Google Chrome|Chrome)",
        r"(.+?)\s*[—\-–]\s*(Mozilla Firefox|Firefox)",
        r"(.+?)\s*[—\-–]\s*(Microsoft Edge|Edge)",
        r"(.+?)\s*[—\-–]\s*(Brave)",
        r"(.+?)\s*[—\-–]\s*(Chromium)",
        r"(.+?)\s*—\s*(Vivaldi)",
    ]

    for pattern in browser_patterns:
        match = re.match(pattern, window_title)
        if match:
            return Citation(
                title=match.group(1).strip(),
                source=match.group(2),
                source_type=SourceType.BROWSER,
            )

    return None


def parse_code_editor_citation(window_title: str) -> Citation | None:
    """Parse window title to extract code editor info.

    Supports VSCode, Neovim, and other editors.

    Args:
        window_title: Window title string.

    Returns:
        Citation object if code editor detected, None otherwise.
    """
    if not window_title:
        return None

    # VSCode: "filename.py - project - Visual Studio Code"
    vscode_match = re.match(r"(.+?)\s*-\s*(.+?)\s*-\s*Visual Studio Code", window_title)
    if vscode_match:
        return Citation(
            title=vscode_match.group(1).strip(),
            source="VSCode",
            source_type=SourceType.UNKNOWN,
            extra={"project": vscode_match.group(2).strip()},
        )

    # Generic: "filename.py - ProjectName"
    generic_match = re.match(r"(.+?\.\w+)\s*-\s*(.+)", window_title)
    if generic_match:
        return Citation(
            title=generic_match.group(1).strip(),
            source=generic_match.group(2).strip(),
            source_type=SourceType.UNKNOWN,
        )

    return None


def parse_generic_citation(window_title: str) -> Citation | None:
    """Parse citation from generic app titles as a last-resort fallback.

    Expected patterns:
    - "Page title - App Name"
    - "Page title — App Name"

    Skips known PDF/EPUB reader apps so mandatory page rules remain enforced.
    """
    if not window_title:
        return None

    if re.search(
        r"(Okular|Evince|Zathura|Foliate|Calibre|Thorium|FBReader)",
        window_title,
        re.IGNORECASE,
    ):
        return None

    match = re.match(r"(.+?)\s*[—\-–]\s*(.+)$", window_title)
    if not match:
        return None

    title = match.group(1).strip()
    source = match.group(2).strip()

    if not title or not source:
        return None

    return Citation(
        title=title,
        source=source,
        source_type=SourceType.UNKNOWN,
    )


def parse_citation_from_window_title(window_title: str) -> Citation | None:
    """Parse a citation directly from a given window title."""
    if not window_title:
        return None

    for parser in CITATION_PARSERS:
        citation = parser(window_title)
        if citation:
            return citation

    if _looks_like_pdf_or_epub_context(window_title):
        return None

    normalized_title = window_title.strip()
    if not normalized_title:
        return None

    return Citation(
        title=normalized_title,
        source_type=SourceType.UNKNOWN,
    )


# Parser registry: ordered list of citation parsers
CITATION_PARSERS = [
    parse_pdf_citation,
    parse_epub_citation,
    parse_browser_citation,
    parse_code_editor_citation,
    parse_generic_citation,
]


def _is_ignored_window(window_title: str) -> bool:
    """Check if window title should be ignored."""
    return any(
        re.search(pattern, window_title, re.IGNORECASE)
        for pattern in IGNORED_WINDOW_TITLE_PATTERNS
    )


def _try_get_citation() -> Citation | None:
    """Single attempt to get citation from active window."""
    window_title = get_active_window_title()
    if not window_title:
        return None

    if _is_ignored_window(window_title):
        return None

    return parse_citation_from_window_title(window_title)


def get_citation() -> Citation | None:
    """Auto-detect citation from active window.

    Tries PDF readers, browsers, and code editors in order.
    Retries briefly because global hotkeys can momentarily shift focus
    to transient windows (e.g. Flameshot / GNOME Shell) before returning.

    Returns:
        Citation object if source detected, None otherwise.
    """
    from ..utils import retry_with_backoff

    return retry_with_backoff(
        _try_get_citation,
        max_attempts=6,
        delay=0.12,
        backoff=1.0,  # No backoff, constant delay
    )
