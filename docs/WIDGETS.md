# Widgets Reference

Complete guide to every panel and widget in openclaw-dash.

## Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│  HEADER (clock)                                                         │
├──────────────────────────── METRIC BOXES ───────────────────────────────┤
│  [ Gateway ] [ Cost ] [ Error Rate ] [ Streak ]                         │
├─────────────────────────────────────────────────────────────────────────┤
│  GATEWAY    │  CURRENT TASK                                             │
├─────────────┼───────────────────────────────────────────────────────────┤
│  ALERTS (2 columns)                                                     │
├─────────────────────────────────────────────────────────────────────────┤
│  REPOS (2 cols)           │  ACTIVITY                                   │
├─────────────┬─────────────┼─────────────────────────────────────────────┤
│  CRON       │  SESSIONS   │  AGENTS                                     │
├─────────────┴─────────────┴─────────────────────────────────────────────┤
│  METRICS (2 columns)      │  CHANNELS                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  SECURITY (2 columns)                                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  LOGS (3 columns)                                                       │
├─────────────────────────────────────────────────────────────────────────┤
│  RESOURCES (3 columns)                                                  │
├─────────────────────────────────────────────────────────────────────────┤
│  INPUT PANE                                                             │
├─────────────────────────────────────────────────────────────────────────┤
│  FOOTER                                                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Metric Boxes Bar

Compact KPI summary always visible at the top.

### Boxes

| Box | Shows | Colors |
|-----|-------|--------|
| **Gateway** | Online/Offline status | Green = online, Red = offline |
| **Cost** | Today's API cost | Neutral display |
| **Error Rate** | Error percentage today | Green <1%, Yellow 1-5%, Red >5% |
| **Streak** | GitHub contribution streak | 🔥 for active streak |

### Example
```
✓ ONLINE  │  $0.42/day  │  0.2% err  │  🔥 12 days
```

---

## Gateway Panel

**Focus key:** `g`

Shows OpenClaw gateway health and resource usage.

### Data Displayed
- **Status**: Online/Offline indicator
- **Context**: Current context window usage (%)
- **Uptime**: How long the gateway has been running

### States

| State | Display |
|-------|---------|
| Healthy | `✓ ONLINE` with green indicator |
| Degraded | `⚠ DEGRADED` with yellow indicator |
| Offline | `✗ OFFLINE` with red indicator, error message |

### Example
```
✓ ONLINE
────────────────────
Context: 24%
████████░░░░░░░░░░░░
Uptime: 2h 15m
```

---

## Current Task Panel

Shows what the agent is currently working on.

### Data Displayed
- Active task description from the agent's current context
- Subtask indicators if available

### Example
```
▸ Building new feature for project-x
  > Implementing auth module
  > Writing tests
```

---

## Alerts Panel

**Focus key:** `a`

Aggregates alerts from multiple sources with severity-based color coding.

### Alert Sources
- CI/CD failures
- Security vulnerabilities
- High context usage warnings
- PR review requests
- Custom alerts

### Severity Levels

| Level | Color | Icon |
|-------|-------|------|
| Critical | Red | 🔴 |
| High | Orange | 🟠 |
| Medium | Yellow | 🟡 |
| Low | Blue | 🔵 |
| Info | Gray | ⚪ |

### Example
```
🔴 2 critical • 🟠 1 high

🔴 CI failing on main
   project-x • 2h ago

🟠 5 vulnerable dependencies
   another-repo • 1d ago
```

---

## Repos Panel

**Focus key:** `p`

Repository health overview as a data table.

### Columns

| Column | Description |
|--------|-------------|
| Repo | Repository name |
| Health | Status emoji (✨ clean, 🟢 good, 🟡 needs attention, 🔴 issues) |
| PRs | Open pull request count |
| Last Commit | Relative time of last commit |

### Example
```
┌──────────────┬────────┬─────┬─────────────┐
│ Repo         │ Health │ PRs │ Last Commit │
├──────────────┼────────┼─────┼─────────────┤
│ my-project   │   ✨   │  0  │   2h ago    │
│ another-repo │   🟢   │  2  │   1d ago    │
│ side-project │   🟡   │  5  │   3d ago    │
└──────────────┴────────┴─────┴─────────────┘
```

---

## Activity Panel

Recent actions log with timestamps.

### Data Displayed
- Action description
- Timestamp
- Source indicator

### Example
```
▸ 14:30 Pushed feature branch
▸ 14:00 Reviewed PR #42
▸ 13:30 Fixed CI pipeline
▸ 12:00 Merged hotfix
```

---

## Sessions Panel

**Focus key:** `s` (via sessions)

Active OpenClaw sessions and context usage.

### Data Displayed
- Session identifier
- Active/inactive status
- Context burn rate (% of context window used)

### Example
```
2/4 active ████░░░░
──────────────────────────
  ● main         ████░ 45%
  ○ sub-agent-1  █░░░░ 12%
  ○ sub-agent-2  ░░░░░  8%
  ○ background   ░░░░░  2%
```

---

## Agents Panel

**Focus key:** `n`

Sub-agent coordination view.

### Data Displayed
- Agent name/ID
- Current status (active, idle, completed, error)
- Context usage
- Current task summary

### Example
```
🤖 Agents
──────────────────────────
  ● researcher   [active]
    Context: 34%
    Finding API docs

  ● coder        [idle]
    Context: 12%
    Waiting for specs
```

