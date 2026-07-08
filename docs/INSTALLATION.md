# Installation

openclaw-dash installs from source. PyPI publication is planned but not yet available.

## Requirements

- Python 3.10+ (3.11 or 3.12 recommended)
- pip or pipx
- Git

Optional:
- Docker and Docker Compose
- gh CLI (for GitHub integration tools)

## From Source

```bash
git clone https://github.com/dlorp/openclaw-dash.git
cd openclaw-dash
pip install -e .
```

Editable mode means code changes take effect immediately.

## With pipx

```bash
git clone https://github.com/dlorp/openclaw-dash.git
cd openclaw-dash
pipx install -e .
```

pipx isolates the installation in its own environment. No dependency conflicts with other projects.

## With Docker

```bash
git clone https://github.com/dlorp/openclaw-dash.git
cd openclaw-dash
docker compose up -d
```

Mount your config:

```yaml
# docker-compose.yml
services:
  dashboard:
    build: .
    volumes:
      - ~/.config/openclaw-dash:/config
    environment:
      - CONFIG_PATH=/config/config.yaml
```

## First Run

Create a minimal config:

```bash
mkdir -p ~/.config/openclaw-dash
cat > ~/.config/openclaw-dash/config.yaml << 'EOF'
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
openclaw-dash
```

Or try the demo without config:

```bash
openclaw-dash --demo
```

## Commands

```bash
# Launch TUI
openclaw-dash

# Quick status (text output)
openclaw-dash --status

# JSON output (for scripts)
openclaw-dash --json

# Demo mode (mock data)
openclaw-dash --demo

# Custom config
openclaw-dash --config /path/to/config.yaml

# List installed plugins
openclaw-dash --list-plugins

# Check version
openclaw-dash --version
```

## Verification

```bash
# Check install
which openclaw-dash
openclaw-dash --version

# Test with demo
openclaw-dash --demo

# Validate config
openclaw-dash --config-check
```

## Troubleshooting

**"No plugins configured"**

Create config at `~/.config/openclaw-dash/config.yaml`. See [Configuration](CONFIGURATION.md).

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
pip uninstall openclaw-dash
```

Or if installed with pipx:

```bash
pipx uninstall openclaw-dash
```
