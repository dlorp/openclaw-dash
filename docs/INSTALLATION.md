# Installation

hermes-dash installs from source. PyPI publication is planned but not yet available.

## Requirements

- Python 3.10+ (3.11 or 3.12 recommended)
- pip or pipx
- Git

Optional:
- Docker and Docker Compose
- gh CLI (for GitHub integration tools)

## From Source

```bash
git clone https://github.com/dlorp/hermes-dash.git
cd hermes-dash
pip install -e .
```

Editable mode means code changes take effect immediately.

## With pipx

```bash
git clone https://github.com/dlorp/hermes-dash.git
cd hermes-dash
pipx install -e .
```

pipx isolates the installation in its own environment. No dependency conflicts with other projects.

## With Docker

```bash
git clone https://github.com/dlorp/hermes-dash.git
cd hermes-dash
docker compose up -d
```

Mount your config:

```yaml
# docker-compose.yml
services:
  dashboard:
    build: .
    volumes:
      - ~/.config/hermes-dash:/config
    environment:
      - CONFIG_PATH=/config/config.yaml
```

## First Run

Create a minimal config:

```bash
mkdir -p ~/.config/hermes-dash
cat > ~/.config/hermes-dash/config.yaml << 'EOF'
plugins:
  - name: localhost
    type: ssh-agent
    host: localhost
    metrics: [cpu, memory, disk]

layout:
  rows:
    - panels:
        - title: System
          source: localhost
          chart: sparkline
EOF
```

Run:

```bash
hermes-dash
```

Or try the demo without config:

```bash
hermes-dash --demo
```

## Commands

```bash
# Launch TUI
hermes-dash

# Quick status (text output)
hermes-dash --status

# JSON output (for scripts)
hermes-dash --json

# Demo mode (mock data)
hermes-dash --demo

# Custom config
hermes-dash --config /path/to/config.yaml

# List installed plugins
hermes-dash --list-plugins

# Check version
hermes-dash --version
```

## Verification

```bash
# Check install
which hermes-dash
hermes-dash --version

# Test with demo
hermes-dash --demo

# Validate config
hermes-dash --config-check
```

## Troubleshooting

**"No plugins configured"**

Create config at `~/.config/hermes-dash/config.yaml`. See [Configuration](CONFIGURATION.md).

**"Connection refused" (SSH plugins)**

Ensure SSH key auth is set up and the target host is reachable:

```bash
ssh -i ~/.ssh/id_ed25519 user@host echo "ok"
```

**"Module not found"**

Reinstall in editable mode:

```bash
pip install -e .
```

**Color issues**

Check 256-color support:

```bash
echo -e "\e[38;5;208mOrange\e[0m"
```

If that shows orange, your terminal supports 256 colors. If not, try a different terminal emulator.

**Unicode box-drawing characters show as squares**

Your font may not support box-drawing characters. Try:
- A monospace font with good Unicode coverage (JetBrains Mono, Fira Code, Cascadia Code)
- Setting `TERM=xterm-256color` before running

## Uninstall

```bash
pip uninstall hermes-dash
```

Or if installed with pipx:

```bash
pipx uninstall hermes-dash
```
