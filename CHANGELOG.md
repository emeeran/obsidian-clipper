# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Production-ready CI/CD pipeline with GitHub Actions
- Automated PyPI publishing on releases
- Dependabot configuration for dependency updates
- Structured JSON logging with rotation support
- Docker support with multi-stage builds
- Docker Compose configuration for easy deployment
- Comprehensive logging utilities with sensitive data filtering
- Circuit breaker pattern for API resilience

### Changed
- Improved error handling with proper exception chaining
- Enhanced CLI with `--log-file` and `--json-logs` options
- Better test coverage (89%+ overall, 100% for core modules)

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
