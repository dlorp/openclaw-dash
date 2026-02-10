"""Model Manager Panel widget for managing LLMs.

This module provides widgets for monitoring and managing language models
discovered via the OpenClaw gateway, with tier-based grouping,
status indicators, and model details.

Wired to OpenClaw gateway API for model switching via GatewayClient.patch_config().
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from textual.app import ComposeResult
from textual.widgets import Static

from openclaw_dash.widgets.ascii_art import (
    STATUS_SYMBOLS,
    mini_bar,
    separator,
    status_indicator,
)

# =============================================================================
# Constants
# =============================================================================

# Phosphor amber for active models
ACTIVE_MODEL_COLOR = "#FB8B24"


class ModelStatus(Enum):
    """Model runtime status."""

    RUNNING = "running"
    STOPPED = "stopped"
    LOADING = "loading"
    ERROR = "error"
    AVAILABLE = "available"


class ModelTier(Enum):
    """Model performance tiers for routing."""

    FAST = "fast"
    BALANCED = "balanced"
    POWERFUL = "powerful"


class ModelBackend(Enum):
    """Supported model backends."""

    OLLAMA = "ollama"
    LLAMA_CPP = "llama.cpp"
    MLX = "mlx"
    UNKNOWN = "unknown"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ModelInfo:
    """Information about a discovered model.

    Mirrors synapse-engine's DiscoveredModel structure for UI display.
    """

    model_id: str
    display_name: str
    family: str
    size_params: float  # Billions of parameters
    quantization: str  # e.g., "q4_k_m", "q8_0", "f16"
    tier: ModelTier
    status: ModelStatus = ModelStatus.AVAILABLE
    backend: ModelBackend = ModelBackend.UNKNOWN

    # Optional details
    context_length: int | None = None  # Max context window
    vram_usage_mb: float | None = None  # Current VRAM usage
    vram_required_mb: float | None = None  # Estimated VRAM needed
    port: int | None = None  # Server port if running
    is_thinking: bool = False  # Reasoning/thinking model
    is_coder: bool = False  # Code-specialized
    is_instruct: bool = False  # Instruction-tuned
    enabled: bool = False  # Enabled for use

    # Runtime stats
    requests_served: int = 0
    avg_tokens_per_sec: float | None = None
    last_used_ms: int | None = None

    def get_size_display(self) -> str:
        """Get formatted size string."""
        if self.size_params >= 1:
            return f"{self.size_params:.1f}B"
        return f"{self.size_params * 1000:.0f}M"

    def get_quant_display(self) -> str:
        """Get uppercase quantization display."""
        return self.quantization.upper().replace("_", " ")

    def get_vram_display(self) -> str:
        """Get formatted VRAM usage string."""
        if self.vram_usage_mb is not None:
            if self.vram_usage_mb >= 1024:
                return f"{self.vram_usage_mb / 1024:.1f}G"
            return f"{self.vram_usage_mb:.0f}M"
        if self.vram_required_mb is not None:
            if self.vram_required_mb >= 1024:
                return f"~{self.vram_required_mb / 1024:.1f}G"
            return f"~{self.vram_required_mb:.0f}M"
        return "?"


@dataclass
class ModelManagerData:
    """Data for the model manager panel.

    Collected from model discovery service and server manager.
    """

    models: list[ModelInfo] = field(default_factory=list)
    total_vram_mb: float | None = None  # Total GPU VRAM
    used_vram_mb: float | None = None  # Currently used VRAM
    gpu_name: str | None = None  # GPU device name
    backends_available: list[ModelBackend] = field(default_factory=list)
    last_scan_ms: int | None = None
    error: str | None = None

    def get_by_tier(self, tier: ModelTier) -> list[ModelInfo]:
        """Get models in a specific tier."""
        return [m for m in self.models if m.tier == tier]

    def get_running(self) -> list[ModelInfo]:
        """Get currently running models."""
        return [m for m in self.models if m.status == ModelStatus.RUNNING]

    def get_enabled(self) -> list[ModelInfo]:
        """Get enabled models."""
        return [m for m in self.models if m.enabled]


# =============================================================================
# Status Helpers
# =============================================================================


def get_status_icon(status: ModelStatus) -> str:
    """Get icon for model status."""
    icons = {
        ModelStatus.RUNNING: STATUS_SYMBOLS["running"],
        ModelStatus.STOPPED: STATUS_SYMBOLS["stopped"],
        ModelStatus.LOADING: STATUS_SYMBOLS["pending"],
        ModelStatus.ERROR: STATUS_SYMBOLS["error"],
        ModelStatus.AVAILABLE: STATUS_SYMBOLS["circle_empty"],
    }
    return icons.get(status, "?")


def get_status_color(status: ModelStatus) -> str:
    """Get Rich color for model status."""
    colors = {
        ModelStatus.RUNNING: ACTIVE_MODEL_COLOR,
        ModelStatus.STOPPED: "dim",
        ModelStatus.LOADING: "yellow",
        ModelStatus.ERROR: "red",
        ModelStatus.AVAILABLE: "cyan",
    }
    return colors.get(status, "white")


def get_tier_icon(tier: ModelTier) -> str:
    """Get icon for model tier."""
    icons = {
        ModelTier.FAST: STATUS_SYMBOLS["lightning"],
        ModelTier.BALANCED: STATUS_SYMBOLS["diamond"],
        ModelTier.POWERFUL: STATUS_SYMBOLS["star"],
    }
    return icons.get(tier, "?")


def get_tier_color(tier: ModelTier) -> str:
    """Get Rich color for tier."""
    colors = {
        ModelTier.FAST: "green",
        ModelTier.BALANCED: "yellow",
        ModelTier.POWERFUL: "magenta",
    }
    return colors.get(tier, "white")


def get_backend_icon(backend: ModelBackend) -> str:
    """Get short label for backend."""
    labels = {
        ModelBackend.OLLAMA: "OL",
        ModelBackend.LLAMA_CPP: "LC",
        ModelBackend.MLX: "MX",
        ModelBackend.UNKNOWN: "??",
    }
    return labels.get(backend, "??")


# =============================================================================
# Widgets
# =============================================================================


class ModelManagerPanel(Static):
    """Panel for managing local LLM models.

    Displays discovered models grouped by tier with status, details,
    and VRAM usage. Supports keyboard navigation and actions.

    Keybinds (when implemented):
        s - Start selected model
        x - Stop selected model
        e - Toggle enabled
        r - Rescan models
        up/down - Navigate models
    """

    # Track selected model for keybinds
    selected_index: int = 0
    _data: ModelManagerData | None = None

    def compose(self) -> ComposeResult:
        """Compose the panel's child widgets."""
        yield Static("Loading models...", id="model-manager-content")

    def refresh_data(self, data: ModelManagerData | None = None) -> None:
        """Refresh model manager display.

        Args:
            data: Model manager data, or None to use cached/mock data.
        """
        content = self.query_one("#model-manager-content", Static)

        if data is not None:
            self._data = data

        # Use mock data if none provided (for development)
        if self._data is None:
            self._data = _get_mock_data()

        data = self._data

        if data.error:
            content.update(f"{status_indicator('error')} [bold red]Error[/]\n[dim]{data.error}[/]")
            return

        if not data.models:
            content.update("[dim]No models discovered[/]\n[dim]Check gateway connection[/]")
            return

        lines: list[str] = []

        # === Header with GPU info ===
        running = data.get_running()
        total = len(data.models)
        enabled = len(data.get_enabled())

        lines.append(f"[bold]Models:[/] {len(running)} running / {enabled} enabled / {total} total")

        # GPU/VRAM status if available
        if data.total_vram_mb is not None and data.used_vram_mb is not None:
            vram_pct = data.used_vram_mb / data.total_vram_mb if data.total_vram_mb > 0 else 0
            vram_bar = mini_bar(vram_pct, width=10)

            # Color based on usage
            if vram_pct > 0.9:
                vram_color = "red"
            elif vram_pct > 0.7:
                vram_color = "yellow"
            else:
                vram_color = "green"

            gpu_label = f" ({data.gpu_name})" if data.gpu_name else ""
            lines.append(
                f"[bold]VRAM:[/] [{vram_color}]{data.used_vram_mb / 1024:.1f}G[/]"
                f" / {data.total_vram_mb / 1024:.1f}G {vram_bar}{gpu_label}"
            )

        lines.append(separator(44, "dotted"))

        # === Models by Tier ===
        for tier in [ModelTier.POWERFUL, ModelTier.BALANCED, ModelTier.FAST]:
            tier_models = data.get_by_tier(tier)
            if not tier_models:
                continue

            tier_icon = get_tier_icon(tier)
            tier_color = get_tier_color(tier)
            tier_running = len([m for m in tier_models if m.status == ModelStatus.RUNNING])

            lines.append("")
            lines.append(
                f"[{tier_color}]{tier_icon}[/] [bold {tier_color}]{tier.value.upper()}[/] "
                f"[dim]({tier_running}/{len(tier_models)} running)[/]"
            )
            lines.append(separator(42, "thin"))

            for model in tier_models[:6]:  # Limit per tier
                lines.extend(self._render_model_line(model))

            remaining = len(tier_models) - 6
            if remaining > 0:
                lines.append(f"    [dim]... and {remaining} more[/]")

        # === Keybind hints ===
        lines.append("")
        lines.append(separator(44, "dotted"))
        lines.append("[dim]s:start  x:stop  e:enable  r:rescan[/]")

        content.update("\n".join(lines))

    def _render_model_line(self, model: ModelInfo) -> list[str]:
        """Render a single model entry.

        Args:
            model: Model info to render.

        Returns:
            List of formatted lines for the model.
        """
        lines: list[str] = []

        status_icon = get_status_icon(model.status)
        status_color = get_status_color(model.status)
        backend_label = get_backend_icon(model.backend)

        # Truncate name if needed
        name = model.display_name
        if len(name) > 24:
            name = name[:21] + "..."

        # First line: status + name + backend
        enabled_mark = "[bold]✓[/]" if model.enabled else "[dim]○[/]"
        lines.append(
            f"  [{status_color}]{status_icon}[/] {enabled_mark} [bold]{name}[/] "
            f"[dim]{backend_label}[/]"
        )

        # Second line: details (size, quant, context, VRAM)
        details: list[str] = []

        # Size
        details.append(f"{model.get_size_display()}")

        # Quantization
        details.append(f"{model.get_quant_display()}")

        # Context length
        if model.context_length:
            ctx_k = model.context_length // 1024
            details.append(f"{ctx_k}K ctx")

        # VRAM
        vram = model.get_vram_display()
        if vram != "?":
            details.append(f"VRAM:{vram}")

        # Port if running
        if model.port and model.status == ModelStatus.RUNNING:
            details.append(f":{model.port}")

        # Capabilities
        caps: list[str] = []
        if model.is_thinking:
            caps.append("")
        if model.is_coder:
            caps.append("local")

        caps_str = "".join(caps) + " " if caps else ""

        lines.append(f"    [dim]{caps_str}{' · '.join(details)}[/]")

        # Third line: stats if running
        if model.status == ModelStatus.RUNNING and model.avg_tokens_per_sec:
            lines.append(
                f"    [dim]↳ {model.avg_tokens_per_sec:.1f} tok/s · {model.requests_served} reqs[/]"
            )

        return lines


