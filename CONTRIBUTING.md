# Contributing to openclaw-dash

Thanks for your interest in contributing! 🎉 This guide will help you get started.

## Table of Contents

- [Quick Start](#quick-start)
- [Development Setup](#development-setup)
- [Project Architecture](#project-architecture)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Style](#code-style)
- [Pull Requests](#pull-requests)
- [Getting Help](#getting-help)

## Quick Start

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/openclaw-dash.git
cd openclaw-dash

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dev dependencies
pip install -e ".[dev]"

# 4. Verify setup
pytest tests/ -v
openclaw-dash --help
```

## Development Setup

### Prerequisites

- **Python 3.10+** (3.11 or 3.12 recommended)
- **Git**
- A terminal with good Unicode/color support (iTerm2, Alacritty, Windows Terminal)

### Environment Setup

We recommend using a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

The `[dev]` extras include:
- `pytest` — Test framework
- `pytest-asyncio` — Async test support  
- `pytest-cov` — Coverage reporting
- `ruff` — Linting and formatting
- `mypy` — Static type checking

### Running the Dashboard

```bash
# Launch TUI
openclaw-dash

# Demo mode (mock data, no gateway needed)
openclaw-dash --demo

# Quick status check
openclaw-dash --status
```

## Project Architecture

```
src/openclaw_dash/
├── app.py              # Main TUI application (Textual)
├── cli.py              # CLI entry point
├── config.py           # User preferences (~/.config/openclaw-dash/)
├── themes.py           # Color themes (dark, light, hacker)
├── version.py          # Version info with git metadata
├── commands.py         # Command palette (Ctrl+P)
├── demo.py             # Mock data for demo mode
├── exporter.py         # Export dashboard state
│
├── collectors/         # Data fetching modules
│   ├── gateway.py      # OpenClaw gateway status
│   ├── sessions.py     # Active sessions
│   ├── repos.py        # Repository health (PRs, TODOs)
│   ├── alerts.py       # Alert aggregation
│   └── ...
│
├── widgets/            # UI components (Textual widgets)
│   ├── ascii_art.py    # Visual primitives (progress bars, sparklines)
│   ├── metric_boxes.py # KPI header bar
│   ├── sessions.py     # Sessions panel
│   └── ...
│
├── metrics/            # Metrics collection
│   ├── costs.py        # Token cost tracking
│   ├── github.py       # GitHub stats
│   └── performance.py  # API performance
│
├── security/           # Security auditing
│   ├── audit.py        # Config scanning
│   ├── deps.py         # Dependency checks
│   └── fixes.py        # Auto-fix logic
│
├── automation/         # Automation features
│   ├── pr_auto.py      # PR auto-merge
│   └── deps_auto.py    # Dependency updates
│
└── tools/              # Bundled CLI tools
    ├── repo-scanner.py
    └── ...
```

### Key Concepts

- **Collectors**: Fetch data from external sources (APIs, CLI tools, files)
- **Widgets**: Display data in the TUI using Textual
- **Metrics**: Track costs, performance, and stats over time
- **Commands**: Actions available via command palette

### Data Flow

```
External Sources → Collectors → Widgets → TUI Display
       ↑                                      ↓
    (gateway, gh CLI, files)           (user interaction)
```

## Making Changes

### 1. Create a Branch

```bash
git checkout -b feature/your-feature
# or
git checkout -b fix/issue-description
```

Branch naming conventions:
- `feature/` — New features
- `fix/` — Bug fixes
- `docs/` — Documentation only
- `refactor/` — Code refactoring
- `test/` — Test additions/changes

### 2. Make Your Changes

- Keep changes focused — one feature or fix per branch
- Add tests for new functionality
- Update documentation if needed
- Follow existing code patterns

### 3. Test Your Changes

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_widgets.py -v

# Run with coverage
pytest tests/ --cov=openclaw_dash --cov-report=html
```

### 4. Check Code Quality

```bash
# Lint
ruff check src/ tests/

# Auto-fix lint issues
ruff check src/ tests/ --fix

# Format code
ruff format src/ tests/

# Type check (optional but appreciated)
mypy src/
```

## Testing

### Test Organization

```
tests/
├── conftest.py         # Shared fixtures
├── test_widgets.py     # Widget tests
├── test_collectors.py  # Collector tests
├── test_config.py      # Configuration tests
└── ...
```

### Writing Tests

```python
"""Tests for my feature."""

import pytest


class TestMyFeature:
    """Test suite for MyFeature."""

    def test_basic_functionality(self):
        """Feature does what it's supposed to do."""
        result = my_function()
        assert result == expected

    def test_edge_case(self):
        """Feature handles edge cases gracefully."""
        result = my_function(edge_case_input)
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_async_operation(self):
        """Async operations work correctly."""
        result = await async_function()
        assert result is not None
```

### Test Fixtures

Use fixtures for common setup:

```python
@pytest.fixture
def mock_gateway_data():
    """Mock gateway status data."""
    return {
        "healthy": True,
        "context_pct": 50,
        "uptime_seconds": 3600,
    }

def test_with_mock_data(mock_gateway_data):
    result = process_gateway(mock_gateway_data)
    assert result["status"] == "online"
```

## Code Style

### Python Version

Target Python 3.10+. Use modern syntax:

```python
# Good
def process(items: list[str]) -> dict[str, Any]:
    match status:
        case "ok":
            return {"success": True}
        case _:
            return {"error": "Unknown status"}

# Avoid (Python 3.9 style)
def process(items: List[str]) -> Dict[str, Any]:
    ...
```

### Type Hints

All public functions should have type hints:

```python
def collect(include_secrets: bool = False) -> dict[str, Any]:
    """Collect data from source.

    Args:
        include_secrets: Whether to include sensitive data.

    Returns:
        Dictionary with collected data.
    """
```

### Docstrings

Use Google-style docstrings:

```python
def process_data(items: list[str], limit: int = 10) -> list[dict]:
    """Process a list of items.

    Args:
        items: List of item identifiers.
        limit: Maximum items to process.

    Returns:
        List of processed item dictionaries.

    Raises:
        ValueError: If items is empty.
    """
```

### Error Handling

Return errors in data dictionaries for collectors:

```python
def collect() -> dict[str, Any]:
    """Collect data, returning error dict on failure."""
    try:
        data = fetch_data()
        return {"items": data}
    except ConnectionError as e:
        return {"error": f"Network error: {e}"}
    except Exception as e:
        return {"error": str(e)}
```

### Formatting

Ruff handles formatting. Key settings (in `pyproject.toml`):

```toml
[tool.ruff]
line-length = 100
target-version = "py310"
```

## Pull Requests

### Before Submitting

- [ ] Tests pass: `pytest tests/ -v`
- [ ] Lint passes: `ruff check src/ tests/`
- [ ] Code is formatted: `ruff format src/ tests/`
- [ ] New features have tests
- [ ] Documentation updated if needed

### PR Description

Include:
- **What** — Brief description of changes
- **Why** — Motivation/context
- **How** — Implementation approach (if complex)
- **Testing** — How you tested the changes

### Review Process

1. Submit PR against `main`
2. CI runs tests and linting
3. Maintainer reviews code
4. Address feedback if needed
5. PR gets merged 🎉

### Commit Messages

#### Structured Commit Format (Recommended)

For better PR generation and automated tools, use the structured commit format:

```
feat(collector): add sparkline visualization to metrics panel

What: Display 7-day trend sparklines in the metrics dashboard
Why: Users need quick visual context for metric changes over time  
How: Added sparkline() function and historical data tracking
```

The structured format includes:
- **What**: One sentence describing what this commit does
- **Why**: What was broken, missing, or needed improvement
- **How**: Brief technical approach

#### Template Setup

Configure git to use the commit message template:

```bash
git config --local commit.template .gitmessage
```

This will pre-populate commit messages with the structured format.

#### Conventional Commits

Traditional format is also supported:

```
feat: add sparkline visualization to metrics panel

- Implement sparkline() function in ascii_art module
- Add historical data tracking to cost collector
- Display 7-day trend in metrics panel
```

Prefixes:
- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation
- `test:` — Test changes
- `refactor:` — Code refactoring
- `chore:` — Maintenance tasks

#### Benefits

The structured format enables:
- **Better PR descriptions**: `pr-describe.py` extracts What/Why/How directly
- **Clearer change intent**: Explicit motivation and approach
- **Improved maintainability**: Future developers understand the context

## Getting Help

### Questions?

- **GitHub Discussions** — General questions and ideas
- **GitHub Issues** — Bug reports and feature requests

### Reporting Issues

Include:
1. Steps to reproduce
2. Expected vs actual behavior
3. Python version (`python --version`)
4. OS and terminal
5. Error messages/traceback

### Feature Requests

Open an issue to discuss before implementing major features. This helps ensure:
- The feature aligns with project goals
- The approach is sound
- No duplicate effort

## Recognition

Contributors are appreciated! All contributions, big or small, help make this project better.

---

Thank you for contributing! 🙏
