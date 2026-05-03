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

    def close(self) -> None:
        if self._session:
            self._session.close()
            self._session = None

    def __enter__(self) -> ObsidianClient:
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: object) -> None:
        self.close()
