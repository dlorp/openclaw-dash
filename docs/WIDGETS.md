# Widgets

All panel types in openclaw-dash: what they show, when to use them, and how to configure them.

## Sparkline

A mini time-series in a single line. Best for quick health checks.

```yaml
- title: CPU Usage
  source: web-server
  chart: sparkline
  height: 3
```

Shows:
- Current value
- Sparkline trend
- Min/max over the window

Use for: CPU, memory, request rate - anything where the trend matters more than the history.

## Time-Series

Full chart with axes. Best for latency, throughput, and trend analysis.

```yaml
- title: API Latency
  source: api-gateway
  chart: time-series
  height: 5
  time_range: 1h
```

Shows:
- Line chart with time axis
- Value axis with labels
- Legend for multiple series

Use for: Response times, throughput, queue depth - metrics where history and patterns matter.

Options:
- `time_range` - Display window (default: 1h)
- `y_axis` - Which metric field to plot

## Gauge

Single value with threshold coloring. Best for utilization and health scores.

```yaml
- title: Memory Usage
  source: web-server
  chart: gauge
  height: 3
  thresholds:
    warning: 70
    error: 90
```

Shows:
- Current value
- Visual threshold zones (green/yellow/red)
- Percentage or absolute value

Use for: Disk usage, memory utilization, health scores - anything with clear good/bad ranges.

Options:
- `thresholds.warning` - Yellow zone start
- `thresholds.error` - Red zone start

## Bar

Comparative values. Best for categorical data.

```yaml
- title: Disk by Mount
  source: web-server
  chart: bar
  height: 3
  metric: disk_usage
  group_by: mount
```

Shows:
- Horizontal bars
- Labels and values
- Sorted by value (descending)

Use for: Disk usage by filesystem, memory by process, request count by endpoint.

Options:
- `metric` - Which metric to display
- `group_by` - Field to group by

## Table

Structured data. Best for lists and detailed status.

```yaml
- title: Connections
  source: database
  chart: table
  height: 5
  columns:
    - name: source_ip
      label: Source
    - name: count
      label: Count
    - name: state
      label: State
```

Shows:
- Formatted table with headers
- Aligned columns
- Scrollable if content overflows

Use for: Active connections, recent errors, process lists - any structured data.

Options:
- `columns` - List of column definitions
- `columns[].name` - Metric field name
- `columns[].label` - Display header

## Heatmap

Density visualization. Best for patterns over time.

```yaml
- title: Request Heatmap
  source: api-gateway
  chart: heatmap
  height: 5
  time_range: 24h
  bucket: 1h
```

Shows:
- Color-coded grid
- Hours on one axis, days on the other
- Intensity = request count/latency

Use for: Traffic patterns, error spikes, usage distribution.

Options:
- `time_range` - Total window
- `bucket` - Size of each cell (1h, 30m, etc.)

## Common Options

All widgets support:

```yaml
- title: Panel Title        # Required - shown in header
  source: plugin-name       # Required - which plugin feeds this
  chart: sparkline          # Required - widget type
  height: 3                 # Lines of terminal height
  enabled: true             # Can disable without removing
  refresh: 30s              # Override global refresh
```

## Layout

Panels organize in rows:

```yaml
layout:
  rows:
    - panels:
        - title: Panel A
          source: plugin-a
          chart: sparkline
        - title: Panel B
          source: plugin-b
          chart: gauge
    - panels:
        - title: Panel C
          source: plugin-c
          chart: time-series
```

- Rows stack vertically
- Panels in a row share horizontal space equally
- Each panel gets a border and title header
- Collapsed panels show only the title bar

## Color Scheme

Colors come from the active theme. Threshold zones:

| Zone | Default | Meaning |
|------|---------|---------|
| Normal | Green | Within expected range |
| Warning | Yellow/Amber | Approaching threshold |
| Error | Red | Exceeds threshold |
| Neutral | Gray | No data / inactive |

In the `phosphor` theme:
- Normal: amber (#ff9500)
- Warning: bright amber (#ffb000)
- Error: red-orange (#ff4400)

## Choosing Widgets

| If you want to show... | Use |
|------------------------|-----|
| "Is it healthy right now?" | sparkline |
| "What happened over the last hour?" | time-series |
| "How full is it?" | gauge |
| "Which is biggest?" | bar |
| "What are the details?" | table |
| "When do spikes happen?" | heatmap |
