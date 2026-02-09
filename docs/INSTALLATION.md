# Installation Guide

This guide covers all methods to install openclaw-dash from source.

**Note**: This package is not yet published to PyPI. All installation methods require cloning from source.

## Quick Install (Recommended)

```bash
git clone https://github.com/dlorp/openclaw-dash.git
cd openclaw-dash
pip install -e .
```

That's it! Run with:

```bash
openclaw-dash
```

## Requirements

- **Python 3.10+** (3.11 or 3.12 recommended)
- **OpenClaw gateway** running (optional but recommended)
- **gh CLI** (for GitHub integration features)

### Checking Your Python Version

```bash
python --version
# Should show Python 3.10.x or higher
```

If you need to upgrade Python, use [pyenv](https://github.com/pyenv/pyenv) or your system package manager.

## Installation Methods

### From Source (Standard Install)

```bash
# Clone the repo
git clone https://github.com/dlorp/openclaw-dash.git
cd openclaw-dash

# Install in editable mode
pip install -e .

# Or with dev dependencies (for contributors)
pip install -e ".[dev]"
```

### Using Virtual Environment (Recommended)

Using a virtual environment keeps dependencies isolated:

```bash
# Clone the repo
git clone https://github.com/dlorp/openclaw-dash.git
cd openclaw-dash

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install
pip install -e .
```

## Development Setup

Full setup for contributing or local development:

```bash
# 1. Clone and enter repo
git clone https://github.com/dlorp/openclaw-dash.git
cd openclaw-dash

# 2. Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install with dev dependencies
pip install -e ".[dev]"

# 4. Verify installation
openclaw-dash --help
pytest tests/ -v  # Run tests
```

### Dev Dependencies

Installing with `[dev]` adds:

| Package | Purpose |
|---------|---------|
| `pytest` | Test framework |
| `pytest-asyncio` | Async test support |
| `pytest-cov` | Coverage reporting |
| `ruff` | Linting and formatting |
| `mypy` | Static type checking |

## Verifying Installation

```bash
# Check version
openclaw-dash --version

# Quick status check (no TUI)
openclaw-dash --status

# Launch dashboard
openclaw-dash
```

## Common Issues

### "command not found: openclaw-dash"

Your Python scripts directory isn't in PATH. Fix:

```bash
# Find where pip installed it
pip show openclaw-dash | grep Location

# Add to PATH (add to your ~/.bashrc or ~/.zshrc)
export PATH="$HOME/.local/bin:$PATH"
```

### "No module named 'textual'"

Dependencies didn't install correctly. Reinstall from the project directory:

```bash
cd openclaw-dash
pip install -e . --force-reinstall
```

### TUI doesn't display correctly

Your terminal may not support the required features:

1. Use a modern terminal (iTerm2, Alacritty, Windows Terminal, Kitty)
2. Ensure UTF-8 encoding: `export LANG=en_US.UTF-8`
3. Try a different terminal theme

### psutil errors on macOS

```bash
# Install Xcode command line tools
xcode-select --install

# Reinstall
pip install --force-reinstall psutil
```

## Optional: OpenClaw Gateway

For full functionality, run the OpenClaw gateway:

```bash
# Start gateway
openclaw gateway start

# Verify it's running
openclaw gateway status
```

The dashboard auto-discovers the gateway at `localhost:3000`. See the [OpenClaw docs](https://github.com/openclaw/openclaw) for gateway setup.

## Optional: GitHub CLI

For repository and PR tracking:

```bash
# Install gh CLI
# macOS
brew install gh

# Ubuntu/Debian
sudo apt install gh

# Authenticate
gh auth login
```

## Uninstalling

```bash
# Uninstall the package
pip uninstall openclaw-dash

# Config cleanup (optional)
rm -rf ~/.config/openclaw-dash
```

## Next Steps

- **[Configuration](CONFIGURATION.md)** — Customize themes, refresh rates, and panel visibility
- **[Widgets](WIDGETS.md)** — Learn what each panel displays
- **[Development](DEVELOPMENT.md)** — Contribute to the project
- **[Usage](../README.md#usage)** — Keyboard shortcuts and commands
