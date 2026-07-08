# Development Guide

How to contribute to openclaw-dash: writing plugins, running tests, and following project conventions.

## Getting Started

```bash
git clone https://github.com/dlorp/openclaw-dash.git
cd openclaw-dash
pip install -e ".[dev]"
pytest
```

## Writing a Plugin

Plugins are the core extensibility mechanism. Any Python class that implements the plugin interface becomes a data source.

### Plugin Interface

```python
from openclaw_dash.plugins import DataSourcePlugin, Metric

class MyPlugin(DataSourcePlugin):
    """Example plugin that collects custom metrics."""

    def acquire(self) -> dict:
        """Fetch raw data from your source."""
        # Call API, SSH, read file, whatever
        response = requests.get("https://api.example.com/metrics")
        return response.json()

    def parse(self, raw: dict) -> list[Metric]:
        """Convert raw data to structured metrics."""
        return [
            Metric(
                name="requests_per_second",
                value=raw["rps"],
                unit="req/s",
                timestamp=time.time(),
            ),
            Metric(
                name="error_rate",
                value=raw["errors"],
                unit="%",
                timestamp=time.time(),
            ),
        ]
```

### Plugin Registration

Drop your plugin in `src/openclaw_dash/plugins/` and register it:

```python
# src/openclaw_dash/plugins/__init__.py
from .my_plugin import MyPlugin

PLUGIN_REGISTRY = {
    "ssh-agent": SSHAgentPlugin,
    "http-api": HTTPAPIPlugin,
    "db-health": DBHealthPlugin,
    "business-api": BusinessAPIPlugin,
    "my-plugin": MyPlugin,  # Add yours here
}
```

### Plugin Config

Plugins receive their config section from `config.yaml`:

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
        self.api_key = os.environ.get(config.get("api_key_env", ""), "")
```

### Error Handling

Plugins should handle errors gracefully. The collector will retry on failure:

```python
def acquire(self) -> dict:
    try:
        response = requests.get(self.api_url, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.warning(f"Plugin {self.name} acquire failed: {e}")
        return {}  # Return empty, collector handles retry
```

## Running Tests

```bash
# Full suite
pytest

# With coverage
pytest --cov=openclaw_dash

# Specific test file
pytest tests/test_collectors.py

# Verbose output
pytest -v
```

## Project Conventions

- **Linting**: Ruff (not Black/flake8)
- **Type hints**: Required for new code
- **Docstrings**: Required for public functions
- **Tests**: Required for new plugins and features
- **Commits**: Descriptive messages, no AI attribution

## Directory Structure

```
src/openclaw_dash/
├── plugins/           # Data source plugins (add yours here)
├── collectors/        # Metric collectors
├── widgets/           # UI widgets
├── tools/             # Standalone utilities
├── services/          # External service clients
├── metrics/           # Metric definitions
├── security/          # Security audit tools
├── app.py             # Main TUI application
├── cli.py             # CLI entry point
├── config.py          # Configuration loader
└── themes.py          # Theme definitions
```

## Adding a Widget Type

1. Create `src/openclaw_dash/widgets/my_widget.py`
2. Implement the widget interface (see existing widgets for reference)
3. Register in `src/openclaw_dash/widgets/__init__.py`
4. Add chart type to layout config parser
5. Write tests

## Architecture Decisions

- **Textual for TUI**: Modern, well-maintained, good terminal support
- **Plugin interface**: Three functions (acquire/parse/push) keep plugins simple
- **YAML config**: Human-readable, no code changes for common customizations
- **WebSocket/SSE**: Real-time updates without page refreshes
