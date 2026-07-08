# Widgets Reference

Every panel type in openclaw-dash, with examples and configuration.

## Panel Types

### Sparkline

Mini time-series chart in a single line. Best for quick health overviews.

```yaml
- title: CPU Usage
  source: web-server
  chart: sparkline
  height: 3
```

Shows: current value, trend, min/max over window.

### Time-Series

Full chart with axes. Best for latency, throughput, and trend analysis.

```yaml
- title: API Latency
  source: api-gateway
  chart: time-series
  height: 5
  time_range: 1h
```

Shows: line chart with time axis, value axis, legend.

### Gauge

Single value with threshold coloring. Best for utilization, health scores.

```yaml
- title: Memory Usage
  source: web-server
  chart: gauge
  height: 3
  thresholds:
    warning: 70
    error: 90
```

Shows: current value, threshold zones (green/yellow/red).

### Bar

Comparative values. Best for categorical data, resource allocation.

```yaml
- title: Disk Usage by Mount
  source: web-server
  chart: bar
  height: 3
  metric: disk_usage
  group_by: mount
```

Shows: horizontal bars with labels and values.

### Table

Structured data. Best for lists, inventories, detailed status.

```yaml
- title: Active Connections
  source: database
  chart: table
  height: 5
  columns:
    - name: source
      label: Source IP
    - name: count
      label: Connections
    - name: state
      label: State
```

Shows: formatted table with headers and alignment.

### Heatmap

Density visualization. Best for request patterns, usage over time.

```yaml
- title: Request Distribution
  source: api-gateway
  chart: heatmap
  height: 5
  time_range: 24h
  bucket: 1h
```

Shows: color-coded grid (hour vs. day) with density intensity.

## Widget Configuration

All widgets support these common options:

```yaml
- title: Panel Title        # Required
  source: plugin-name       # Required: which plugin feeds this
  chart: sparkline          # Required: panel type
  height: 3                 # Lines of terminal height
  enabled: true             # Can disable without removing
  refresh: 30s              # Override global refresh interval
```

## Layout Structure

Panels are organized in rows:

```yaml
layout:
  rows:
    - panels:
        - title: Panel 1
          source: plugin-a
          chart: sparkline
        - title: Panel 2
          source: plugin-b
          chart: gauge
    - panels:
        - title: Panel 3
          source: plugin-c
          chart: time-series
```

Rows stack vertically. Panels within a row share horizontal space equally.

## Color Scheme

Widget colors come from the active theme. Threshold zones:

| Zone | Color | Usage |
|------|-------|-------|
| Normal | Green/Blue | Within expected range |
| Warning | Yellow/Amber | Approaching threshold |
| Error | Red | Exceeds threshold |
| Neutral | Gray | No data / inactive |
