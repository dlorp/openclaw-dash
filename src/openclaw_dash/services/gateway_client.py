"""OpenClaw Gateway API client.

Provides interface for querying OpenClaw gateway at localhost:18789.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

DEFAULT_GATEWAY_URL = "http://localhost:18789"


@dataclass
class GatewayConfig:
    """OpenClaw gateway configuration."""

    url: str = DEFAULT_GATEWAY_URL
    timeout: float = 10.0


class GatewayClient:
    """Client for OpenClaw gateway API."""

    def __init__(self, config: GatewayConfig | None = None):
        self.config = config or GatewayConfig()
        self._client = httpx.Client(base_url=self.config.url, timeout=self.config.timeout)

    def get_status(self) -> dict[str, Any]:
        """GET /api/status - gateway status and info."""
        # TODO: Implement actual API call
        raise NotImplementedError("Gateway integration pending")

    def get_sessions(self) -> list[dict[str, Any]]:
        """GET /api/sessions - list active sessions."""
        raise NotImplementedError("Gateway integration pending")

    def get_config(self) -> dict[str, Any]:
        """Get current gateway configuration."""
        raise NotImplementedError("Gateway integration pending")

    def patch_config(self, patch: dict[str, Any]) -> bool:
        """Patch gateway configuration (e.g., switch models)."""
        raise NotImplementedError("Gateway integration pending")

    def get_available_models(self) -> list[str]:
        """Get models available in OpenClaw config."""
        raise NotImplementedError("Gateway integration pending")

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
