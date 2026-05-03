"""Citation parsing utilities."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .text import get_active_window_title

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pre-compiled regex patterns
# ---------------------------------------------------------------------------

IGNORED_WINDOW_TITLE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"flameshot", re.IGNORECASE),
    re.compile(r"obsidian\s*clipper", re.IGNORECASE),
    re.compile(r"gnome\s*shell", re.IGNORECASE),
]

# Combined: matches any page-number representation in reader titles.
#   "page 42" | "p. 42" | "pg. 42" | "(42/100)" | "42/100" | "42 of 100"
PAGE_NUMBER_PATTERN = re.compile(
    r"\b(?:page|p\.|pg\.)\s*(\d+)\b"
    r"|\((\d+)\s*/\s*\d+\)"
    r"|\b(\d+)\s*/\s*\d+\b"
    r"|\b(\d+)\s+of\s+\d+\b",
    re.IGNORECASE,
)

# Combined: trailing page segment after an em/regular dash.
#   "— page 42" | "— 42/100" | "— 42 of 100"
TRAILING_PAGE_PATTERN = re.compile(
    r"\s*[—\-–]\s*(?:(?:page|p\.|pg\.)\s*\d+|\d+\s*/\s*\d+|\d+\s+of\s+\d+)\s*$",
    re.IGNORECASE,
)

PDF_EPUB_CONTEXT_PATTERN = re.compile(
    r"(\.pdf\b|\.epub\b|Okular|Evince|Zathura|Foliate|Calibre|Thorium|FBReader)",
    re.IGNORECASE,
)

EPUB_APP_PATTERN = re.compile(
    r"(Foliate|Calibre|Thorium|FBReader|Atril|Xreader|MuPDF)", re.IGNORECASE
)

# Browser title patterns: "Page Title — BrowserName"
BROWSER_PATTERN = re.compile(
    r"(.+?)\s*[—\-–]\s*"
    r"(Google Chrome|Chrome|Mozilla Firefox|Firefox|Microsoft Edge|Edge"
    r"|Brave|Chromium|Vivaldi)"
)

# Reader apps whose titles should be skipped by the generic fallback parser
READER_APP_PATTERN = re.compile(
    r"(Okular|Evince|Zathura|Foliate|Calibre|Thorium|FBReader)", re.IGNORECASE
)

# Citation detection retry configuration
CITATION_RETRY_ATTEMPTS = 6
CITATION_RETRY_DELAY = 0.12  # seconds between attempts
CITATION_RETRY_BACKOFF = 1.0  # constant delay (no exponential backoff)

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _extract_page_number(text: str) -> str | None:
    """Extract the first page number from common reader title patterns."""
    match = PAGE_NUMBER_PATTERN.search(text)
    if not match:
        return None
    # The combined pattern has four capture groups; exactly one matches.
    return next(g for g in match.groups() if g is not None)


def _strip_trailing_page_segment(title: str) -> str:
    """Strip trailing page markers such as '- 44/320' from *title*."""
    return TRAILING_PAGE_PATTERN.sub("", title).strip()


def _looks_like_pdf_or_epub_context(window_title: str) -> bool:
    """Check whether a title appears to come from PDF/EPUB context."""
    return bool(PDF_EPUB_CONTEXT_PATTERN.search(window_title))


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


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
    extra: dict[str, Any] = field(default_factory=dict)

    def format_markdown(self) -> str:
        """Format citation as markdown string."""
        parts: list[str] = []
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

    def get_auto_tags(self) -> list[str]:
        """Suggest tags based on source type."""
        tag_map: dict[SourceType, list[str]] = {
            SourceType.PDF: ["pdf", "research"],
            SourceType.EPUB: ["epub", "reading"],
            SourceType.BROWSER: ["web", "article"],
        }
        return tag_map.get(self.source_type, [])[:]


# ---------------------------------------------------------------------------
# Document parsers (PDF + EPUB share core logic)
# ---------------------------------------------------------------------------


def _parse_document_citation(
    window_title: str,
    source_type: SourceType,
) -> Citation | None:
    """Parse a window title from a PDF or EPUB reader.

    Supports Evince, Zathura, Okular, Foliate, Calibre, Thorium, FBReader,
    and generic patterns (including ``.pdf`` / ``.epub`` in the title).
    """
    if not window_title:
        return None

    page_number = _extract_page_number(window_title)

    # -- Evince: "Document.pdf — Page 42" ---------------------------------
    evince_match = re.match(
        r"(.+\.pdf)\s*[—\-–]\s*Page\s*(\d+)", window_title, re.IGNORECASE
    )
    if evince_match:
        return Citation(
            title=evince_match.group(1).strip(),
            page=evince_match.group(2),
            source="Evince",
            source_type=source_type,
        )

    # -- Zathura: "Document.pdf (42/100)" ----------------------------------
    zathura_match = re.match(
        r"(.+\.pdf)\s*\((\d+)/\d+\)", window_title, re.IGNORECASE
    )
    if zathura_match:
        return Citation(
            title=zathura_match.group(1).strip(),
            page=zathura_match.group(2),
            source="Zathura",
            source_type=source_type,
        )

    # -- Okular: "Doc.pdf : Page 42 - Okular" ------------------------------
    okular_match = re.match(
        r"(.+\.pdf)\s*:\s*Page\s*(\d+)\s*-\s*Okular", window_title, re.IGNORECASE
    )
    if okular_match:
        return Citation(
            title=okular_match.group(1).strip(),
            page=okular_match.group(2),
            source="Okular",
            source_type=source_type,
        )

    # -- Okular: "Title — Page 42 — Okular" --------------------------------
    okular_tp = re.match(
        r"(.+?)\s*[—\-–]\s*Page\s*(\d+)\s*[—\-–]\s*Okular",
        window_title,
        re.IGNORECASE,
    )
    if okular_tp:
        return Citation(
            title=okular_tp.group(1).strip(),
            page=okular_tp.group(2),
            source="Okular",
            source_type=source_type,
        )

    # -- Okular (generic): "Title — Okular" with page elsewhere -------------
    okular_generic = re.match(
        r"(.+?)\s*[—\-–]\s*Okular", window_title, re.IGNORECASE
    )
    if okular_generic:
        title = _strip_trailing_page_segment(okular_generic.group(1).strip())
        if title and len(title) > 3 and page_number:
            return Citation(
                title=title,
                page=page_number,
                source="Okular",
                source_type=source_type,
            )

    # -- EPUB app with named reader (Foliate, Calibre, …) ------------------
    if source_type is SourceType.EPUB:
        epub_app_match = EPUB_APP_PATTERN.search(window_title)
        if epub_app_match and page_number:
            source = epub_app_match.group(1)
            title_match = re.match(
                r"(.+?)\s*[—\-–]\s*(?:Page|p\.)\s*\d+",
                window_title,
                re.IGNORECASE,
            )
            if title_match:
                title = _strip_trailing_page_segment(title_match.group(1).strip())
            else:
                title = _strip_trailing_page_segment(
                    re.sub(
                        r"\s*[—\-–]\s*(Foliate|Calibre|Thorium|FBReader|Atris|Xreader|MuPDF).*",
                        "",
                        window_title,
                        flags=re.IGNORECASE,
                    ).strip()
                )
            if title and len(title) > 3:
                return Citation(
                    title=title,
                    page=page_number,
                    source=source,
                    source_type=SourceType.EPUB,
                )

    # -- Generic file extension match (.pdf / .epub) -----------------------
    ext = r"\.pdf" if source_type is SourceType.PDF else r"\.epub"
    generic_match = re.search(
        rf"([^\n]+{ext})", window_title, re.IGNORECASE
    )
    if generic_match:
        if not page_number:
            return None
        return Citation(
            title=generic_match.group(1).strip(),
            page=page_number,
            source="PDF Reader" if source_type is SourceType.PDF else "EPUB Reader",
            source_type=source_type,
        )

    # -- Known reader app in title without file extension -------------------
    if source_type is SourceType.PDF:
        reader_match = re.search(r"(Okular|Evince|Zathura)", window_title, re.IGNORECASE)
        if reader_match and page_number:
            title = _strip_trailing_page_segment(
                re.sub(
                    r"\s*[—\-–]\s*(Okular|Evince|Zathura).*",
                    "",
                    window_title,
                    flags=re.IGNORECASE,
                ).strip()
            )
            if title and len(title) > 3:
                return Citation(
                    title=title,
                    page=page_number,
                    source=reader_match.group(1),
                    source_type=SourceType.PDF,
                )

    return None


def parse_pdf_citation(window_title: str) -> Citation | None:
    """Parse window title to extract PDF citation info.

    Supports Evince, Zathura, Okular, and generic PDF patterns.
    """
    return _parse_document_citation(window_title, SourceType.PDF)


def parse_epub_citation(window_title: str) -> Citation | None:
    """Parse window title to extract EPUB citation info.

    Supports Foliate, Calibre, Thorium, FBReader, and generic EPUB patterns.
    """
    if not window_title:
        return None
    # Guard: only proceed if this looks like an EPUB context
    if (
        ".epub" not in window_title.lower()
        and not EPUB_APP_PATTERN.search(window_title)
    ):
        return None
    return _parse_document_citation(window_title, SourceType.EPUB)


# ---------------------------------------------------------------------------
# Browser / editor / generic parsers
# ---------------------------------------------------------------------------


def parse_browser_citation(window_title: str) -> Citation | None:
    """Parse window title to extract browser source info.

    Supports Chrome, Firefox, Edge, Brave, Chromium, and Vivaldi.
    """
    if not window_title:
        return None
    match = BROWSER_PATTERN.match(window_title)
    if match:
        return Citation(
            title=match.group(1).strip(),
            source=match.group(2),
            source_type=SourceType.BROWSER,
        )
    return None


def parse_code_editor_citation(window_title: str) -> Citation | None:
    """Parse window title to extract code editor info.

    Supports VSCode and generic ``filename.ext - ProjectName`` patterns.
    """
    if not window_title:
        return None

    # VSCode: "filename.py - project - Visual Studio Code"
    vscode_match = re.match(
        r"(.+?)\s*-\s*(.+?)\s*-\s*Visual Studio Code", window_title
    )
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
    """Last-resort fallback: split on dash if no known reader app detected."""
    if not window_title:
        return None
    if READER_APP_PATTERN.search(window_title):
        return None
    match = re.match(r"(.+?)\s*[—\-–]\s*(.+)$", window_title)
    if not match:
        return None
    title, source = match.group(1).strip(), match.group(2).strip()
    if not title or not source:
        return None
    return Citation(title=title, source=source, source_type=SourceType.UNKNOWN)


# ---------------------------------------------------------------------------
# Parser list and top-level dispatch
# ---------------------------------------------------------------------------

_PARSERS = [
    parse_pdf_citation,
    parse_epub_citation,
    parse_browser_citation,
    parse_code_editor_citation,
    parse_generic_citation,
]


def parse_citation_from_window_title(window_title: str) -> Citation | None:
    """Parse a citation directly from a given window title."""
    if not window_title:
        return None

    for parser in _PARSERS:
        citation = parser(window_title)
        if citation:
            return citation

    # PDF/EPUB context detected but no parser matched — return None so the
    # caller knows we deliberately skipped it (missing page number, etc.).
    if _looks_like_pdf_or_epub_context(window_title):
        return None

    normalized = window_title.strip()
    if not normalized:
        return None
    return Citation(title=normalized, source_type=SourceType.UNKNOWN)


# ---------------------------------------------------------------------------
# Active-window helpers
# ---------------------------------------------------------------------------


def _is_ignored_window(window_title: str) -> bool:
    """Check if window title should be ignored."""
    return any(p.search(window_title) for p in IGNORED_WINDOW_TITLE_PATTERNS)


def _try_get_citation() -> Citation | None:
    """Single attempt to get citation from active window."""
    window_title = get_active_window_title()
    if not window_title or _is_ignored_window(window_title):
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
        max_attempts=CITATION_RETRY_ATTEMPTS,
        delay=CITATION_RETRY_DELAY,
        backoff=CITATION_RETRY_BACKOFF,
    )
