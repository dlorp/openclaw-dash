"""Sink base class for publishing metrics to external targets.

All sinks inherit from SinkBase and implement publish() to send
aggregated metric payloads to their target (MQTT broker, file, etc).
Thread-safe queue decouples collection from delivery.
"""

from __future__ import annotations

import logging
import queue
import threading
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class SinkBase(ABC):
    """Abstract base class for metric sinks.

    Subclasses implement connect(), disconnect(), and _do_publish().
    The base handles the producer/consumer queue and lifecycle threads.

    Args:
        name: Human-readable sink name for logging.
        interval: Seconds between publish cycles (default 10).
        queue_size: Maximum items in the outbound queue (default 256).
    """

    def __init__(self, name: str, interval: int = 10, queue_size: int = 256) -> None:
        self.name = name
        self.interval = interval
        self._queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=queue_size)
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._connected = False

    # -- Lifecycle -----------------------------------------------------------

    def start(self) -> None:
        """Start the sink's background publishing thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("Sink %s already running", self.name)
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name=f"sink-{self.name}",
            daemon=True,
        )
        self._thread.start()
        logger.info("Sink %s started (interval=%ds)", self.name, self.interval)

    def stop(self) -> None:
        """Signal the sink to stop and wait for the thread to drain."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self.interval + 2)
            self._thread = None
        try:
            self.disconnect()
        except Exception:
            logger.exception("Sink %s error during disconnect", self.name)
        logger.info("Sink %s stopped", self.name)

    @property
    def running(self) -> bool:
        """Return True if the sink thread is alive."""
        return self._thread is not None and self._thread.is_alive()

    # -- Producer API --------------------------------------------------------

    def publish(self, metric_name: str, value: Any, unit: str = "") -> None:
        """Enqueue a single metric for publishing.

        Args:
            metric_name: Identifier like 'cpu', 'mem', 'gateway.status'.
            value: Numeric or string value.
            unit: Optional unit label ('%', 'GB', 'count').
        """
        try:
            self._queue.put_nowait({
                "metric": metric_name,
                "value": value,
                "unit": unit,
            })
        except queue.Full:
            logger.debug("Sink %s queue full, dropping %s", self.name, metric_name)

    def publish_batch(self, payload: dict[str, Any]) -> None:
        """Enqueue an entire payload dict (e.g. from collector snapshot).

        Args:
            payload: Complete key-value dict to publish on next cycle.
        """
        try:
            self._queue.put_nowait(payload)
        except queue.Full:
            logger.debug("Sink %s queue full, dropping batch", self.name)

    # -- Abstract methods ----------------------------------------------------

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the sink target."""

    @abstractmethod
    def disconnect(self) -> None:
        """Tear down the connection."""

    @abstractmethod
    def _do_publish(self, payload: dict[str, Any]) -> None:
        """Send payload to the sink target (implemented by subclass)."""

    # -- Internal loop -------------------------------------------------------

    def _run_loop(self) -> None:
        """Background loop: drain queue every interval seconds."""
        while not self._stop_event.is_set():
            # Connect if needed
            if not self._connected:
                try:
                    self.connect()
                    self._connected = True
                except Exception:
                    logger.exception("Sink %s connect failed, retrying in %ds", self.name, self.interval)
                    self._stop_event.wait(timeout=self.interval)
                    continue

            # Drain queue and batch
            batch: dict[str, Any] = {}
            drained = 0
            while True:
                try:
                    item = self._queue.get_nowait()
                    if "metric" in item:
                        # Single metric publish
                        batch[item["metric"]] = item["value"]
                        if item.get("unit"):
                            batch[f"{item['metric']}_unit"] = item["unit"]
                    else:
                        # Full payload — merge top-level keys
                        batch.update(item)
                    drained += 1
                except queue.Empty:
                    break

            if batch:
                try:
                    self._do_publish(batch)
                except Exception:
                    logger.exception("Sink %s publish failed", self.name)
                    self._connected = False

            # Wait for next cycle
            self._stop_event.wait(timeout=self.interval)