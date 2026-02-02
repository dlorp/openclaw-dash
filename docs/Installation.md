# Installation

## From PyPI

```bash
pip install openclaw-dash
```

## From Source

```bash
git clone https://github.com/dlorp/openclaw-dash.git
cd openclaw-dash
pip install -e .
```

## Development Installation

If you want to contribute or modify the code:

```bash
git clone https://github.com/dlorp/openclaw-dash.git
cd openclaw-dash
pip install -e ".[dev]"
```

This installs additional development dependencies for testing and linting.

## Prerequisites

Before using openclaw-dash, ensure you have:

1. **Python 3.10+** installed
2. **OpenClaw gateway** running (usually at `localhost:3000`)
3. **GitHub CLI (`gh`)** installed and authenticated for GitHub features

## Verification

After installation, verify it works:

```bash
openclaw-dash --version
openclaw-dash --status
```

## Configuration

The dashboard auto-discovers:

| Setting | Default Location |
|---------|------------------|
| OpenClaw gateway | `localhost:3000` |
| Repositories | `~/repos/` |
| Workspace | `~/.openclaw/workspace/` |

User preferences are saved to `~/.config/openclaw-dash/config.toml`.

---

Next: [Usage](Usage.md)
