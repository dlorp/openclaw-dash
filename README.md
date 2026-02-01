# openclaw-dash

TUI dashboard for monitoring your [OpenClaw](https://github.com/openclaw/openclaw) ecosystem at a glance.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  OPENCLAW DASHBOARD                                       14:32 PST    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─ GATEWAY ─────┐  ┌─ CURRENT TASK ──────────────────────────────────┐ │
│  │   ✓ ONLINE    │  │  Building new feature for project-x            │ │
│  │   ctx: 24%    │  │  > Implementing auth module                    │ │
│  │   2h uptime   │  │  > Writing tests                               │ │
│  └───────────────┘  └─────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─ REPOS ──────────────────────┐  ┌─ ACTIVITY ─────────────────────┐  │
│  │  my-project      ✨  0 PRs   │  │  ▸ 14:30 Pushed feature branch │  │
│  │  another-repo    🟢  2 PRs   │  │  ▸ 14:00 Reviewed PR #42       │  │
│  │  side-project    🟡  5 PRs   │  │  ▸ 13:30 Fixed CI pipeline     │  │
│  └──────────────────────────────┘  └─────────────────────────────────┘  │
│                                                                         │
│  ┌─ SESSIONS ───────────────────┐  ┌─ CRON ─────────────────────────┐  │
│  │  ● main         [45%]        │  │  daily-summary    04:00 ✓      │  │
│  │  ○ sub-agent-1  [12%]        │  │  backup-check     hourly       │  │
│  │  ○ sub-agent-2  [8%]         │  │  dep-update       weekly       │  │
│  └──────────────────────────────┘  └─────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Features

- **Gateway Status** — Health, context usage, uptime
- **Current Task** — Track what your agent is working on
- **Repository Health** — PRs, CI status, TODO counts
- **Activity Log** — Recent actions with timestamps
- **Sessions** — Active sessions and context burn rate
- **Cron Jobs** — Scheduled tasks and status
- **Security Audit** — Config scanning, dependency vulnerabilities *(coming soon)*
- **Metrics** — Cost tracking, performance stats *(coming soon)*

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

### Commands (coming soon)

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

Custom config coming soon.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT — see [LICENSE](LICENSE)
