"""Model discovery and management service.

Discovers LLM models from:
1. Local providers (Ollama, LM Studio, vLLM)
2. OpenClaw gateway API (remote models)
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from openclaw_dash.services.gateway_client import GatewayClient


class ModelTier(str, Enum):
    """Model performance tiers for categorization."""

    FAST = "fast"  # Small, quick models (< 7B params)
    BALANCED = "balanced"  # Medium models (7B-30B params)
    POWERFUL = "powerful"  # Large models (30B+ params)
    UNKNOWN = "unknown"


# Model parameter count thresholds (in billions)
TIER_THRESHOLDS = {
    ModelTier.FAST: 7,
    ModelTier.BALANCED: 30,
}

# Known model size patterns for tier inference
MODEL_SIZE_PATTERNS = {
    # Fast tier
    "1b": ModelTier.FAST,
    "3b": ModelTier.FAST,
    "1.5b": ModelTier.FAST,
    "2b": ModelTier.FAST,
    "4b": ModelTier.FAST,
    "7b": ModelTier.FAST,
    "8b": ModelTier.FAST,
    # Balanced tier
    "13b": ModelTier.BALANCED,
    "14b": ModelTier.BALANCED,
    "20b": ModelTier.BALANCED,
    "22b": ModelTier.BALANCED,
    "27b": ModelTier.BALANCED,
    "32b": ModelTier.BALANCED,
    # Powerful tier
    "70b": ModelTier.POWERFUL,
    "72b": ModelTier.POWERFUL,
    "105b": ModelTier.POWERFUL,
    "180b": ModelTier.POWERFUL,
    "405b": ModelTier.POWERFUL,
}

# Keywords that indicate reasoning/thinking models
REASONING_KEYWORDS = {"r1", "o1", "o3", "reasoning", "think", "opus"}

# Keywords that indicate code-specialized models
CODER_KEYWORDS = {"code", "coder", "codex", "starcoder", "deepseek-coder"}


# Configuration schema for model manager settings
CONFIG_SCHEMA = {
    "model_manager": {
        "type": "object",
        "description": "Model manager configuration",
        "properties": {
            "ollama_host": {
                "type": "string",
                "default": "http://localhost:11434",
                "description": "Ollama API host URL",
            },
            "lm_studio_host": {
                "type": "string",
                "default": "http://localhost:1234",
                "description": "LM Studio API host URL",
            },
            "vllm_host": {
                "type": "string",
                "default": "http://localhost:8000",
                "description": "vLLM API host URL",
            },
            "discovery_timeout": {
                "type": "integer",
                "default": 5,
                "description": "Timeout in seconds for model discovery",
            },
            "cache_ttl": {
                "type": "integer",
                "default": 60,
                "description": "Cache TTL in seconds for model lists",
            },
        },
    }
}


@dataclass
class ModelInfo:
    """Information about a discovered model."""

    name: str
    provider: str  # ollama, lm-studio, vllm, openai, anthropic, etc.
    tier: ModelTier = ModelTier.UNKNOWN
    size_bytes: int | None = None
    size_billions: float | None = None  # Parameter count if known
    parameter_count: str | None = None  # e.g., "7B", "70B"
    quantization: str | None = None  # e.g., "Q4_K_M", "fp16"
    family: str | None = None  # e.g., "llama", "mistral", "qwen", "claude"
    running: bool = False
    context_length: int | None = None
    modified_at: datetime | None = None
    digest: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # Capability flags
    is_instruct: bool = True  # Chat/instruct tuned
    is_coder: bool = False  # Code-specialized
    is_reasoning: bool = False  # Thinking/reasoning model

    # Optional metadata for API models
    version: str | None = None  # e.g., "4", "3.5"
    variant: str | None = None  # e.g., "turbo", "sonnet", "opus"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "provider": self.provider,
            "tier": self.tier.value,
            "size_bytes": self.size_bytes,
            "size_billions": self.size_billions,
            "parameter_count": self.parameter_count,
            "quantization": self.quantization,
            "family": self.family,
            "running": self.running,
            "context_length": self.context_length,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
            "digest": self.digest,
            "is_coder": self.is_coder,
            "is_reasoning": self.is_reasoning,
            "variant": self.variant,
            "metadata": self.metadata,
        }

    @property
    def size_gb(self) -> float | None:
        """Get size in gigabytes."""
        if self.size_bytes:
            return self.size_bytes / (1024**3)
        return None

    @property
    def display_size(self) -> str:
        """Get human-readable size string."""
        if self.size_bytes is None:
            return "?"
        gb = self.size_gb
        if gb and gb >= 1:
            return f"{gb:.1f}GB"
        mb = self.size_bytes / (1024**2)
        return f"{mb:.0f}MB"

    @property
    def display_name(self) -> str:
        """Human-readable display name."""
        if self.variant and self.family:
            return f"{self.family.title()} {self.variant.title()}"
        if self.family:
            return self.family.title()
        return self.name

    @property
    def tier_emoji(self) -> str:
        """Glyph representing the tier."""
        return {"fast": "▸", "balanced": "◉", "powerful": "★", "unknown": "◌"}[self.tier.value]


@dataclass
class DiscoveryResult:
    """Result of model discovery."""

    models: list[ModelInfo] = field(default_factory=list)
    gateway_connected: bool = False
    local_providers: list[str] = field(default_factory=list)

    @property
    def by_tier(self) -> dict[ModelTier, list[ModelInfo]]:
        """Group models by tier."""
        result: dict[ModelTier, list[ModelInfo]] = {tier: [] for tier in ModelTier}
        for model in self.models:
            result[model.tier].append(model)
        return result

    @property
    def by_provider(self) -> dict[str, list[ModelInfo]]:
        """Group models by provider."""
        result: dict[str, list[ModelInfo]] = {}
        for model in self.models:
            if model.provider not in result:
                result[model.provider] = []
            result[model.provider].append(model)
        return result


def infer_tier(model_name: str, parameter_count: str | None = None) -> ModelTier:
    """Infer model tier from name or parameter count.

    Args:
        model_name: The model name/tag
        parameter_count: Optional explicit parameter count like "7B"

    Returns:
        Inferred ModelTier
    """
    import re

    name_lower = model_name.lower()

    # Check explicit parameter count first
    if parameter_count:
        pc_lower = parameter_count.lower().replace(" ", "")
        if pc_lower in MODEL_SIZE_PATTERNS:
            return MODEL_SIZE_PATTERNS[pc_lower]

    # Extract size from model name using regex for precise matching
    # Patterns like ":13b", "-7b", ":72b-instruct" etc.
    size_match = re.search(r"[:\-](\d+\.?\d*b)\b", name_lower)
    if size_match:
        size_str = size_match.group(1)
        if size_str in MODEL_SIZE_PATTERNS:
            return MODEL_SIZE_PATTERNS[size_str]
        # Try without decimal (e.g., "3.8b" -> check for tier by parsing)
        try:
            size_val = float(size_str.rstrip("b"))
            if size_val < 7:
                return ModelTier.FAST
            elif size_val <= 30:
                return ModelTier.BALANCED
            else:
                return ModelTier.POWERFUL
        except ValueError:
            pass

    return ModelTier.UNKNOWN


def infer_family(model_name: str) -> str | None:
    """Infer model family from name.

    Args:
        model_name: The model name

    Returns:
        Family name or None
    """
    name_lower = model_name.lower()

    # Ordered by specificity (longer/more specific patterns first)
    families = [
        "codellama",  # Before llama
        "codestral",  # Before mistral
        "command-r",
        "starcoder",
        "deepseek",
        "mixtral",  # Before mistral
        "mistral",
        "granite",
        "vicuna",
        "falcon",
        "llama",
        "gemma",
        "claude",
        "qwen",
        "phi",
        "gpt",
        "mpt",
        "aya",
        "yi",
    ]

    for family in families:
        if family in name_lower:
            return family

    return None


class ModelDiscoveryService:
    """Service for discovering and managing LLM models.

    Supports both local providers (Ollama, LM Studio, vLLM) and
    remote models via OpenClaw gateway.
    """

    # Tier thresholds (in billions of parameters)
    FAST_THRESHOLD = 8.0  # <8B = FAST
    POWERFUL_THRESHOLD = 30.0  # >=30B = POWERFUL

    def __init__(
        self,
        client: GatewayClient | None = None,
        ollama_host: str = "http://localhost:11434",
        lm_studio_host: str = "http://localhost:1234",
        vllm_host: str = "http://localhost:8000",
        timeout: int = 5,
    ):
        """Initialize the model discovery service.

        Args:
            client: Optional GatewayClient for remote model discovery
            ollama_host: Ollama API host URL
            lm_studio_host: LM Studio API host URL
            vllm_host: vLLM API host URL
            timeout: Request timeout in seconds
        """
        self.client = client
        self.ollama_host = ollama_host
        self.lm_studio_host = lm_studio_host
        self.vllm_host = vllm_host
        self.timeout = timeout
        self._cache: dict[str, tuple[datetime, list[ModelInfo]]] = {}
        self._cache_ttl = 60  # seconds

    def discover(self, include_local: bool = True, include_gateway: bool = True) -> DiscoveryResult:
        """Discover available models from all sources.

        Args:
            include_local: Include local providers (Ollama, LM Studio, vLLM)
            include_gateway: Include OpenClaw gateway models

        Returns:
            DiscoveryResult with all discovered models
        """
        result = DiscoveryResult()

        # Discover from gateway if client is available
        if include_gateway and self.client:
            try:
                model_names = self.client.get_available_models()
                result.gateway_connected = True

                for name in model_names:
                    model = self._parse_gateway_model(name)
                    result.models.append(model)

            except Exception:
                result.gateway_connected = False

        # Discover from local providers
        if include_local:
            ollama_models = self.discover_ollama()
            if ollama_models:
                result.local_providers.append("ollama")
                result.models.extend(ollama_models)

            lm_studio_models = self.discover_lm_studio()
            if lm_studio_models:
                result.local_providers.append("lm-studio")
                result.models.extend(lm_studio_models)

            vllm_models = self.discover_vllm()
            if vllm_models:
                result.local_providers.append("vllm")
                result.models.extend(vllm_models)

        # Sort by tier (POWERFUL first), then name
        result.models.sort(
            key=lambda m: (
                0 if m.tier == ModelTier.POWERFUL else 1 if m.tier == ModelTier.BALANCED else 2 if m.tier == ModelTier.FAST else 3,
                m.name,
            )
        )

        return result

    def discover_all(self) -> list[ModelInfo]:
        """Discover models from all local providers.

        Returns:
            Combined list of ModelInfo from all available providers
        """
        return self.discover(include_local=True, include_gateway=False).models

    def _parse_gateway_model(self, name: str) -> ModelInfo:
        """Parse a gateway model name string into ModelInfo.

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
        is_reasoning = any(kw in name_lower for kw in REASONING_KEYWORDS)

        # Detect code specialization
        is_coder = any(kw in name_lower for kw in CODER_KEYWORDS)

        # Assign tier based on known model characteristics
        tier = self._assign_gateway_tier(name_lower, variant, is_reasoning)

        # Extract family name (simplified)
        family_name = infer_family(name) or (family.split("-")[0] if "-" in family else family)

        return ModelInfo(
            name=name,
            family=family_name,
            tier=tier,
            is_reasoning=is_reasoning,
            is_coder=is_coder,
            variant=variant,
            provider=provider or "unknown",
        )

    def _assign_gateway_tier(
        self,
        name_lower: str,
        variant: str | None,
        is_reasoning: bool,
    ) -> ModelTier:
        """Assign performance tier for gateway models.

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

    def discover_ollama(self) -> list[ModelInfo]:
        """Discover models from Ollama.

        Uses `ollama list` CLI command for reliability.

        Returns:
            List of ModelInfo for Ollama models
        """
        models: list[ModelInfo] = []

        try:
            # Get list of all models
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            if result.returncode != 0:
                return models

            # Parse the table output
            lines = result.stdout.strip().split("\n")
            if len(lines) < 2:  # Need header + at least one model
                return models

            # Skip header line
            for line in lines[1:]:
                parts = line.split()
                if len(parts) < 2:
                    continue

                name = parts[0]
                # Format: NAME ID SIZE MODIFIED
                # e.g., "llama3.2:3b 7f41... 2.0 GB 2 weeks ago"
                size_bytes = None
                if len(parts) >= 4:
                    try:
                        size_val = float(parts[2])
                        size_unit = parts[3].upper()
                        if size_unit == "GB":
                            size_bytes = int(size_val * 1024**3)
                        elif size_unit == "MB":
                            size_bytes = int(size_val * 1024**2)
                    except (ValueError, IndexError):
                        pass

                model = ModelInfo(
                    name=name,
                    provider="ollama",
                    tier=infer_tier(name),
                    size_bytes=size_bytes,
                    family=infer_family(name),
                    digest=parts[1] if len(parts) > 1 else None,
                )
                models.append(model)

            # Check which models are running
            running_models = self._get_ollama_running()
            running_names = {m.lower() for m in running_models}
            for model in models:
                model.running = model.name.lower() in running_names

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass

        return models

    def _get_ollama_running(self) -> list[str]:
        """Get list of currently running Ollama models."""
        try:
            result = subprocess.run(
                ["ollama", "ps"],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            if result.returncode != 0:
                return []

            lines = result.stdout.strip().split("\n")
            if len(lines) < 2:
                return []

            running = []
            for line in lines[1:]:
                parts = line.split()
                if parts:
                    running.append(parts[0])
            return running

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return []

    def discover_lm_studio(self) -> list[ModelInfo]:
        """Discover models from LM Studio.

        Uses the OpenAI-compatible API endpoint.

        Returns:
            List of ModelInfo for LM Studio models
        """
        models: list[ModelInfo] = []

        try:
            import urllib.request

            url = f"{self.lm_studio_host}/v1/models"
            req = urllib.request.Request(url, headers={"Accept": "application/json"})

            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode())

            for model_data in data.get("data", []):
                model_id = model_data.get("id", "unknown")
                model = ModelInfo(
                    name=model_id,
                    provider="lm-studio",
                    tier=infer_tier(model_id),
                    family=infer_family(model_id),
                    running=True,  # If listed, it's loaded
                    metadata=model_data,
                )
                models.append(model)

        except Exception:
            pass

        return models

    def discover_vllm(self) -> list[ModelInfo]:
        """Discover models from vLLM.

        Uses the OpenAI-compatible API endpoint.

        Returns:
            List of ModelInfo for vLLM models
        """
        models: list[ModelInfo] = []

        try:
            import urllib.request

            url = f"{self.vllm_host}/v1/models"
            req = urllib.request.Request(url, headers={"Accept": "application/json"})

            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode())

            for model_data in data.get("data", []):
                model_id = model_data.get("id", "unknown")
                model = ModelInfo(
                    name=model_id,
                    provider="vllm",
                    tier=infer_tier(model_id),
                    family=infer_family(model_id),
                    running=True,  # vLLM models are always running
                    metadata=model_data,
                )
                models.append(model)

        except Exception:
            pass

        return models

    def get_running_models(self) -> list[ModelInfo]:
        """Get only currently running models.

        Returns:
            List of running ModelInfo
        """
        all_models = self.discover_all()
        return [m for m in all_models if m.running]

    def filter_by_tier(self, models: list[ModelInfo], tier: ModelTier | str) -> list[ModelInfo]:
        """Filter models by tier.

        Args:
            models: List of models to filter
            tier: Tier to filter by (ModelTier or string)

        Returns:
            Filtered list of models
        """
        if isinstance(tier, str):
            tier = ModelTier(tier.lower())
        return [m for m in models if m.tier == tier]

    def filter_by_provider(self, models: list[ModelInfo], provider: str) -> list[ModelInfo]:
        """Filter models by provider.

        Args:
            models: List of models to filter
            provider: Provider name to filter by

        Returns:
            Filtered list of models
        """
        return [m for m in models if m.provider.lower() == provider.lower()]


def discover_local_models(
    running_only: bool = False,
    tier: str | None = None,
    provider: str | None = None,
) -> list[ModelInfo]:
    """Convenience function to discover local models.

    Args:
        running_only: Only return running models
        tier: Filter by tier (fast, balanced, powerful)
        provider: Filter by provider (ollama, lm-studio, vllm)

    Returns:
        List of discovered ModelInfo
    """
    service = ModelDiscoveryService()

    if running_only:
        models = service.get_running_models()
    else:
        models = service.discover_all()

    if tier:
        models = service.filter_by_tier(models, tier)

    if provider:
        models = service.filter_by_provider(models, provider)

    return models
