# Configuration Guide

openclaw-dash uses YAML for all configuration: plugin definitions, panel layout, themes, and update intervals.

## Config File Location

Default: `~/.config/openclaw-dash/config.yaml`

Override with: `openclaw-dash --config /path/to/config.yaml`

## Minimal Config

```yaml
plugins:
  - name: system
    type: ssh-agent
    host: my-server
    metrics: [cpu, memory, disk]

  - name: api-health
    type: http-api
    url: https://myapi.com/health
    interval: 30s

  - name: db
    type: db-health
    connection: postgresql://localhost:5432/mydb
```

This gives you three panels: server health, API status, and database connections.

## Plugin Configuration

Each plugin has a standard structure:

```yaml
plugins:
  - name: my-plugin          # Unique identifier
    type: ssh-agent          # Plugin type (see below)
    interval: 30s            # Update frequency (default: 60s)
    enabled: true            # Can disable without removing
    # ... type-specific options
```

### Built-in Plugin Types

#### ssh-agent

Collects system metrics via SSH.

```yaml
- name: prod-server
  type: ssh-agent
  host: 192.168.1.100
  user: monitor
  key: ~/.ssh/id_ed25519
  metrics:
    - cpu
    - memory
    - disk
    - network
    - load
```

#### http-api

Polls HTTP endpoints for status and latency.

```yaml
- name: api-gateway
  type: http-api
  url: https://api.example.com/health
  method: GET
  interval: 15s
  expected_status: 200
  timeout: 5s
  headers:
    Authorization: Bearer ${API_TOKEN}
```

#### db-health

Checks database connections and performance.

```yaml
- name: primary-db
  type: db-health
  connection: postgresql://user:pass@localhost:5432/mydb
  checks:
    - connection_pool
    - slow_queries
    - replication_lag
```

#### business-api

Pulls custom metrics from internal APIs.

```yaml
- name: daily-metrics
  type: business-api
  url: https://internal.example.com/metrics/daily
  headers:
    X-API-Key: ${BUSINESS_API_KEY}
  map:
    registrations: users.new_today
    revenue: orders.total_cents
```

### Environment Variables

Plugins support environment variable interpolation:

```yaml
url: https://api.example.com/health
headers:
  Authorization: Bearer ${API_TOKEN}
```

Set `API_TOKEN` in your shell or `.env` file.

## Layout Configuration

Panel layout is defined separately from plugins:

```yaml
layout:
  rows:
    - panels:
        - title: System Health
          source: prod-server
          chart: sparkline
          height: 3
        - title: API Latency
          source: api-gateway
          chart: time-series
          height: 5
    - panels:
        - title: Database
          source: primary-db
          chart: gauge
          height: 3
        - title: Business Metrics
          source: daily-metrics
          chart: bar
          height: 3
```

### Chart Types

| Type | Best For | Height |
|------|----------|--------|
| `sparkline` | Quick health overview | 1-3 lines |
| `time-series` | Latency, throughput trends | 5+ lines |
| `gauge` | Single values with thresholds | 3 lines |
| `bar` | Comparing categories | 3-5 lines |
| `table` | Structured data | Variable |
| `heatmap` | Density over time | 5+ lines |

## Theme Configuration

```yaml
theme:
  name: phosphor          # Built-in: dark, light, phosphor
  # Or define custom:
  colors:
    background: "#0a0a0a"
    text: "#ff9500"
    accent: "#ff6600"
    success: "#00ff00"
    warning: "#ffff00"
    error: "#ff0000"
```

## Global Settings

```yaml
settings:
  refresh_interval: 30s    # Global default for all plugins
  log_level: info          # debug, info, warn, error
  demo_mode: false         # Use mock data
  gateway_url: http://localhost:18789  # Optional gateway
```

## Full Example

```yaml
plugins:
  - name: web-server
    type: ssh-agent
    host: web.example.com
    user: monitor
    metrics: [cpu, memory, disk, network]

  - name: api-status
    type: http-api
    url: https://api.example.com/health
    interval: 10s

  - name: database
    type: db-health
    connection: postgresql://localhost:5432/app

  - name: signups
    type: business-api
    url: https://internal.example.com/metrics/signups
    interval: 300s

layout:
  rows:
    - panels:
        - title: Web Server
          source: web-server
          chart: sparkline
        - title: API Health
          source: api-status
          chart: gauge
    - panels:
        - title: Database
          source: database
          chart: time-series
        - title: Signups
          source: signups
          chart: bar

theme:
  name: dark

settings:
  refresh_interval: 30s
```
