"""Services for openclaw-dash."""

from openclaw_dash.services.gateway_client import (
    DEFAULT_GATEWAY_URL,
    GatewayClient,
    GatewayConfig,
)
from openclaw_dash.services.model_discovery import (
    CONFIG_SCHEMA as MODEL_CONFIG_SCHEMA,
)
from openclaw_dash.services.model_discovery import (
    DiscoveryResult,
    ModelDiscoveryService,
    ModelInfo,
    ModelTier,
    discover_local_models,
)

__all__ = [
    "DEFAULT_GATEWAY_URL",
    "DiscoveryResult",
    "GatewayClient",
    "GatewayConfig",
    "MODEL_CONFIG_SCHEMA",
    "ModelDiscoveryService",
    "ModelInfo",
    "ModelTier",
    "discover_local_models",
]
