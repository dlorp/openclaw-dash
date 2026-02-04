# openclaw-dash

![Version](https://img.shields.io/badge/version-0.3.0-blue)
[![License](https://img.shields.io/badge/license-PolyForm%20NC%201.0.0-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org/)
[![CI](https://img.shields.io/github/actions/workflow/status/dlorp/openclaw-dash/ci.yml?label=CI)](https://github.com/dlorp/openclaw-dash/actions)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey)](https://github.com/dlorp/openclaw-dash)

TUI dashboard for monitoring your [OpenClaw](https://github.com/openclaw/openclaw) ecosystem at a glance.


![Dashboard Screenshot](docs/images/dashboard.svg)
<!-- Real screenshots coming soon — expect warm amber (#FB8B24) glow on dark backgrounds -->

<details>
<summary>ASCII Preview</summary>

```
╭─────────────────────────────────────────────────────────────────────────╮
│  █▀█ █▀█ █▀▀ █▄ █ █▀▀ █   ▄▀█ █ █ █  ░░░░░░░░▓▓▓▓▓▓    14:32 PST    │
│  █▄█ █▀▀ ██▄ █ ▀█ █▄▄ █▄▄ █▀█ ▀▄▀▄▀  DASHBOARD         ◉ PHOSPHOR    │
├─────────────────────────────────────────────────────────────────────────┤
│  ╭────────────╮ ╭────────────╮ ╭────────────╮ ╭────────────╮            │
│  │ ● GATEWAY  │ │ $0.42/day  │ │ 0.2% ░░░░░ │ │ 🔥 12 days │            │
│  ╰────────────╯ ╰────────────╯ ╰────────────╯ ╰────────────╯            │
├─────────────────────────────────────────────────────────────────────────┤
│ [a]─ GATEWAY ──────╮ [b]─ CURRENT TASK ──────────────────────────────╮  │
│ │   ● ONLINE       │ │  Building new feature for project-x          │  │
│ │   ctx: ▓▓░░ 24%  │ │  › Implementing auth module                   │  │
│ │   2h uptime      │ │  › Writing tests                              │  │
│ ╰──────────────────╯ ╰───────────────────────────────────────────────╯  │
│                                                                         │
│ [c]─ REPOS ─────────────────────╮ [d]─ ACTIVITY ─────────────────────╮  │
│ │  my-project      ✨  0 PRs    │ │  ▸ 14:30 Pushed feature branch   │  │
│ │  another-repo    ●   2 PRs    │ │  ▸ 14:00 Reviewed PR #42         │  │
│ │  side-project    ◐   5 PRs    │ │  ▸ 13:30 Fixed CI pipeline       │  │
│ ╰───────────────────────────────╯ ╰──────────────────────────────────╯  │
│                                                                         │
│ ━━━ SESSIONS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  ● main         [▓▓▓▓▓▓▓▓░░] 45%                                        │
│  ○ sub-agent-1  [▓░░░░░░░░░] 12%                                        │
│  ○ sub-agent-2  [░░░░░░░░░░]  8%                                        │
│                                                                         │
│ [h] Help  [f] Jump  [t] Theme  [Ctrl+P] Palette                [q] Quit │
╰─────────────────────────────────────────────────────────────────────────╯
```

</details>

## Features

### Panels
- **Gateway Status** — Health, context usage, uptime
- **Current Task** — Track what your agent is working on
- **Repository Health** — PRs, CI status, TODO counts
- **Activity Log** — Recent actions with timestamps
- **Sessions** — Active sessions and context burn rate
- **Cron Jobs** — Scheduled tasks and status
- **Alerts** — Color-coded severity alerts from all sources
- **Channels** — Connected messaging channels and status
- **Agents** — Sub-agent coordination view with status, context usage, and task summaries
- **Security Audit** — Config scanning, dependency vulnerabilities
- **Metrics** — Cost tracking, performance stats, GitHub streak
- **System Resources** — CPU, memory, disk, and network I/O (toggleable with `x`)
- **Logs** — Real-time gateway log viewer

### UI Features
- **Metric Boxes** — Compact KPI bar showing gateway status, cost, error rate, and streak
- **Collapsible Panels** — Collapse/expand any panel with `Enter`, or all with `Ctrl+[`/`Ctrl+]`
- **Jump Mode** — Press `f` to show letter labels, then press a letter to jump to that panel
- **Vim Navigation** — `j`/`k` to scroll, `G` for end, `Home` for top
- **Command Palette** — `Ctrl+P` for quick access to all commands
- **Themes** — Cycle through dark/light/phosphor themes with `t` (amber glow!)
- **Responsive Layout** — Adapts to terminal size, hides less-critical panels when narrow

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `q` | Quit |
| `r` | Refresh all panels |
| `t` | Cycle theme |
| `h` / `?` | Help panel |
| `Ctrl+P` | Command palette |
| `j` / `k` | Scroll down/up |
| `G` / `Home` | Jump to end/top |
| `Tab` / `Shift+Tab` | Next/previous panel |
| `f` / `/` | Enter jump mode |
| `Enter` | Toggle panel collapse |
| `Ctrl+[` / `Ctrl+]` | Collapse/expand all |
| `x` | Toggle resources panel |
| `g` `s` `m` `a` `c` `p` `l` | Focus specific panels |

## Installation

```bash
pip install openclaw-dash
```

Or from source:

```bash
git clone https://github.com/dlorp/openclaw-dash.git
cd openclaw-dash
pip install -e .
```

## Usage

```bash
openclaw-dash              # Launch TUI dashboard
openclaw-dash --status     # Quick text status
openclaw-dash --json       # JSON output for scripting
```

### Commands

```bash
openclaw-dash security              # Run security audit
openclaw-dash security --deep       # Full vulnerability scan
openclaw-dash security --fix        # Auto-fix issues

openclaw-dash metrics               # View metrics
openclaw-dash auto merge            # Auto-merge approved PRs
openclaw-dash auto cleanup          # Clean stale branches
```

## Integrated Tools

Bundled automation tools:

| Tool | Description |
|------|-------------|
| `repo-scanner` | Repository health metrics (TODOs, tests, PRs) |
| `pr-tracker` | PR status monitoring and merge detection |
| `smart-todo-scanner` | Context-aware TODO categorization |
| `dep-shepherd` | Dependency auditing and updates |
| `pr-describe` | Automated PR description generation |
| `pr-create` | Streamlined PR creation with auto-generated content |
| `audit` | Security scanning (secrets, vulnerabilities, dangerous patterns) |
| `version-bump` | Semantic version management based on conventional commits |

## Requirements

- Python 3.10+
- [OpenClaw](https://github.com/openclaw/openclaw) gateway running
- `gh` CLI (for GitHub integration)

## Configuration

The dashboard auto-discovers:
- OpenClaw gateway at `localhost:18789`
- Repositories in `~/repos/`
- Workspace at `~/.openclaw/workspace/`

User preferences are saved to `~/.config/openclaw-dash/config.toml`:

```toml
theme = "dark"              # dark, light, or phosphor (amber CRT aesthetic)
refresh_interval = 30       # seconds between auto-refresh
show_resources = true       # show system resources panel
show_notifications = true   # show toast notifications
collapsed_panels = []       # panels to start collapsed
```

## Documentation

Comprehensive guides in the `docs/` folder:

- **[Installation Guide](docs/INSTALLATION.md)** — Detailed install guide (pip, source, dev setup)
- **[Configuration](docs/CONFIGURATION.md)** — Config options, themes, and demo mode
- **[Widgets Reference](docs/WIDGETS.md)** — Every panel explained with examples
- **[Development Guide](docs/DEVELOPMENT.md)** — Add widgets, run tests, contribute
- **[Design Audit](docs/DESIGN_AUDIT.md)** — Brand colors, aesthetic guidelines, phosphor theme spec

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[PolyForm NonCommercial 1.0.0](LICENSE) — free for personal and non-commercial use