---

## Cron Panel

**Focus key:** `c`

Scheduled jobs and their status.

### Data Displayed
- Job name
- Enabled/disabled status
- Last run time
- Next scheduled run

### Example
```
3/5 enabled ████░░░░
──────────────────────────
  ▸ daily-backup     (enabled)
  ▸ sync-repos       (enabled)
  ▸ cleanup-logs     (enabled)
  ○ weekly-audit     (disabled)
  ○ monthly-report   (disabled)
```

---

## Channels Panel

Connected messaging channels and their status.

### Data Displayed
- Channel type (Discord, Slack, etc.)
- Connection status
- Message activity

### Example
```
Channels
──────────────────────────
  ● Discord    online  (3 servers)
  ● Slack      online  (2 workspaces)
  ○ Telegram   offline
```

---

## Metrics Panel

**Focus key:** `m`

Cost tracking and performance statistics.

### Sections

#### Token Costs
- Today's spend
- Input/output token breakdown
- 7-day trend

#### Performance
- Total API calls
- Error count and rate
- Average latency

#### GitHub
- Contribution streak
- PR cycle time averages

### Example
```
📊 Metrics
──────────────────────────
💰 Today: $0.42
   Input:  12,456 tokens
   Output: 3,891 tokens

⚡ Performance
   Calls: 234 | Errors: 2 (0.9%)
   Latency: 450ms avg

🐙 GitHub
   🔥 12 day streak
   PR cycle: 4.2h avg
```

---

## Security Panel

**Focus key:** `s`

Security audit results and recommendations.

### Data Displayed
- Config security score
- Dependency vulnerabilities
- Audit findings by severity

### Example
```
🔒 Security
──────────────────────────
Config Score: 85/100
  ⚠ 2 warnings
  ℹ 3 suggestions

Dependencies:
  🔴 1 critical (lodash)
  🟡 3 moderate
  Total: 4 issues
```

---

## Logs Panel

**Focus key:** `l`

Real-time gateway log viewer.

### Features
- Auto-scrolling log tail
- Color-coded log levels
- Timestamp display
- Configurable line count

### Log Levels

| Level | Color |
|-------|-------|
| ERROR | Red |
| WARN | Yellow |
| INFO | Default |
| DEBUG | Dim |

### Example
```
📜 Logs
──────────────────────────
14:32:01 [INFO]  Request completed in 234ms
14:32:00 [DEBUG] Processing message...
14:31:58 [WARN]  Rate limit approaching
14:31:55 [INFO]  New session started
```

---

## Resources Panel

**Focus key:** `x` (toggle visibility)

System resource monitoring.

### Data Displayed

#### CPU
- Overall usage percentage
- Per-core usage bars
- Load average (1m/5m/15m)
- Usage sparkline history

#### Memory
- Usage percentage
- Used/Total/Available
- Swap usage (if significant)

#### Disk
- Per-mount usage
- Free space

#### Network
- Upload/download rates
- Rate sparklines

### Example
```
📊 Resources
──────────────────────────
✓ CPU: 23.5% ████████░░░░ ▁▂▃▄▃▂▁▂▃▄
  Cores: ██░░░░██░░░░ (8 total)
  Load: 1.23 / 1.45 / 1.67
────────────────────────────────────────
✓ MEM: 67.2% ████████████░░░ ▄▅▅▆▆▅▅▆
  10.8G / 16.0G (5.2G free)
────────────────────────────────────────
█ DISK
  ✓ /: 45% ████░░░░ (120G free)
  ⚠ /data: 82% ████████░░ (18G free)
────────────────────────────────────────
⚡ NET
  ↑ 1.2 MB/s ▁▂▃▄▃▂▁▂
  ↓ 3.4 MB/s ▂▃▄▅▄▃▂▃
```

---

## Input Pane

**Focus key:** `:` or `i`

Command input for sending commands to the gateway.

### Usage
1. Press `:` or `i` to focus
2. Type command
3. Press Enter to send
4. Press Escape to cancel

---

## Help Panel

**Focus key:** `h` or `?`

Overlay showing all keyboard shortcuts and navigation help.

---

## Collapsible Panels

All main panels support collapse/expand:

| Key | Action |
|-----|--------|
| `Enter` | Toggle focused panel |
| `Ctrl+[` | Collapse all panels |
| `Ctrl+]` | Expand all panels |

Collapsed panels show a summary line instead of full content.

---

## Navigation

### Focus Keys

| Key | Panel |
|-----|-------|
| `g` | Gateway |
| `s` | Security |
| `m` | Metrics |
| `a` | Alerts |
| `c` | Cron |
| `p` | Repos |
| `l` | Logs |
| `n` | Agents |
| `x` | Toggle Resources |

### Jump Mode

Press `f` to enter jump mode, then press the letter shown on each panel to focus it.

### Tab Navigation

- `Tab` — Next panel
- `Shift+Tab` — Previous panel

### Vim-Style Scrolling

- `j` — Scroll down
- `k` — Scroll up
- `G` — Jump to end
- `Home` — Jump to top

---

## Next Steps

- [Configuration](CONFIGURATION.md) — Customize panel visibility and behavior
- [Development](DEVELOPMENT.md) — Create custom widgets
