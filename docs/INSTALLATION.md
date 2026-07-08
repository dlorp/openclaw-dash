# Installation Guide

All installation methods require cloning from source. This package is not yet published to PyPI.

## Prerequisites

- Python 3.10+ (3.11 or 3.12 recommended)
- pip or pipx
- Git

Optional:
- Docker and Docker Compose (for containerized deployment)
- gh CLI (for GitHub integration features)

## From Source

```bash
git clone https://github.com/dlorp/openclaw-dash.git
cd openclaw-dash
pip install -e .
```

This installs openclaw-dash in editable mode. Changes to the source code take effect immediately.

## With pipx

```bash
git clone https://github.com/dlorp/openclaw-dash.git
cd openclaw-dash
pipx install -e .
```

pipx isolates the installation in a virtual environment, avoiding dependency conflicts.

## With Docker

```bash
git clone https://github.com/dlorp/openclaw-dash.git
cd openclaw-dash
docker compose up -d
```

The Docker setup includes all dependencies and runs the dashboard in a container. Mount your config file:

```yaml
# docker-compose.yml
services:
  dashboard:
    volumes:
      - ~/.config/openclaw-dash:/config
    ports:
      - "18789:18789"
```

## Configuration

After installation, create a config file:

```bash
mkdir -p ~/.config/openclaw-dash
cat > ~/.config/openclaw-dash/config.yaml << 'EOF'
plugins:
  - name: system
    type: ssh-agent
    host: localhost
    metrics: [cpu, memory, disk]

  - name: api
    type: http-api
    url: https://api.example.com/health
    interval: 30s
EOF
```

See [Configuration](CONFIGURATION.md) for all options.

## Running

```bash
# Launch the TUI
openclaw-dash

# Quick status check
openclaw-dash --status

# JSON output (for scripting)
openclaw-dash --json

# Demo mode (no plugins required)
openclaw-dash --demo
```

## Verifying Installation

```bash
# Check version
openclaw-dash --version

# Run with demo data
openclaw-dash --demo

# Check plugin registry
openclaw-dash --list-plugins
```

## Troubleshooting

### "No plugins configured"

Create a config file at `~/.config/openclaw-dash/config.yaml`. See [Configuration](CONFIGURATION.md).

### "Connection refused"

If using SSH plugins, ensure SSH access is configured and the target host is reachable.

### "Module not found"

Reinstall in editable mode: `pip install -e .`

### Color issues

Ensure your terminal supports 256 colors. Test with: `echo -e "\e[38;5;208mOrange\e[0m"`