class ModelManagerSummaryPanel(Static):
    """Compact model manager summary for metric boxes.

    Shows running/total count and VRAM usage in a single line.
    """

    _data: ModelManagerData | None = None

    def compose(self) -> ComposeResult:
        """Compose the panel's child widgets."""
        yield Static("", id="model-manager-summary")

    def refresh_data(self, data: ModelManagerData | None = None) -> None:
        """Refresh the summary display.

        Args:
            data: Model manager data, or None to use cached/mock data.
        """
        content = self.query_one("#model-manager-summary", Static)

        if data is not None:
            self._data = data

        if self._data is None:
            self._data = _get_mock_data()

        data = self._data

        if data.error or not data.models:
            content.update("[dim]No models[/]")
            return

        running = len(data.get_running())
        total = len(data.models)

        # Running indicator color
        if running > 0:
            run_color = ACTIVE_MODEL_COLOR
        else:
            run_color = "dim"

        # VRAM mini bar if available
        vram_str = ""
        if data.total_vram_mb and data.used_vram_mb:
            pct = data.used_vram_mb / data.total_vram_mb
            vram_bar = mini_bar(pct, width=4)
            vram_str = f" {vram_bar}"

        content.update(f"[{run_color}]●[/] {running}/{total}{vram_str}")


class TierSummaryPanel(Static):
    """Shows model counts per tier in a compact horizontal format."""

    _data: ModelManagerData | None = None

    def compose(self) -> ComposeResult:
        """Compose the panel's child widgets."""
        yield Static("", id="tier-summary")

    def refresh_data(self, data: ModelManagerData | None = None) -> None:
        """Refresh the tier summary display."""
        content = self.query_one("#tier-summary", Static)

        if data is not None:
            self._data = data

        if self._data is None:
            self._data = _get_mock_data()

        data = self._data

        if not data.models:
            content.update("[dim]─[/]")
            return

        parts: list[str] = []
        for tier in [ModelTier.FAST, ModelTier.BALANCED, ModelTier.POWERFUL]:
            tier_models = data.get_by_tier(tier)
            running = len([m for m in tier_models if m.status == ModelStatus.RUNNING])
            total = len(tier_models)

            icon = get_tier_icon(tier)
            color = get_tier_color(tier)

            # Highlight if any running
            if running > 0:
                parts.append(f"[{color}]{icon}{running}[/]/{total}")
            else:
                parts.append(f"[dim]{icon}[/]{running}/{total}")

        content.update(" ".join(parts))


