# Development

How to write plugins, run tests, and contribute to openclaw-dash.

## Setup

```bash
git clone https://github.com/dlorp/openclaw-dash.git
cd openclaw-dash
pip install -e ".[dev]"
pytest
```

The `[dev]` extra installs: pytest, pytest-cov, ruff, mypy.

## Writing a Plugin

Plugins are the extension mechanism. Any class implementing the plugin interface becomes a data source.

### The Interface

```python
from openclaw_dash.plugins import DataSourcePlugin, Metric

class MyPlugin(DataSourcePlugin):
    """Example plugin collecting custom metrics."""

    def acquire(self) -> dict:
        """Fetch raw data from your source."""
        response = requests.get(
            "https://api.example.com/metrics",
            timeout=5
        )
        response.raise_for_status()
        return response.json()

    def parse(self, raw: dict) -> list[Metric]:
        """Convert to structured metrics."""
        return [
            Metric(
                name="requests_per_second",
                value=raw["rps"],
                unit="req/s",
                timestamp=time.time(),
            ),
            Metric(
                name="error_rate",
                value=raw["error_pct"],
                unit="%",
                timestamp=time.time(),
            ),
        ]

    def push(self, metrics: list[Metric]) -> None:
        """Send to collector. Base class handles this."""
        super().push(metrics)
```

### Registration

Add your plugin to the registry:

```python
# src/openclaw_dash/plugins/__init__.py
from .my_plugin import MyPlugin

PLUGIN_REGISTRY = {
    "ssh-agent": SSHAgentPlugin,
    "http-api": HTTPAPIPlugin,
    "db-health": DBHealthPlugin,
    "business-api": BusinessAPIPlugin,
    "my-plugin": MyPlugin,  # Add here
}
```

### Configuration

Plugins receive their config section from YAML:

```yaml
plugins:
  - name: my-service
    type: my-plugin
    api_url: https://api.example.com
    api_key: ${MY_API_KEY}
    interval: 30s
```

Access in your plugin:

```python
class MyPlugin(DataSourcePlugin):
    def __init__(self, config: dict):
        self.api_url = config["api_url"]
        self.api_key = os.environ.get(
            config.get("api_key_env", ""), ""
        )
```

### Error Handling

Handle errors gracefully. Return empty data on failure; the collector retries:

```python
def acquire(self) -> dict:
    try:
        response = requests.get(
            self.api_url,
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.warning(f"Plugin {self.name} failed: {e}")
        return {}
```

## Running Tests

```bash
# Full suite
pytest

# With coverage
pytest --cov=openclaw_dash

# Specific file
pytest tests/test_collectors.py

# Verbose
pytest -v

# Fail fast
pytest -x
```

## Code Conventions

- **Linting:** Ruff (configured in pyproject.toml)
- **Types:** Required for new code
- **Docstrings:** Required for public functions
- **Tests:** Required for new plugins

Run checks:

```bash
ruff check src/
ruff format --check src/
mypy src/openclaw_dash
```

## Adding a Widget

1. Create `src/openclaw_dash/widgets/my_widget.py`
2. Implement the widget interface (see existing widgets)
3. Register in `src/openclaw_dash/widgets/__init__.py`
4. Add chart type to layout parser
5. Write tests

Widget interface:

```python
from textual.widgets import Static

class MyWidget(Static):
    """Custom panel type."""

    def __init__(self, config: dict, collector: Collector):
        self.config = config
        self.collector = collector
        super().__init__()

    def on_mount(self):
        """Subscribe to collector updates."""
        self.collector.subscribe(self.update)

    def update(self, metrics: list[Metric]):
        """Render new data."""
        self.update(self.render(metrics))

    def render(self, metrics: list[Metric]) -> RenderableType:
        """Return Rich renderable."""
        return Panel("Hello")
```

## Directory Structure

```
src/openclaw_dash/
├── plugins/           # Data source plugins
├── collectors/        # Metric collectors
├── widgets/           # UI widgets
├── tools/             # Standalone utilities
├── services/          # External service clients
├── metrics/           # Metric type definitions
├── security/          # Security audit tools
├── app.py             # Main TUI application
├── cli.py             # CLI entry point
├── config.py          # Configuration loader
└── themes.py          # Theme definitions
```

## Why These Choices

**Textual for TUI**
Modern, maintained, good terminal support. Reactive system fits the dashboard model.

**Three-method plugin interface**
Small surface area. Easy to implement. Separates fetching, parsing, and pushing concerns.

**YAML configuration**
Human-readable. No code changes for common customizations.

**No external dependencies for core**
Keep the dashboard lightweight. Optional dependencies for specific plugins only.

## Submitting Changes

1. Fork and branch
2. Write tests for new features
3. Run the test suite
4. Submit PR with clear description

Issues and feature requests welcome. Plugin ideas especially welcome - if you need a data source, others probably do too.
