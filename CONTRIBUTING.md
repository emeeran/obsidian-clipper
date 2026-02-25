# Contributing to Obsidian Clipper

Thank you for your interest in contributing to Obsidian Clipper! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Git

### Quick Start

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/obsidian-clipper.git
   cd obsidian-clipper
   ```

2. **Create a virtual environment and install dependencies**
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -e ".[dev]"
   ```

3. **Install pre-commit hooks**
   ```bash
   pre-commit install
   ```

4. **Run tests to verify setup**
   ```bash
   pytest
   ```

## Development Workflow

### Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clean, typed Python code
   - Follow the existing code style (enforced by black, isort, ruff)
   - Add tests for new functionality

3. **Run quality checks**
   ```bash
   # Format code
   black .
   isort .

   # Lint
   ruff check .

   # Type check
   mypy obsidian_clipper/

   # Run tests
   pytest --cov
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: description of your change"
   ```

   We follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation
   - `test:` for tests
   - `refactor:` for code refactoring
   - `chore:` for maintenance tasks

5. **Push and create a pull request**
   ```bash
   git push origin feature/your-feature-name
   ```

## Code Standards

### Type Annotations

All code must be properly typed:

```python
def process_text(text: str, max_length: int = 100) -> str:
    """Process text with optional max length."""
    return text[:max_length]
```

### Documentation

- Use docstrings for all public modules, classes, and functions
- Follow Google-style docstrings:

```python
def capture_screenshot(output_path: Path) -> bool:
    """Capture a screenshot to the specified path.

    Args:
        output_path: Path where screenshot will be saved.

    Returns:
        True if capture was successful, False otherwise.

    Raises:
        ScreenshotError: If screenshot capture fails.
    """
```

### Testing

- Aim for 85%+ test coverage
- Write unit tests for all new functionality
- Use pytest fixtures for common setup
- Mock external dependencies (APIs, subprocesses)

```python
class TestNewFeature:
    """Tests for new feature."""

    def test_basic_functionality(self):
        """Test basic use case."""
        result = new_feature("input")
        assert result == "expected"

    def test_edge_case(self):
        """Test edge case handling."""
        with pytest.raises(ValueError):
            new_feature("")
```

## Project Structure

```
obsidian-clipper/
├── .github/              # CI/CD workflows
├── obsidian_clipper/     # Main package
│   ├── capture/          # Text/screenshot capture
│   ├── cli/              # Command-line interface
│   ├── obsidian/         # Obsidian API client
│   ├── utils/            # Utilities (logging, retry, etc.)
│   └── workflow/         # Capture workflow
├── tests/                # Test suite
├── pyproject.toml        # Project configuration
└── README.md             # User documentation
```

## Release Process

Releases are automated via GitHub Actions:

1. Update version in `obsidian_clipper/_version.py`
2. Update `CHANGELOG.md` with changes
3. Create a GitHub release with tag `vX.Y.Z`
4. CI automatically publishes to PyPI

## Getting Help

- Open an issue for bugs or feature requests
- Check existing issues before creating new ones
- Provide minimal reproducible examples for bugs

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
