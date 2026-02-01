# openclaw-dash

At-a-glance overview of lorp's systems and current activity.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  LORP STATUS                                              06:12 AKST   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─ GATEWAY ─────┐  ┌─ CURRENT TASK ──────────────────────────────────┐ │
│  │   ✓ ONLINE    │  │  Creating openclaw-dash repo                    │ │
│  │   ctx: 24%    │  │  > Setting up TUI dashboard for ecosystem       │ │
│  │   30m uptime  │  │  > Integrating automation tools                 │ │
│  └───────────────┘  └─────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─ REPOS ──────────────────────┐  ┌─ ACTIVITY ─────────────────────┐  │
│  │  synapse-engine  ✨  2 PRs   │  │  ▸ 06:00 Created openclaw-dash │  │
│  │  r3LAY           🟢  1 PR    │  │  ▸ 04:00 Posted daily summary  │  │
│  │  t3rra1n         ✨  0 PRs   │  │  ▸ 03:30 Checked CI status     │  │
│  │  openclaw-dash   🆕  new     │  │  ▸ 03:00 Heartbeat check       │  │
│  └──────────────────────────────┘  └─────────────────────────────────┘  │
│                                                                         │
│  ┌─ CRON ───────────────────────┐  ┌─ CHANNELS ─────────────────────┐  │
│  │  daily-summary    04:00 ✓    │  │  discord     ✓ connected       │  │
│  │  mlorp-engage     hourly     │  │  telegram    — disabled        │  │
│  │  heartbeat        30m        │  │  signal      — disabled        │  │
│  └──────────────────────────────┘  └─────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Overview

A terminal dashboard showing:
- **Gateway Status** — Health, context usage, uptime
- **Current Task** — What lorp is actively working on
- **Repositories** — Health metrics, open PRs
- **Activity Log** — Recent actions and events
- **Cron Jobs** — Scheduled tasks and their status
- **Channels** — Connected messaging platforms

## Installation

```bash
pip install -e .
```

## Usage

```bash
openclaw-dash              # Launch TUI
openclaw-dash --status     # Quick text status
openclaw-dash --json       # JSON for scripting
```

## Integrated Tools

- `repo-scanner` — Repository health metrics
- `pr-tracker` — PR status monitoring
- `smart-todo-scanner` — Context-aware TODO detection
- `dep-shepherd` — Dependency auditing
- `pr-describe` — PR description generation

## Requirements

- Python 3.10+
- OpenClaw gateway running

## License

MIT
