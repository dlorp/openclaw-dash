"""Sink manager — lifecycle and metric routing for all configured sinks.

Reads [sinks.*] sections from config.toml, instantiates enabled sinks,
starts their threads, and hooks into the collector refresh loop to
publish metrics on each cycle.
"""

from __future__ import annotations

import logging
from typing import Any

from openclaw_dash.collectors import alerts, gateway, resources

logger = logging.getLogger(__name__)


def _load_sink_config() -> dict[str, dict[str, Any]]:
    """Load sink configuration from the user's config.toml.

    Looks for [sinks.mqtt], [sinks.log], etc. Sections where
    enabled is absent or false are skipped.

    Returns:
        Dict mapping sink name to its parsed config dict.
    """
    from pathlib import Path

    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore[import-not-found,no-redef]

    config_path = Path.home() / ".config" / "openclaw-dash" / "config.toml"
    if not config_path.exists():
        return {}

    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        logger.debug("Could not load config from %s", config_path)
        return {}

    sinks_section = data.get("sinks", {})
    enabled: dict[str, dict[str, Any]] = {}

    for name, cfg in sinks_section.items():
        if isinstance(cfg, dict) and cfg.get("enabled", False):
            enabled[name] = cfg

    return enabled


class SinkManager:
    """Manages lifecycle and data flow for all metric sinks.

    Usage::

        manager = SinkManager()
        manager.start_all()
        # ... later, on each refresh cycle:
        manager.refresh_and_publish()
        # ... on shutdown:
        manager.stop_all()
    """

    def __init__(self) -> None:
        self._sinks: list[Any] = []

    @property
    def sinks(self) -> list[Any]:
        """Return the list of active sink instances."""
        return list(self._sinks)

    @property
    def running(self) -> bool:
        """Return True if any sink is currently running."""
        return any(s.running for s in self._sinks)

    def start_all(self) -> None:
        """Instantiate and start sinks based on config.toml."""
        configs = _load_sink_config()

        if not configs:
            logger.info("No sinks enabled in config")
            return

        for name, cfg in configs.items():
            if name == "mqtt":
                sink = self._create_mqtt_sink(cfg)
            else:
                logger.warning("Unknown sink type: %s, skipping", name)
                continue

            if sink is not None:
                self._sinks.append(sink)
                sink.start()

        if self._sinks:
            logger.info("Started %d sink(s)", len(self._sinks))

    def stop_all(self) -> None:
        """Stop all running sinks."""
        for sink in self._sinks:
            sink.stop()
        self._sinks.clear()
        logger.info("All sinks stopped")

    def refresh_and_publish(self) -> None:
        """Collect current metrics and push them to all sinks.

        Gathers data from resource, gateway, and alert collectors,
        merges into a single payload, and fans out to every active sink.
        """
        if not self._sinks:
            return

        payload: dict[str, Any] = {}

        # Resource metrics (CPU, memory)
        try:
            payload["resources"] = resources.collect()
        except Exception:
            logger.debug("Resource collection failed for sink publish")

        # Gateway status
        try:
            payload["gateway"] = gateway.collect()
        except Exception:
            logger.debug("Gateway collection failed for sink publish")

        # Alert count
        try:
            alert_data = alerts.collect()
            payload["alerts"] = alert_data
        except Exception:
            logger.debug("Alert collection failed for sink publish")

        for sink in self._sinks:
            sink.publish_batch(payload)

    # -- Factory methods -----------------------------------------------------

    @staticmethod
    def _create_mqtt_sink(cfg: dict[str, Any]) -> Any:
        """Create an MqttSink from config dict.

        Args:
            cfg: Dict with broker, port, topic, interval, username, password.

        Returns:
            MqttSink instance or None if paho-mqtt is missing.
        """
        try:
            from openclaw_dash.sinks.mqtt_sink import MqttSink
        except ImportError as e:
            logger.warning("Cannot create MQTT sink: %s", e)
            return None

        return MqttSink(
            broker=cfg.get("broker", "localhost"),
            port=int(cfg.get("port", 1883)),
            topic=cfg.get("topic", "ocd/panel"),
            interval=int(cfg.get("interval", 10)),
            client_id=cfg.get("client_id", "ocd-dash"),
            username=cfg.get("username"),
            password=cfg.get("password"),
        )