# Usage

## Basic Commands

```bash
openclaw-dash              # Launch TUI dashboard
openclaw-dash --status     # Quick text status
openclaw-dash --json       # JSON output for scripting
```

## Security Commands

```bash
openclaw-dash security              # Run security audit
openclaw-dash security --deep       # Full vulnerability scan
openclaw-dash security --fix        # Auto-fix issues
```

## Metrics

```bash
openclaw-dash metrics               # View metrics
```

## Automation

```bash
openclaw-dash auto merge            # Auto-merge approved PRs
openclaw-dash auto cleanup          # Clean stale branches
```

## TUI Dashboard

When you run `openclaw-dash` without arguments, the full TUI dashboard launches.

### Panels

- **Gateway** — Shows OpenClaw gateway status (online/offline), context usage percentage, and uptime
- **Current Task** — Displays what your agent is currently working on
- **Repos** — Repository health at a glance with PR counts and status indicators
- **Activity** — Recent actions with timestamps
- **Sessions** — Active agent sessions and their context burn rate
- **Cron** — Scheduled tasks and their status/next run time
- **Alerts** — Color-coded alerts from various sources
- **Channels** — Connected messaging channels (Discord, Slack, etc.)
- **System Resources** — CPU, memory, disk, network (toggleable with `x`)

### Keyboard Shortcuts

#### Global Actions
| Key | Action |
|-----|--------|
| `q` | Quit application |
| `r` | Refresh all panels |
| `t` | Cycle theme (dark/light/phosphor) |
| `h` / `?` | Show help panel |
| `s` | Open settings screen |
| `Ctrl+P` | Open command palette |

#### Navigation
| Key | Action |
|-----|--------|
| `Tab` / `Shift+Tab` | Navigate to next/previous panel |
| `f` / `/` | Enter jump mode (show panel labels) |
| `j` / `k` | Scroll down/up (Vim-style) |
| `G` | Jump to end of panel |
| `Home` | Jump to top of panel |

#### Panel Focus Shortcuts
| Key | Panel |
|-----|-------|
| `g` | Gateway |
| `m` | Metrics |
| `a` | Alerts |
| `c` | Cron |
| `p` | Repos |
| `l` | Logs |
| `n` | Agents |

#### Panel Management
| Key | Action |
|-----|--------|
| `Enter` | Toggle focused panel collapse/expand |
| `Ctrl+[` | Collapse all panels |
| `Ctrl+]` | Expand all panels |
| `x` | Toggle resources panel visibility |

#### Tab Groups
| Key | Action |
|-----|--------|
| `1` | Focus Runtime tab group (Sessions/Agents/Cron/Channels) |
| `2` | Focus Code tab group (Repos/Activity) |
| `[` | Previous tab in focused group |
| `]` | Next tab in focused group |

#### Input
| Key | Action |
|-----|--------|
| `:` / `i` | Focus command input pane |

## JSON Output

For scripting and automation, use `--json` to get machine-readable output:

```bash
openclaw-dash --json | jq '.gateway.status'
```

---

See also: [Integrated Tools](Integrated-Tools.md)
