# Development Guide

Guide for contributing to openclaw-dash: adding widgets, running tests, and following project conventions.

## Getting Started

### Prerequisites

- Python 3.10+
- Git
- A terminal with good Unicode/color support

### Setup

```bash
# Clone the repo
git clone https://github.com/dlorp/openclaw-dash.git
cd openclaw-dash

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install with dev dependencies
pip install -e ".[dev]"

# Verify everything works
pytest tests/ -v
openclaw-dash --help
```

## Project Structure

```
openclaw-dash/
├── src/openclaw_dash/
│   ├── __init__.py
│   ├── app.py              # Main TUI application
│   ├── cli.py              # CLI entry point
│   ├── config.py           # User configuration
│   ├── themes.py           # Theme definitions
│   ├── version.py          # Version info
│   ├── commands.py         # Command palette commands
│   ├── collectors/         # Data collection modules
│   │   ├── gateway.py      # Gateway status
│   │   ├── sessions.py     # Session data
│   │   ├── repos.py        # Repository health
│   │   ├── alerts.py       # Alert aggregation
│   │   └── ...
│   ├── widgets/            # UI components
│   │   ├── __init__.py     # Public exports
│   │   ├── ascii_art.py    # Visual primitives
│   │   ├── collapsible_panel.py
│   │   ├── resources.py    # System resources
│   │   ├── alerts.py       # Alerts panel
│   │   └── ...
│   ├── metrics/            # Metrics collection
│   │   ├── costs.py        # Token cost tracking
│   │   ├── performance.py  # API performance
│   │   └── github.py       # GitHub stats
│   ├── security/           # Security audit
│   │   ├── audit.py        # Config scanning
│   │   ├── deps.py         # Dependency checks
│   │   └── fixes.py        # Auto-fix logic
│   └── tools/              # Bundled automation tools
│       ├── repo-scanner.py
│       ├── pr-tracker.py
│       └── ...
├── tests/                  # Test suite
├── docs/                   # Documentation
├── pyproject.toml          # Project config
└── README.md
```

## Adding a New Widget

### 1. Create the Widget

Widgets are Textual `Static` or `Widget` subclasses that fetch and display data.

**`src/openclaw_dash/widgets/my_widget.py`:**

```python
"""My custom widget for the dashboard."""

from textual.app import ComposeResult
from textual.widgets import Static

from openclaw_dash.collectors import my_collector
from openclaw_dash.widgets.ascii_art import (
    progress_bar,
    status_indicator,
    separator,
)


class MyWidget(Static):
    """Custom widget that displays something cool."""

    def compose(self) -> ComposeResult:
        # Initial loading state
        yield Static("Loading...", id="my-widget-content")

    def refresh_data(self) -> None:
        """Fetch and display fresh data."""
        data = my_collector.collect()
        content = self.query_one("#my-widget-content", Static)

        if data.get("error"):
            content.update(f"{status_indicator('error')} {data['error']}")
            return

        # Build display
        lines = [
            f"{status_indicator('ok')} [bold]My Widget[/]",
            separator(20, "dotted"),
            f"Value: {data.get('value', 'N/A')}",
            progress_bar(data.get('progress', 0), width=15),
        ]
        content.update("\n".join(lines))
```

### 2. Create the Collector

Collectors fetch data from external sources (APIs, files, CLI tools).

**`src/openclaw_dash/collectors/my_collector.py`:**

```python
"""Data collector for my widget."""

from typing import Any


def collect() -> dict[str, Any]:
    """Collect data for the widget.

    Returns:
        Dict with widget data, or {"error": "message"} on failure.
    """
    try:
        # Fetch your data here
        # Examples: HTTP requests, file reads, CLI output parsing

        return {
            "value": 42,
            "progress": 0.75,
            "items": ["one", "two", "three"],
        }
    except Exception as e:
        return {"error": str(e)}
```

### 3. Add to Main App

**`src/openclaw_dash/app.py`:**

```python
# Import your widget
from openclaw_dash.widgets.my_widget import MyWidget

# Add to compose() method
with Container(id="my-widget-panel", classes="panel"):
    with Collapsible(
        title="🎯 My Widget",
        collapsed=False,
        collapsed_symbol="▸",
        expanded_symbol="▾",
        id="my-widget-panel-collapsible",
    ):
        yield MyWidget()

# Add to PANEL_ORDER for navigation
PANEL_ORDER = [
    # ... existing panels
    "my-widget-panel",
]

# Add to refresh methods
def _auto_refresh(self) -> None:
    # ... existing panels
    try:
        panel = self.query_one(MyWidget)
        panel.refresh_data()
    except Exception:
        pass
```

### 4. Add CSS Styling

In the `CSS` string in `app.py`:

```css
#my-widget-panel {
    column-span: 1;  /* Or 2, 3 for wider panels */
    row-span: 1;
}
```

### 5. Export in `__init__.py`

**`src/openclaw_dash/widgets/__init__.py`:**

```python
from openclaw_dash.widgets.my_widget import MyWidget

__all__ = [
    # ... existing exports
    "MyWidget",
]
```

### 6. Write Tests

**`tests/test_my_widget.py`:**

