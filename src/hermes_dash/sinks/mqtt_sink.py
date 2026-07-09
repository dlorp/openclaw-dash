"""MQTT sink — publishes dashboard metrics to an MQTT broker.

Default topic: ocd/panel
Default payload: JSON with cpu, mem, alerts, status, ts fields.
Requires paho-mqtt (optional dep: pip install hermes-dash[mqtt]).
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from hermes_dash.sinks.base import SinkBase

logger = logging.getLogger(__name__)


class MqttSink(SinkBase):
    """Publish metrics to an MQTT broker as JSON.

    Args:
        broker: MQTT broker hostname (default 'localhost').
        port: MQTT broker port (default 1883).
        topic: MQTT topic to publish to (default 'ocd/panel').
        interval: Seconds between publish cycles (default 10).
        client_id: MQTT client identifier (default 'ocd-dash').
        username: Optional MQTT username.
        password: Optional MQTT password.
    """

    def __init__(
        self,
        broker: str = "localhost",
        port: int = 1883,
        topic: str = "ocd/panel",
        interval: int = 10,
        client_id: str = "ocd-dash",
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        super().__init__(name="mqtt", interval=interval)
        self.broker = broker
        self.port = port
        self.topic = topic
        self.client_id = client_id
        self.username = username
        self.password = password
        self._client: Any = None

    def connect(self) -> None:
        """Connect to the MQTT broker."""
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            raise ImportError(
                "paho-mqtt is required for MQTT sink. Install with: pip install hermes-dash[mqtt]"
            )

        # paho-mqtt v2+ requires CallbackAPIVersion as first arg
        if hasattr(mqtt, "CallbackAPIVersion"):
            self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.client_id)
        else:
            self._client = mqtt.Client(client_id=self.client_id)

        if self.username and self.password:
            self._client.username_pw_set(self.username, self.password)

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

        logger.info("MQTT sink connecting to %s:%d", self.broker, self.port)
        self._client.connect(self.broker, self.port, keepalive=60)
        self._client.loop_start()

    def disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None
            self._connected = False

    def _do_publish(self, payload: dict[str, Any]) -> None:
        """Publish metric payload as JSON to the configured topic.

        Args:
            payload: Merged metric key-values collected since last publish.
        """
        # Flatten nested dicts for the OLED panel (which expects flat keys)
        flat = self._flatten_metrics(payload)
        flat["ts"] = time.time()

        json_str = json.dumps(flat, default=str)

        if self._client is not None:
            result = self._client.publish(self.topic, json_str, qos=0)
            if result.rc != 0:
                logger.warning("MQTT publish failed rc=%d for topic %s", result.rc, self.topic)
            else:
                logger.debug("MQTT published %d bytes to %s", len(json_str), self.topic)

    def _flatten_metrics(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Extract key metrics from collector payloads for the panel.

        Accepts raw collector output and pulls the fields the OLED
        panel cares about: cpu%, mem%, alerts count, status string.
        """
        flat: dict[str, Any] = {}

        for key, value in payload.items():
            if not isinstance(value, dict):
                flat[key] = value
                continue

            # Resource collector: cpu.percent, memory.percent
            if "cpu" in value and isinstance(value["cpu"], dict):
                cpu_data = value["cpu"]
                flat["cpu"] = cpu_data.get("percent", 0.0)

            if "memory" in value and isinstance(value["memory"], dict):
                mem_data = value["memory"]
                flat["mem"] = mem_data.get("percent", 0.0)

        # Alerts count
        if "alerts" in payload and isinstance(payload["alerts"], dict):
            alerts_data = payload["alerts"]
            flat.setdefault("alerts", alerts_data.get("count", alerts_data.get("total", 0)))
        elif "alerts" not in flat:
            flat.setdefault("alerts", 0)

        # Status derived from gateway health
        if "gateway" in payload and isinstance(payload["gateway"], dict):
            gw = payload["gateway"]
            flat.setdefault("status", "ok" if gw.get("healthy", False) else "err")
        elif "status" not in flat:
            flat.setdefault("status", "ok")

        return flat

    # -- Callbacks -----------------------------------------------------------

    @staticmethod
    def _on_connect(client: Any, userdata: Any, flags: Any, *args: Any) -> None:
        # paho-mqtt v1: (client, userdata, flags, rc)
        # paho-mqtt v2: (client, userdata, flags, reason_code, properties)
        rc = args[0] if args else -1
        rc_value = int(rc) if not isinstance(rc, int) else rc
        if rc_value == 0:
            logger.info("MQTT connected (rc=0)")
        else:
            logger.warning("MQTT connect returned rc=%s", rc)

    @staticmethod
    def _on_disconnect(client: Any, userdata: Any, *args: Any) -> None:
        # paho-mqtt v1: (client, userdata, rc)
        # paho-mqtt v2: (client, userdata, flags, reason_code, properties)
        rc = args[0] if args else -1
        rc_value = int(rc) if not isinstance(rc, int) else rc
        if rc_value != 0:
            logger.warning("MQTT unexpected disconnect (rc=%s), will reconnect", rc)
