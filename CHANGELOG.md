# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- CI pipeline with GitHub Actions (lint, type-check, tests, pip-audit, bandit)
- Docker support with multi-stage builds
- Docker Compose configuration (experimental — requires host display access; see README)
- `--selection {primary,clipboard}` flag to capture from the clipboard instead of primary selection
- `ObsidianClient.list_vault_files()` public API for vault-wide file listing
- Concurrent text + citation capture to reduce capture latency

### Fixed
- webp screenshots now upload with the correct `image/webp` content type (previously mislabeled as `image/png`)
- EPUB reader "Atril" is no longer misspelled ("Atris") in citation title stripping
- `--json-logs` / `LOG_FORMAT=json` now produces structured JSON logs (the option was previously a no-op)
- Periodic-note `period` parameter is validated against supported values

### Changed
- Subprocess calls in the capture modules routed through the shared safe-execution helper
- Filename hash uses `hashlib.md5(..., used_for_security=False)`
- URI fallback now warns when capture content may exceed `obsidian://` URI length limits
- Actionable message when no display server (X11/Wayland) is detected

### Removed
- Overstated changelog claims about automated PyPI publishing, Dependabot, and a
  circuit-breaker pattern — none of these were implemented

## [1.0.1] - 2024-01-15

### Added
- Initial release
- Text capture from X11 selection
- Screenshot capture with Flameshot/Grim support
- OCR processing with Tesseract
- Citation detection from PDF readers and browsers
- Obsidian Local REST API integration
- Configuration via environment variables
- Desktop notifications

### Security
- Path traversal protection
- API key handling via environment variables
- Input validation

[Unreleased]: https://github.com/emeeran/obsidian-clipper/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/emeeran/obsidian-clipper/releases/tag/v1.0.1
