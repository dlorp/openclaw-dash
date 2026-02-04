"""Services for openclaw-dash."""

from openclaw_dash.services.gateway_client import (
    DEFAULT_GATEWAY_URL,
    GatewayClient,
    GatewayConfig,
)
from openclaw_dash.services.model_discovery import (
    ModelDiscoveryService,
    ModelInfo,
    ModelTier,
    discover_local_models,
)

__all__ = [
    "DEFAULT_GATEWAY_URL",
    "GatewayClient",
    "GatewayConfig",
    "ModelDiscoveryService",
    "ModelInfo",
    "ModelTier",
    "discover_local_models",
]
