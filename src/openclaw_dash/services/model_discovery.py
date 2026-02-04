"""Model discovery service via OpenClaw gateway.

Queries OpenClaw gateway API to discover available models.
The gateway is the source of truth for model availability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openclaw_dash.services.gateway_client import GatewayClient


class ModelTier(str, Enum):
    """Performance tier for models based on size and capabilities."""

    FAST = "fast"  # <8B params, optimized for speed
    BALANCED = "balanced"  # 8-30B params, good balance
    POWERFUL = "powerful"  # >30B params or reasoning models


@dataclass
class ModelInfo:
    """Information about a model available via OpenClaw."""

    # Core identification
    name: str  # Model name/ID (e.g., "anthropic/claude-sonnet-4-20250514")
    family: str  # Model family (e.g., "claude", "gpt", "gemini")

    # Model characteristics
    tier: ModelTier  # Performance tier
    size_billions: float | None = None  # Parameter count if known
    quantization: str | None = None  # Quantization level if applicable

    # Capabilities
    is_instruct: bool = True  # Chat/instruct tuned (most API models are)
    is_coder: bool = False  # Code-specialized
    is_reasoning: bool = False  # Thinking/reasoning model

    # Optional metadata
    version: str | None = None  # e.g., "4", "3.5"
    variant: str | None = None  # e.g., "turbo", "sonnet", "opus"
    provider: str | None = None  # e.g., "anthropic", "openai", "google"

    @property
    def display_name(self) -> str:
        """Human-readable display name."""
        if self.variant:
            return f"{self.family.title()} {self.variant.title()}"
        return self.family.title()

    @property
    def tier_emoji(self) -> str:
        """Emoji representing the tier."""
        return {"fast": "⚡", "balanced": "⚖️", "powerful": "🧠"}[self.tier.value]


@dataclass
class DiscoveryResult:
    """Result of model discovery from gateway."""

    models: list[ModelInfo] = field(default_factory=list)
    gateway_connected: bool = False

    @property
    def by_tier(self) -> dict[ModelTier, list[ModelInfo]]:
        """Group models by tier."""
        result: dict[ModelTier, list[ModelInfo]] = {tier: [] for tier in ModelTier}
        for model in self.models:
            result[model.tier].append(model)
        return result


class ModelDiscoveryService:
    """Service for discovering models via OpenClaw gateway.

    Queries the OpenClaw gateway API to get available models.
    The gateway is the single source of truth.
    """

    # Tier thresholds (in billions of parameters)
    FAST_THRESHOLD = 8.0  # <8B = FAST
    POWERFUL_THRESHOLD = 30.0  # >=30B = POWERFUL

    # Keywords that indicate reasoning/thinking models
    REASONING_KEYWORDS = {"r1", "o1", "o3", "reasoning", "think", "opus"}

    # Keywords that indicate code-specialized models
    CODER_KEYWORDS = {"code", "coder", "codex", "starcoder", "deepseek-coder"}

    def __init__(
        self,
        client: GatewayClient,
        *,
        fast_threshold: float = 8.0,
        powerful_threshold: float = 30.0,
    ) -> None:
        """Initialize model discovery service.

        Args:
            client: GatewayClient instance for gateway communication.
            fast_threshold: Max size in billions for FAST tier.
            powerful_threshold: Min size in billions for POWERFUL tier.
        """
        self.client = client
        self.fast_threshold = fast_threshold
        self.powerful_threshold = powerful_threshold

    def discover(self) -> DiscoveryResult:
        """Discover available models from OpenClaw gateway.

        Returns:
            DiscoveryResult with models from gateway.
        """
        result = DiscoveryResult()

        try:
            model_names = self.client.get_available_models()
            result.gateway_connected = True

            for name in model_names:
                model = self._parse_model_name(name)
                result.models.append(model)

            # Sort by tier (POWERFUL first), then name
            result.models.sort(
                key=lambda m: (
                    0 if m.tier == ModelTier.POWERFUL else 1 if m.tier == ModelTier.BALANCED else 2,
                    m.name,
                )
            )

        except Exception:
            # Gateway not available - return empty result
            result.gateway_connected = False

        return result

    def _parse_model_name(self, name: str) -> ModelInfo:
        """Parse a model name string into ModelInfo.

        Model names are typically like:
        - "anthropic/claude-sonnet-4-20250514"
        - "openai/gpt-4o"
        - "google/gemini-2.0-flash"
        """
        name_lower = name.lower()

        # Extract provider from prefix
        provider = None
        family = name
        if "/" in name:
            provider, family = name.split("/", 1)

        # Detect variant from common patterns
        variant = None
        for v in ["opus", "sonnet", "haiku", "turbo", "flash", "pro", "ultra", "mini"]:
            if v in name_lower:
                variant = v
                break

        # Detect reasoning capability
        is_reasoning = any(kw in name_lower for kw in self.REASONING_KEYWORDS)

        # Detect code specialization
        is_coder = any(kw in name_lower for kw in self.CODER_KEYWORDS)

        # Assign tier based on known model characteristics
        tier = self._assign_tier(name_lower, variant, is_reasoning)

        # Extract family name (simplified)
        if provider:
            family = family.split("-")[0] if "-" in family else family

        return ModelInfo(
            name=name,
            family=family,
            tier=tier,
            is_reasoning=is_reasoning,
            is_coder=is_coder,
            variant=variant,
            provider=provider,
        )

    def _assign_tier(
        self,
        name_lower: str,
        variant: str | None,
        is_reasoning: bool,
    ) -> ModelTier:
        """Assign performance tier based on model name patterns.

        Rules:
        1. Fast/small variants (flash, mini, haiku) → FAST (check first!)
        2. Reasoning models (o1, opus, etc.) → POWERFUL
        3. Large/premium variants (opus, pro, ultra, gpt-4o) → POWERFUL
        4. Everything else → BALANCED
        """
        # Fast tier indicators (check first - mini overrides gpt-4o)
        if variant in {"flash", "mini", "haiku"}:
            return ModelTier.FAST

        # Reasoning models always POWERFUL
        if is_reasoning:
            return ModelTier.POWERFUL

        # Premium tier indicators
        if variant in {"opus", "pro", "ultra"} or "gpt-4o" in name_lower:
            return ModelTier.POWERFUL

        return ModelTier.BALANCED
