# openclaw-dash

TUI dashboard for monitoring your [OpenClaw](https://github.com/openclaw/openclaw) ecosystem at a glance.

![Dashboard Screenshot](docs/images/dashboard.svg)

<details>
<summary>ASCII Preview</summary>

```
┌─────────────────────────────────────────────────────────────────────────┐
│  OPENCLAW DASHBOARD                                       14:32 PST     │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐            │
│  │ ✓ GATEWAY  │ │ $0.42/day  │ │ 0.2% err   │ │ 🔥 12 days │            │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘            │
├─────────────────────────────────────────────────────────────────────────┤
│ [a]─ GATEWAY ─────  [b]─ CURRENT TASK ─────────────────────────────── ▼ │
│ │   ✓ ONLINE       │  Building new feature for project-x               │
│ │   ctx: 24%       │  > Implementing auth module                       │
│ │   2h uptime      │  > Writing tests                                  │
│                                                                         │
│ [c]─ REPOS ─────────────────────  [d]─ ACTIVITY ─────────────────────── │
│ │  my-project      ✨  0 PRs     │  ▸ 14:30 Pushed feature branch       │
│ │  another-repo    🟢  2 PRs     │  ▸ 14:00 Reviewed PR #42             │
│ │  side-project    🟡  5 PRs     │  ▸ 13:30 Fixed CI pipeline           │
│                                                                         │
│ ━━━ SESSIONS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ │ [Sessions] [Cron] [Channels]                                          │
│ │  ● main         [████████░░] 45%                                      │
│ │  ○ sub-agent-1  [█░░░░░░░░░] 12%                                      │
│ │  ○ sub-agent-2  [░░░░░░░░░░]  8%                                      │
│                                                                         │
│ [h] Help  [f] Jump  [t] Theme  [Ctrl+P] Command Palette  [q] Quit       │
└─────────────────────────────────────────────────────────────────────────┘

Jump Mode: Press 'f' then letter to focus panel    Tabs: Switch with Tab key
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
- **Themes** — Cycle through dark/light/hacker themes with `t`
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

## Requirements

- Python 3.10+
- [OpenClaw](https://github.com/openclaw/openclaw) gateway running
- `gh` CLI (for GitHub integration)

## Configuration

The dashboard auto-discovers:
- OpenClaw gateway at `localhost:3000`
- Repositories in `~/repos/`
- Workspace at `~/.openclaw/workspace/`

User preferences are saved to `~/.config/openclaw-dash/config.toml`:

```toml
theme = "dark"              # dark, light, or hacker
refresh_interval = 30       # seconds between auto-refresh
show_resources = true       # show system resources panel
show_notifications = true   # show toast notifications
collapsed_panels = []       # panels to start collapsed
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[PolyForm NonCommercial 1.0.0](LICENSE) — free for personal and non-commercial use