# =============================================================================
# Mock Data (for development/testing)
# =============================================================================


def _get_mock_data() -> ModelManagerData:
    """Generate mock model data for development."""
    models = [
        ModelInfo(
            model_id="deepseek_r1_8b_q4km_powerful",
            display_name="DeepSeek R1 8B",
            family="deepseek",
            size_params=8.0,
            quantization="q4_k_m",
            tier=ModelTier.POWERFUL,
            status=ModelStatus.RUNNING,
            backend=ModelBackend.LLAMA_CPP,
            context_length=32768,
            vram_usage_mb=5120,
            port=8080,
            is_thinking=True,
            enabled=True,
            requests_served=42,
            avg_tokens_per_sec=28.5,
        ),
        ModelInfo(
            model_id="qwen3_14b_q4km_powerful",
            display_name="Qwen3 14B Instruct",
            family="qwen",
            size_params=14.0,
            quantization="q4_k_m",
            tier=ModelTier.POWERFUL,
            status=ModelStatus.STOPPED,
            backend=ModelBackend.OLLAMA,
            context_length=131072,
            vram_required_mb=8192,
            is_instruct=True,
            enabled=True,
        ),
        ModelInfo(
            model_id="codellama_7b_q4km_balanced",
            display_name="CodeLlama 7B",
            family="llama",
            size_params=7.0,
            quantization="q4_k_m",
            tier=ModelTier.BALANCED,
            status=ModelStatus.AVAILABLE,
            backend=ModelBackend.OLLAMA,
            context_length=16384,
            vram_required_mb=4096,
            is_coder=True,
            enabled=False,
        ),
        ModelInfo(
            model_id="phi3_mini_q8_fast",
            display_name="Phi-3 Mini 3.8B",
            family="phi",
            size_params=3.8,
            quantization="q8_0",
            tier=ModelTier.FAST,
            status=ModelStatus.RUNNING,
            backend=ModelBackend.MLX,
            context_length=4096,
            vram_usage_mb=2048,
            port=8081,
            enabled=True,
            requests_served=156,
            avg_tokens_per_sec=45.2,
        ),
        ModelInfo(
            model_id="gemma2_2b_q4km_fast",
            display_name="Gemma 2 2B",
            family="gemma",
            size_params=2.0,
            quantization="q4_k_m",
            tier=ModelTier.FAST,
            status=ModelStatus.AVAILABLE,
            backend=ModelBackend.OLLAMA,
            context_length=8192,
            vram_required_mb=1536,
            is_instruct=True,
            enabled=True,
        ),
    ]

    return ModelManagerData(
        models=models,
        total_vram_mb=24576,  # 24GB
        used_vram_mb=7168,  # ~7GB used
        gpu_name="Apple M3 Max",
        backends_available=[ModelBackend.OLLAMA, ModelBackend.LLAMA_CPP, ModelBackend.MLX],
    )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Enums
    "ModelStatus",
    "ModelTier",
    "ModelBackend",
    # Data classes
    "ModelInfo",
    "ModelManagerData",
    # Widgets
    "ModelManagerPanel",
    "ModelManagerSummaryPanel",
    "TierSummaryPanel",
    # Helpers
    "get_status_icon",
    "get_status_color",
    "get_tier_icon",
    "get_tier_color",
    "get_backend_icon",
]