```python
"""Tests for MyWidget."""

import pytest

from openclaw_dash.collectors import my_collector


class TestMyCollector:
    """Tests for the data collector."""

    def test_collect_returns_dict(self):
        """Collector returns a dictionary."""
        result = my_collector.collect()
        assert isinstance(result, dict)

    def test_collect_has_expected_keys(self):
        """Collector returns expected data structure."""
        result = my_collector.collect()
        # Either has data or error
        assert "value" in result or "error" in result


class TestMyWidget:
    """Tests for the widget UI."""

    def test_widget_has_content_id(self):
        """Widget creates content element with correct ID."""
        from openclaw_dash.widgets.my_widget import MyWidget

        widget = MyWidget()
        # Test compose creates expected structure
        children = list(widget.compose())
        assert len(children) == 1
```

## Visual Primitives

Use the `ascii_art` module for consistent visuals:

```python
from openclaw_dash.widgets.ascii_art import (
    # Progress bars
    progress_bar,      # Full progress bar with optional %
    mini_bar,          # Compact bar (4-8 chars)

    # Status indicators
    status_indicator,  # Colored status with icon
    STATUS_SYMBOLS,    # Dict of unicode symbols

    # Layout
    separator,         # Horizontal line
    draw_box,          # Box drawing

    # Data visualization
    sparkline,         # Mini line chart
    trend_indicator,   # ↑/↓/→ arrows
    format_with_trend, # Value with trend arrow
)
```

### Examples

```python
# Progress bar (0.0 to 1.0)
progress_bar(0.75, width=15, show_percent=True)
# ████████████░░░ 75%

# Mini bar for compact displays
mini_bar(0.5, width=6)
# ███░░░

# Status indicator
status_indicator("ok", "Online")    # ✓ Online (green)
status_indicator("warning", "Slow") # ⚠ Slow (yellow)
status_indicator("error", "Down")   # ✗ Down (red)

# Sparkline from history
sparkline([1, 3, 5, 2, 4, 6, 3], width=7)
# ▁▃▅▂▄█▃

# Separator
separator(20, style="dotted")
# ····················

# Trend
trend_indicator(5)   # ↑ (green)
trend_indicator(-3)  # ↓ (red)
trend_indicator(0)   # → (dim)
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_config.py -v

# Run with coverage
pytest tests/ --cov=openclaw_dash --cov-report=html

# Run async tests
pytest tests/ -v --asyncio-mode=auto

# Run only fast tests (skip slow integration tests)
pytest tests/ -v -m "not slow"
```

### Test Patterns

```python
import pytest
from pathlib import Path

# Use fixtures for temporary files
@pytest.fixture
def temp_config_path(tmp_path: Path) -> Path:
    return tmp_path / "config.toml"

# Test with mocked data
def test_with_mock(mocker):
    mocker.patch(
        "openclaw_dash.collectors.gateway.collect",
        return_value={"healthy": True, "context_pct": 50}
    )
    # Test code that uses the collector

# Async tests
@pytest.mark.asyncio
async def test_async_operation():
    result = await some_async_function()
    assert result is not None
```

## Linting and Formatting

```bash
# Check for issues
ruff check src/ tests/

# Auto-fix issues
ruff check src/ tests/ --fix

# Format code
ruff format src/ tests/

# Type checking
mypy src/
```

### Ruff Configuration

The project uses these ruff settings (in `pyproject.toml`):

```toml
[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "W", "UP"]
```

## Code Style Guidelines

### Type Hints

Use type hints for all public functions:

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

Return errors in data dictionaries rather than raising exceptions in collectors:

```python
def collect() -> dict[str, Any]:
    try:
        # ... fetch data
        return {"data": result}
    except requests.RequestException as e:
        return {"error": f"Network error: {e}"}
    except Exception as e:
        return {"error": str(e)}
```

## Creating a New Theme

Add to `src/openclaw_dash/themes.py`:

```python
from textual.theme import Theme

MY_THEME = Theme(
    name="mytheme",
    primary="#...",      # Main accent color
    secondary="#...",    # Secondary accent
    accent="#...",       # Highlights
    foreground="#...",   # Text color
    background="#...",   # Background
    surface="#...",      # Panel backgrounds
    panel="#...",        # Panel borders
    success="#...",      # Success states
    warning="#...",      # Warning states
    error="#...",        # Error states
    dark=True,           # True for dark themes
)

# Add to theme list
THEMES = [DARK_THEME, LIGHT_THEME, HACKER_THEME, MY_THEME]
THEME_NAMES = [t.name for t in THEMES]
```

## Pull Request Checklist

Before submitting a PR:

- [ ] Tests pass: `pytest tests/ -v`
- [ ] Linting passes: `ruff check src/ tests/`
- [ ] Code is formatted: `ruff format src/ tests/`
- [ ] New features have tests
- [ ] Documentation updated if needed
- [ ] Commit messages are clear

## Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Open a GitHub Issue with reproduction steps
- **Features**: Open an Issue to discuss before implementing

## Next Steps

- [Widgets Reference](WIDGETS.md) — See all existing widgets
- [Configuration](CONFIGURATION.md) — Understand user config
- [Contributing Guidelines](../CONTRIBUTING.md) — Project contribution rules
