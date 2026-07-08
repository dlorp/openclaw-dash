"""Metric sinks for publishing dashboard data to external targets.

Sinks decouple the TUI dashboard from external consumers (MQTT panels,
log files, webhooks). Each sink runs in its own thread with a shared
queue, draining on a configurable interval.

Quick start::

    from openclaw_dash.sinks import SinkManager

    manager = SinkManager()
    manager.start_all()
    # ... on each refresh:
    manager.refresh_and_publish()
    # ... on shutdown:
    manager.stop_all()
"""

from openclaw_dash.sinks.base import SinkBase
from openclaw_dash.sinks.manager import SinkManager

__all__ = ["SinkBase", "SinkManager"]
