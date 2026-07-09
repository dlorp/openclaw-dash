# Configuration

hermes-dash uses one YAML file for everything: plugins, layout, themes, intervals.

## Config Location

Default: `~/.config/hermes-dash/config.yaml`

Override: `hermes-dash --config /path/to/config.yaml`

## Minimal Example

```yaml
plugins:
  - name: server
    type: ssh-agent
    host: 192.168.1.10
    metrics: [cpu, memory, disk]

  - name: api
    type: http-api
    url: https://api.example.com/health
    interval: 30s

layout:
  rows:
    - panels:
        - title: Server
          source: server
          chart: sparkline
        - title: API
          source: api
          chart: gauge
```

This gives you two panels: server health and API status.

## Plugin Configuration

Each plugin has a standard structure:

```yaml
plugins:
  - name: my-source       # Unique identifier
    type: ssh-agent       # Plugin type
    interval: 30s         # Update frequency (default: 60s)
    enabled: true         # Can disable without removing
    # ... type-specific options
```

### ssh-agent

System metrics via SSH.

```yaml
- name: prod-web
  type: ssh-agent
  host: web-01.prod.internal
  user: monitor
  key: ~/.ssh/id_ed25519
  metrics:
    - cpu
    - memory
    - disk
    - network
    - load
```

Requires SSH key auth. Password auth is not supported.

### http-api

Poll HTTP endpoints.

```yaml
- name: gateway-health
  type: http-api
  url: https://gateway.example.com/health
  method: GET
  interval: 15s
  expected_status: 200
  timeout: 5s
  headers:
    Authorization: Bearer ${API_TOKEN}
```

Returns: status code, response time, optional JSON fields.

### db-health

Database connection and performance.

```yaml
- name: primary-db
  type: db-health
  connection: postgresql://user:${DB_PASS}@localhost:5432/app
  checks:
    - connection_pool
    - slow_queries
    - replication_lag
```

Supports PostgreSQL, MySQL, and SQLite.

### business-api

Custom metrics from internal APIs.

```yaml
- name: daily-kpis
  type: business-api
  url: https://internal.example.com/metrics/daily
  headers:
    X-API-Key: ${BUSINESS_API_KEY}
  map:
    registrations: users.new_today
    revenue: orders.total_cents
```

The `map` section translates API response fields to metric names.

### Environment Variables

Use `${VAR_NAME}` syntax anywhere in plugin config:

```yaml
connection: postgresql://user:${DB_USER}@localhost:5432/app
headers:
  Authorization: Bearer ${API_TOKEN}
```

Variables are read from environment at startup.

## Layout Configuration

Define panel arrangement separately from plugins:

```yaml
layout:
  rows:
    - panels:
        - title: CPU Usage
          source: prod-web
          chart: sparkline
          height: 3
        - title: Memory
          source: prod-web
          chart: gauge
          height: 3
    - panels:
        - title: API Latency
          source: gateway-health
          chart: time-series
          height: 5
```

Rows stack vertically. Panels in a row share horizontal space equally.

### Chart Types

| Type | Height | Best For |
|------|--------|----------|
| sparkline | 1-3 | Quick health overview |
| time-series | 5+ | Latency, throughput trends |
| gauge | 3 | Single values with thresholds |
| bar | 3-5 | Category comparison |
| table | variable | Structured lists |
| heatmap | 5+ | Density over time |

### Widget Options

Common options for all widgets:

```yaml
- title: Panel Title        # Required
  source: plugin-name       # Required - which plugin feeds this
  chart: sparkline          # Required - panel type
  height: 3                 # Lines of terminal height
  enabled: true             # Can disable without removing
  refresh: 30s              # Override global interval
```

Gauge-specific options:

```yaml
- title: Disk Usage
  source: prod-web
  chart: gauge
  thresholds:
    warning: 70
    error: 90
```

Time-series options:

```yaml
- title: Request Latency
  source: gateway-health
  chart: time-series
  time_range: 1h            # Display window
  y_axis: latency_ms        # Metric field to plot
```

## Theme Configuration

Use a built-in theme:

```yaml
theme:
  name: phosphor    # dark | light | phosphor
```

Or define custom colors:

```yaml
theme:
  colors:
    background: "#0a0a0a"
    text: "#ff9500"
    accent: "#ff6600"
    success: "#00aa00"
    warning: "#ffaa00"
    error: "#ff0000"
```

The `phosphor` theme uses amber (#ff9500) on dark gray to mimic CRT phosphor.

## Global Settings

```yaml
settings:
  refresh_interval: 30s     # Default for all plugins
  log_level: info           # debug | info | warn | error
  demo_mode: false          # Use mock data
  gateway_url: null         # Optional gateway endpoint
```

## Full Example

```yaml
plugins:
  - name: web-server
    type: ssh-agent
    host: web-01.internal
    user: monitor
    metrics: [cpu, memory, disk, network]

  - name: api-gateway
    type: http-api
    url: https://api.internal/health
    interval: 10s

  - name: database
    type: db-health
    connection: postgresql://localhost:5432/app

  - name: signups
    type: business-api
    url: https://metrics.internal/signups
    interval: 300s

layout:
  rows:
    - panels:
        - title: Web Server
          source: web-server
          chart: sparkline
          height: 3
        - title: API Health
          source: api-gateway
          chart: gauge
          height: 3
    - panels:
        - title: Database
          source: database
          chart: time-series
          height: 5
        - title: Daily Signups
          source: signups
          chart: bar
          height: 5

theme:
  name: dark

settings:
  refresh_interval: 30s
  log_level: info
```

## Validation

Config is validated on startup. Errors are printed to stderr with line numbers. The dashboard will not start with invalid config.

Check config without running:

```bash
hermes-dash --config-check
```
