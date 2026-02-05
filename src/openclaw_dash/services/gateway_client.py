"""OpenClaw Gateway API client.

Provides interface for querying OpenClaw gateway at localhost:18789.
Uses HTTP for fast health checks and falls back to CLI for detailed data.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

DEFAULT_GATEWAY_URL = "http://localhost:18789"


@dataclass
class GatewayConfig:
    """OpenClaw gateway configuration."""

    url: str = DEFAULT_GATEWAY_URL
    timeout: float = 10.0


class GatewayError(Exception):
    """Base exception for gateway errors."""

    pass


class GatewayConnectionError(GatewayError):
    """Raised when unable to connect to gateway."""

    pass


class GatewayClient:
    """Client for OpenClaw gateway API.

    Provides methods for checking gateway status, listing sessions,
    and managing configuration. Uses HTTP API where available and
    falls back to CLI commands for operations not exposed via HTTP.

    Example:
        with GatewayClient() as client:
            status = client.get_status()
            if status["healthy"]:
                sessions = client.get_sessions()
    """

    def __init__(self, config: GatewayConfig | None = None):
        """Initialize gateway client.

        Args:
            config: Gateway configuration. Uses default localhost:18789 if not provided.
        """
        self.config = config or GatewayConfig()
        self._client = httpx.Client(base_url=self.config.url, timeout=self.config.timeout)

    def get_status(self) -> dict[str, Any]:
        """GET /health - gateway status and health info.

        Returns:
            Dictionary containing:
                - healthy (bool): Whether gateway is responding
                - latency_ms (int): Response time in milliseconds
                - url (str): Gateway URL
                - collected_at (str): ISO timestamp
        """
        start_time = datetime.now()
        try:
            resp = self._client.get("/health")
            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            if resp.status_code == 200:
                # Try to parse JSON response, fall back to basic status
                try:
                    data = resp.json()
                    data.update(
                        {
                            "healthy": True,
                            "latency_ms": latency_ms,
                            "url": self.config.url,
                            "collected_at": datetime.now().isoformat(),
                        }
                    )
                    return data
                except Exception:
                    return {
                        "healthy": True,
                        "latency_ms": latency_ms,
                        "url": self.config.url,
                        "collected_at": datetime.now().isoformat(),
                    }
            else:
                return {
                    "healthy": False,
                    "status_code": resp.status_code,
                    "error": f"Health check returned {resp.status_code}",
                    "latency_ms": latency_ms,
                    "url": self.config.url,
                    "collected_at": datetime.now().isoformat(),
                }
        except httpx.ConnectError as e:
            raise GatewayConnectionError(f"Cannot connect to gateway at {self.config.url}: {e}")
        except httpx.TimeoutException:
            raise GatewayConnectionError(f"Gateway at {self.config.url} timed out")
        except Exception as e:
            raise GatewayError(f"Gateway error: {e}")

    def is_healthy(self) -> bool:
        """Quick health check - returns True if gateway is responding.

        Returns:
            True if gateway responds to health check, False otherwise.
        """
        try:
            status = self.get_status()
            return status.get("healthy", False)
        except GatewayError:
            return False

    def get_sessions(self) -> list[dict[str, Any]]:
        """Get active sessions via CLI.

        Uses `openclaw status` to retrieve session information since
        the HTTP API doesn't expose session details.

        Returns:
            List of session dictionaries with keys:
                - key: Session identifier
                - kind: Session type (main, sub-agent, etc.)
                - age: How long session has been active
                - model: Model being used
                - tokens_used: Tokens consumed
                - context_pct: Context window usage percentage

        Raises:
            GatewayError: If unable to retrieve session data.
        """
        try:
            result = subprocess.run(
                ["openclaw", "status"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode != 0:
                raise GatewayError(f"openclaw status failed: {result.stderr}")

            # Parse session data from CLI output
            from openclaw_dash.collectors.openclaw_cli import (
                parse_status_output,
                status_to_sessions_data,
            )

            status = parse_status_output(result.stdout)
            data = status_to_sessions_data(status)
            return data.get("sessions", [])

        except subprocess.TimeoutExpired:
            raise GatewayError("openclaw status timed out")
        except FileNotFoundError:
            raise GatewayError("openclaw CLI not found - is OpenClaw installed?")
        except Exception as e:
            raise GatewayError(f"Failed to get sessions: {e}")

    def get_config(self) -> dict[str, Any]:
        """Get current gateway configuration via CLI.

        Uses `openclaw config` to retrieve current configuration.

        Returns:
            Dictionary containing gateway configuration.

        Raises:
            GatewayError: If unable to retrieve configuration.
        """
        try:
            result = subprocess.run(
                ["openclaw", "config", "--json"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                import json

                return json.loads(result.stdout)
            # Fall back to non-JSON output parsing
            result = subprocess.run(
                ["openclaw", "config"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                # Basic parsing of key=value output
                config: dict[str, Any] = {}
                for line in result.stdout.split("\n"):
                    if "=" in line or ":" in line:
                        sep = "=" if "=" in line else ":"
                        parts = line.split(sep, 1)
                        if len(parts) == 2:
                            key = parts[0].strip().lower().replace(" ", "_")
                            value = parts[1].strip()
                            config[key] = value
                return config
            raise GatewayError(f"openclaw config failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            raise GatewayError("openclaw config timed out")
        except FileNotFoundError:
            raise GatewayError("openclaw CLI not found")
        except Exception as e:
            raise GatewayError(f"Failed to get config: {e}")

    def patch_config(self, patch: dict[str, Any]) -> bool:
        """Patch gateway configuration via CLI.

        Uses `openclaw config set` to update configuration values.

        Args:
            patch: Dictionary of configuration keys and values to set.
                   Example: {"model": "claude-sonnet-4-20250514", "context_limit": 100000}

        Returns:
            True if all patches applied successfully.

        Raises:
            GatewayError: If unable to apply configuration changes.
        """
        errors = []
        for key, value in patch.items():
            try:
                result = subprocess.run(
                    ["openclaw", "config", "set", key, str(value)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode != 0:
                    errors.append(f"{key}: {result.stderr.strip() or 'failed'}")
            except subprocess.TimeoutExpired:
                errors.append(f"{key}: timed out")
            except Exception as e:
                errors.append(f"{key}: {e}")

        if errors:
            raise GatewayError(f"Config patch errors: {'; '.join(errors)}")
        return True

    def get_available_models(self) -> list[str]:
        """Get models available in OpenClaw config.

        Retrieves the list of configured models from the gateway.

        Returns:
            List of model identifiers (e.g., ["claude-sonnet-4-20250514", "claude-opus-4-20250514"]).

        Raises:
            GatewayError: If unable to retrieve model list.
        """
        try:
            # Try getting models from config
            config = self.get_config()

            # Look for model-related keys
            models = []

            # Check for explicit models list
            if "models" in config and isinstance(config["models"], list):
                models.extend(config["models"])

            # Check for default model
            if "model" in config:
                model = config["model"]
                if model and model not in models:
                    models.append(model)

            # Check for tier-specific models
            for tier in ["fast", "balanced", "powerful"]:
                tier_key = f"{tier}_model"
                if tier_key in config and config[tier_key]:
                    if config[tier_key] not in models:
                        models.append(config[tier_key])

            return models if models else ["claude-sonnet-4-20250514"]  # Default fallback

        except Exception as e:
            raise GatewayError(f"Failed to get available models: {e}")

    def set_model(self, model: str) -> bool:
        """Set the default model for the gateway.

        Args:
            model: Model identifier to set as default.

        Returns:
            True if model was set successfully.

        Raises:
            GatewayError: If unable to set the model.
        """
        return self.patch_config({"model": model})

    def close(self) -> None:
        """Close the HTTP client connection."""
        self._client.close()

    def __enter__(self) -> GatewayClient:
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit - closes the client."""
        self.close()
