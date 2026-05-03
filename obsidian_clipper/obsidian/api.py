"""Obsidian Local REST API client."""

from __future__ import annotations

import logging
import re
import warnings
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

import requests
from requests.adapters import HTTPAdapter
from urllib3.exceptions import InsecureRequestWarning
from urllib3.util.retry import Retry

from ..config import Config, get_config
from ..exceptions import (
    APIConnectionError,
    APIRequestError,
    PathSecurityError,
)

logger = logging.getLogger(__name__)

_DRIVE_LETTER_PATTERN = re.compile(r"^[A-Za-z]:")


def validate_path(path: str) -> str:
    """Validate a path for security — blocks traversal and Windows drives."""
    path = unquote(path).replace("\\", "/")
    while path.startswith("/"):
        path = path[1:]
    if not path:
        return ""
    if ".." in path.split("/") or _DRIVE_LETTER_PATTERN.search(path):
        raise PathSecurityError(f"Path traversal detected: {path}")
    return path


class ObsidianClient:
    """Client for Obsidian Local REST API."""

    def __init__(self, config: Config | None = None):
        self.config = config or get_config()
        self._session: requests.Session | None = None
        self._known_notes: set[str] = set()

    def _get_session(self) -> requests.Session:
        """Get or create HTTP session with retry logic."""
        if self._session is None:
            self._session = requests.Session()
            retry = Retry(total=3, backoff_factor=0.3, status_forcelist=[429, 500, 502, 503, 504])
            adapter = HTTPAdapter(max_retries=retry)
            self._session.mount("https://", adapter)
            self._session.mount("http://", adapter)
            self._session.headers.update({"Connection": "keep-alive"})
        return self._session

    def _build_url(self, path: str) -> str:
        """Build and validate URL for API endpoint."""
        safe_path = validate_path(path)
        encoded = quote(safe_path, safe="/:")
        return f"{self.config.base_url}/vault/{encoded}"

    def _execute_request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        """Execute HTTP request with error handling."""
        kwargs.setdefault("headers", {})
        kwargs["headers"].update(self.config.headers)
        kwargs.setdefault("verify", self.config.verify_ssl)
        kwargs.setdefault("timeout", self.config.timeout)

        try:
            session = self._get_session()
            if not kwargs.get("verify", True):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", InsecureRequestWarning)
                    return session.request(method, url, **kwargs)
            return session.request(method, url, **kwargs)
        except requests.exceptions.ConnectionError as e:
            raise APIConnectionError(f"Failed to connect to Obsidian API: {e}") from e
        except requests.exceptions.Timeout as e:
            raise APIRequestError("Request timed out") from e
        except requests.exceptions.RequestException as e:
            raise APIRequestError(f"Request failed: {e}") from e

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        """Make API request with path validation."""
        return self._execute_request(method, self._build_url(path), **kwargs)

    def check_connection(self) -> bool:
        """Check if the Obsidian Local REST API is reachable."""
        try:
            response = self._execute_request("GET", self.config.base_url + "/")
            return response.status_code in (200, 404)
        except (APIConnectionError, APIRequestError):
            return False

    @staticmethod
    def _default_initial_content(note_path: str) -> str:
        return f"# {Path(note_path).stem}\n"

    def ensure_note_exists(self, note_path: str, initial_content: str | None = None) -> bool:
        """Create target note if missing. Caches known-existing notes."""
        safe_path = validate_path(note_path)
        if initial_content is None:
            initial_content = self._default_initial_content(note_path)
        if safe_path in self._known_notes:
            return True
        try:
            response = self._request("GET", safe_path)
            if response.status_code == 200:
                self._known_notes.add(safe_path)
                return True
            if response.status_code == 404:
                create = self._request(
                    "PUT", safe_path,
                    headers={**self.config.headers, "Content-Type": "text/markdown"},
                    data=initial_content.encode("utf-8"),
                )
                if create.status_code in (200, 201, 204):
                    self._known_notes.add(safe_path)
                    return True
            return False
        except (APIConnectionError, APIRequestError) as e:
            logger.error("Failed to ensure note exists: %s", e)
            return False

    def create_note(self, note_path: str, content: str) -> bool:
        """Create a new note with content."""
        try:
            response = self._request(
                "PUT", note_path,
                headers={**self.config.headers, "Content-Type": "text/markdown"},
                data=content.encode("utf-8"),
            )
            return response.status_code in (200, 201, 204)
        except (APIConnectionError, APIRequestError) as e:
            logger.error("Failed to create note: %s", e)
            return False

    def append_to_note(self, note_path: str, content: str) -> bool:
        """Append content to a note."""
        try:
            response = self._request(
                "POST", note_path,
                headers={**self.config.headers, "Content-Type": "text/markdown"},
                data=content.encode("utf-8"),
            )
            return response.status_code in (200, 201, 204)
        except (APIConnectionError, APIRequestError) as e:
            logger.error("Failed to append to note: %s", e)
            return False

    def upload_image(self, img_path: str | Path, dest_filename: str | None = None, dest_dir: str | None = None) -> bool:
        """Upload an image to the vault."""
        img_path = Path(img_path)
        if not img_path.exists():
            logger.error("Image file not found: %s", img_path)
            return False

        ext = img_path.suffix.lower()
        content_type = {"webp": "image/webp"}.get(ext, "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png")

        try:
            with open(img_path, "rb") as f:
                img_data = f.read()
            dest = validate_path(f"{dest_dir or self.config.attachment_dir}{dest_filename or img_path.name}")
            response = self._request(
                "PUT", dest,
                headers={**self.config.headers, "Content-Type": content_type},
                data=img_data,
            )
            return response.status_code in (200, 201, 204)
        except (APIConnectionError, APIRequestError) as e:
            logger.error("Failed to upload image: %s", e)
            return False
        except OSError as e:
            logger.error("Failed to read image file: %s", e)
            return False

    def search(self, query: str, **kwargs: Any) -> list[dict]:
        """Search vault using structured search.

        Args:
            query: Search query string.
            **kwargs: Additional search parameters (e.g., context_length).

        Returns:
            List of search result dicts with 'filename', 'matches', etc.
        """
        try:
            url = f"{self.config.base_url}/search/"
            body = {"query": query, **kwargs}
            response = self._execute_request(
                "POST", url,
                headers={**self.config.headers, "Content-Type": "application/json"},
                json=body,
            )
            if response.status_code == 200:
                return response.json() if response.text.strip() else []
            return []
        except (APIConnectionError, APIRequestError) as e:
            logger.error("Search failed: %s", e)
            return []

    def search_simple(self, query: str) -> list[str]:
        """Simple text search returning matching file paths.

        Args:
            query: Search query string.

        Returns:
            List of matching file paths.
        """
        try:
            encoded_query = quote(query, safe="")
            url = f"{self.config.base_url}/search/simple/?query={encoded_query}"
            response = self._execute_request("GET", url)
            if response.status_code == 200:
                return response.json() if response.text.strip() else []
            return []
        except (APIConnectionError, APIRequestError) as e:
            logger.error("Simple search failed: %s", e)
            return []

    def get_tags(self) -> dict[str, dict]:
        """List all tags in the vault with metadata.

        Returns:
            Dict mapping tag names to metadata dicts.
        """
        try:
            url = f"{self.config.base_url}/tags/"
            response = self._execute_request("GET", url)
            if response.status_code == 200:
                return response.json() if response.text.strip() else {}
            return {}
        except (APIConnectionError, APIRequestError) as e:
            logger.error("Failed to get tags: %s", e)
            return {}

    def list_directory(self, path: str = "") -> list[str]:
        """List files in a vault directory.

        Args:
            path: Directory path (empty string for root).

        Returns:
            List of file paths in the directory.
        """
        try:
            safe_path = validate_path(path)
            url = self._build_url(safe_path) if safe_path else f"{self.config.base_url}/vault/"
            # Ensure trailing slash for directory listing
            if not url.endswith("/"):
                url += "/"
            response = self._execute_request("GET", url)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    return list(data.get("files", []))
                return list(data)
            return []
        except (APIConnectionError, APIRequestError) as e:
            logger.error("Failed to list directory: %s", e)
            return []

    def open_note(self, note_path: str, new_leaf: bool = False) -> bool:
        """Open a note in Obsidian.

        Args:
            note_path: Path to the note to open.
            new_leaf: If True, open in a new pane.

        Returns:
            True if the open request succeeded.
        """
        try:
            safe_path = validate_path(note_path)
            url = f"{self.config.base_url}/open/{quote(safe_path, safe='/')}"
            params: dict[str, str] = {}
            if new_leaf:
                params["newLeaf"] = "true"
            response = self._execute_request("POST", url, params=params)
            return response.status_code in (200, 204)
        except (APIConnectionError, APIRequestError) as e:
            logger.error("Failed to open note: %s", e)
            return False

    def get_active_file(self) -> str | None:
        """Get the path of the currently active file in Obsidian.

        Returns:
            Active file path, or None if not available.
        """
        try:
            url = f"{self.config.base_url}/active/"
            response = self._execute_request("GET", url)
            if response.status_code == 200:
                data = response.json()
                return str(data.get("filepath", "")) or None
            return None
        except (APIConnectionError, APIRequestError) as e:
            logger.error("Failed to get active file: %s", e)
            return None

    def get_periodic_note(self, period: str = "daily") -> str | None:
        """Get content of a periodic note.

        Args:
            period: Note period — 'daily', 'weekly', 'monthly'.

        Returns:
            Note content, or None if not found.
        """
        try:
            url = f"{self.config.base_url}/periodic/{period}/"
            response = self._execute_request("GET", url)
            if response.status_code == 200:
                return str(response.text)
            return None
        except (APIConnectionError, APIRequestError) as e:
            logger.error("Failed to get periodic note: %s", e)
            return None

    def append_periodic_note(self, period: str, content: str) -> bool:
        """Append content to a periodic note.

        Args:
            period: Note period — 'daily', 'weekly', 'monthly'.
            content: Markdown content to append.

        Returns:
            True if successful.
        """
        try:
            url = f"{self.config.base_url}/periodic/{period}/"
            response = self._execute_request(
                "POST", url,
                headers={**self.config.headers, "Content-Type": "text/markdown"},
                data=content.encode("utf-8"),
            )
            return response.status_code in (200, 201, 204)
        except (APIConnectionError, APIRequestError) as e:
            logger.error("Failed to append to periodic note: %s", e)
            return False

    def close(self) -> None:
        if self._session:
            self._session.close()
            self._session = None

    def __enter__(self) -> ObsidianClient:
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: object) -> None:
        self.close()
