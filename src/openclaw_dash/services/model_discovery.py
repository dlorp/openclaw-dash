"""Model discovery service for local LLM model detection.

Scans common locations (HuggingFace cache, Ollama, custom paths) for GGUF models,
parses filenames to extract metadata, and assigns performance tiers.
"""

# TODO: Integrate with OpenClaw gateway API (localhost:18789) as primary source

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator


class ModelTier(str, Enum):
    """Performance tier for models based on size and capabilities."""

    FAST = "fast"  # <8B params, optimized for speed
    BALANCED = "balanced"  # 8-30B params, good balance
    POWERFUL = "powerful"  # >30B params or reasoning models


@dataclass
class ModelInfo:
    """Information about a discovered model."""

    # Core identification
    name: str  # Display name (e.g., "Qwen2.5 Coder 14B")
    family: str  # Model family (e.g., "qwen", "llama", "deepseek")
    path: Path  # Full path to model file

    # Model characteristics
    size_billions: float  # Parameter count in billions
    quantization: str  # e.g., "q4_k_m", "q8_0", "f16"
    tier: ModelTier  # Performance tier

    # Capabilities (detected from filename)
    is_instruct: bool = False  # Chat/instruct tuned
    is_coder: bool = False  # Code-specialized
    is_reasoning: bool = False  # Thinking/reasoning model (R1, o1, etc.)

    # Source
    source: str = "unknown"  # "huggingface", "ollama", "custom"
    file_size_gb: float = 0.0  # File size in GB

    # Optional metadata
    version: str | None = None  # e.g., "2.5", "3"
    variant: str | None = None  # e.g., "VL", "R1", "coder"

    def __post_init__(self) -> None:
        """Ensure path is a Path object."""
        if isinstance(self.path, str):
            self.path = Path(self.path)

    @property
    def display_name(self) -> str:
        """Human-readable display name."""
        parts = [self.family.title()]
        if self.version:
            parts[0] = f"{parts[0]}{self.version}"
        if self.variant:
            parts.append(self.variant.upper())
        parts.append(f"{self.size_billions:.0f}B")
        return " ".join(parts)

    @property
    def tier_emoji(self) -> str:
        """Emoji representing the tier."""
        return {"fast": "⚡", "balanced": "⚖️", "powerful": "🧠"}[self.tier.value]

    @property
    def filename(self) -> str:
        """Just the filename without path."""
        return self.path.name


@dataclass
class DiscoveryResult:
    """Result of model discovery scan."""

    models: list[ModelInfo] = field(default_factory=list)
    scan_paths: list[Path] = field(default_factory=list)
    ollama_running: bool = False
    llamacpp_running: bool = False

    @property
    def by_tier(self) -> dict[ModelTier, list[ModelInfo]]:
        """Group models by tier."""
        result: dict[ModelTier, list[ModelInfo]] = {tier: [] for tier in ModelTier}
        for model in self.models:
            result[model.tier].append(model)
        return result

    @property
    def total_size_gb(self) -> float:
        """Total size of all discovered models in GB."""
        return sum(m.file_size_gb for m in self.models)


class ModelDiscoveryService:
    """Service for discovering local LLM models.

    Scans HuggingFace cache, Ollama models directory, and custom paths
    for GGUF model files. Parses filenames to extract metadata and
    assigns performance tiers.
    """

    # GGUF filename patterns (adapted from synapse-engine)
    # Pattern 1: qwen2.5-coder-14b-instruct-q4_k_m.gguf
    PATTERN_SIMPLE = re.compile(
        r"^(?P<family>[\w]+)"
        r"(?P<version>[\d.]+)?"
        r"(?:-(?P<variant>[\w-]+?))?"
        r"-(?P<size>\d+)b"
        r"(?:-(?P<suffix>instruct|chat|coder))?"
        r"-(?P<quant>q\d+_[\w]+|f\d+)"
        r"\.gguf$",
        re.IGNORECASE,
    )

    # Pattern 2: DeepSeek-R1-0528-Qwen3-8B-Q4_K_M.gguf
    PATTERN_COMPLEX = re.compile(
        r"^(?P<family>[\w]+)"
        r"-(?P<variant>[\w\d]+)"
        r"(?:-(?P<version>[\d]+))?"
        r"(?:-(?P<submodel>[\w\d]+))?"
        r"-(?P<size>\d+)B"
        r"(?:-(?P<suffix>Instruct|Chat|Coder))?"
        r"-(?P<quant>Q\d+_[\w]+|F\d+)"
        r"\.gguf$"
    )

    # Pattern 3: model-20b-Q4_K_M.gguf (minimal format)
    PATTERN_MINIMAL = re.compile(
        r"^(?P<family>[\w-]+?)"
        r"-(?P<size>\d+)[bB]"
        r"-(?P<quant>[qQfF]\d+_[\w]+|[fF]\d+)"
        r"\.gguf$",
        re.IGNORECASE,
    )

    # Keywords that indicate reasoning/thinking models
    REASONING_KEYWORDS = {"r1", "o1", "reasoning", "think", "cot"}

    # Tier thresholds (in billions of parameters)
    FAST_THRESHOLD = 8.0  # <8B = FAST
    POWERFUL_THRESHOLD = 30.0  # >=30B = POWERFUL

    def __init__(
        self,
        custom_paths: list[Path] | None = None,
        *,
        fast_threshold: float = 8.0,
        powerful_threshold: float = 30.0,
    ) -> None:
        """Initialize model discovery service.

        Args:
            custom_paths: Additional paths to scan for models.
            fast_threshold: Max size in billions for FAST tier.
            powerful_threshold: Min size in billions for POWERFUL tier.
        """
        self.custom_paths = custom_paths or []
        self.fast_threshold = fast_threshold
        self.powerful_threshold = powerful_threshold

    def discover(self) -> DiscoveryResult:
        """Discover all local models.

        Scans:
        - ~/.cache/huggingface/hub/ for GGUF files
        - ~/.ollama/models/ for Ollama models
        - Any custom paths configured

        Returns:
            DiscoveryResult with all found models and runtime status.
        """
        result = DiscoveryResult()

        # Standard scan locations
        hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
        ollama_dir = Path.home() / ".ollama" / "models"

        # Scan HuggingFace cache
        if hf_cache.exists():
            result.scan_paths.append(hf_cache)
            for model in self._scan_huggingface(hf_cache):
                result.models.append(model)

        # Scan Ollama directory
        if ollama_dir.exists():
            result.scan_paths.append(ollama_dir)
            for model in self._scan_ollama(ollama_dir):
                result.models.append(model)

        # Scan custom paths
        for path in self.custom_paths:
            if path.exists() and path.is_dir():
                result.scan_paths.append(path)
                for model in self._scan_directory(path, source="custom"):
                    result.models.append(model)

        # Check running servers
        result.ollama_running = self._is_ollama_running()
        result.llamacpp_running = self._is_llamacpp_running()

        # Sort by tier (POWERFUL first), then size (descending)
        result.models.sort(
            key=lambda m: (
                0 if m.tier == ModelTier.POWERFUL else 1 if m.tier == ModelTier.BALANCED else 2,
                -m.size_billions,
            )
        )

        return result

    def _scan_huggingface(self, hf_cache: Path) -> Iterator[ModelInfo]:
        """Scan HuggingFace cache for GGUF files.

        HuggingFace stores models in subdirectories like:
        ~/.cache/huggingface/hub/models--org--model-name/snapshots/hash/*.gguf
        """
        for gguf_file in hf_cache.rglob("*.gguf"):
            model = self._parse_gguf_file(gguf_file, source="huggingface")
            if model:
                yield model

    def _scan_ollama(self, ollama_dir: Path) -> Iterator[ModelInfo]:
        """Scan Ollama models directory.

        Ollama stores model blobs and manifests. We look for the
        manifest files to understand what models are available.
        """
        manifests_dir = ollama_dir / "manifests" / "registry.ollama.ai" / "library"
        if not manifests_dir.exists():
            return

        for model_dir in manifests_dir.iterdir():
            if not model_dir.is_dir():
                continue

            model_name = model_dir.name
            # List available tags
            for tag_file in model_dir.iterdir():
                if tag_file.is_file():
                    tag = tag_file.name
                    # Create a synthetic ModelInfo for Ollama models
                    model = self._create_ollama_model_info(model_name, tag, ollama_dir)
                    if model:
                        yield model

    def _scan_directory(self, path: Path, source: str = "custom") -> Iterator[ModelInfo]:
        """Scan a directory recursively for GGUF files."""
        for gguf_file in path.rglob("*.gguf"):
            model = self._parse_gguf_file(gguf_file, source=source)
            if model:
                yield model

    def _parse_gguf_file(self, file_path: Path, source: str) -> ModelInfo | None:
        """Parse GGUF filename and create ModelInfo.

        Tries multiple regex patterns to extract model metadata.
        """
        filename = file_path.name

        # Try each pattern
        for pattern in [self.PATTERN_SIMPLE, self.PATTERN_COMPLEX, self.PATTERN_MINIMAL]:
            match = pattern.match(filename)
            if match:
                return self._create_model_info_from_match(file_path, match.groupdict(), source)

        return None

    def _create_model_info_from_match(
        self,
        file_path: Path,
        groups: dict[str, str | None],
        source: str,
    ) -> ModelInfo | None:
        """Create ModelInfo from regex match groups."""
        try:
            family = (groups.get("family") or "unknown").lower()
            size_str = groups.get("size")
            quant_str = groups.get("quant")

            if not size_str or not quant_str:
                return None

            size_billions = float(size_str)
            quantization = quant_str.lower()

            # Detect capabilities from filename
            filename_lower = file_path.name.lower()
            suffix = (groups.get("suffix") or "").lower()
            variant = groups.get("variant") or groups.get("submodel")

            is_instruct = any(
                kw in filename_lower for kw in ("instruct", "chat", "it")
            ) or suffix in ("instruct", "chat")
            is_coder = "coder" in filename_lower or suffix == "coder"
            is_reasoning = self._is_reasoning_model(filename_lower, variant)

            # Calculate tier
            tier = self._assign_tier(size_billions, quantization, is_reasoning)

            # Get file size
            try:
                file_size_gb = file_path.stat().st_size / (1024**3)
            except OSError:
                file_size_gb = 0.0

            # Build display name
            name_parts = [family.title()]
            version = groups.get("version")
            if version:
                name_parts[0] = f"{name_parts[0]}{version}"
            if variant:
                name_parts.append(variant)
            name_parts.append(f"{size_billions:.0f}B")
            name = " ".join(name_parts)

            return ModelInfo(
                name=name,
                family=family,
                path=file_path,
                size_billions=size_billions,
                quantization=quantization,
                tier=tier,
                is_instruct=is_instruct,
                is_coder=is_coder,
                is_reasoning=is_reasoning,
                source=source,
                file_size_gb=file_size_gb,
                version=version,
                variant=variant,
            )
        except (ValueError, TypeError):
            return None

    def _create_ollama_model_info(
        self,
        model_name: str,
        tag: str,
        ollama_dir: Path,
    ) -> ModelInfo | None:
        """Create ModelInfo for an Ollama model.

        Since Ollama uses a different format, we infer what we can
        from the model name and tag.
        """
        # Try to parse size from tag (e.g., "7b", "13b-q4_0")
        size_match = re.search(r"(\d+)b", tag.lower())
        size_billions = float(size_match.group(1)) if size_match else 7.0  # Default guess

        # Try to parse quantization
        quant_match = re.search(r"(q\d+_[\w]+|f\d+)", tag.lower())
        quantization = quant_match.group(1) if quant_match else "unknown"

        # Detect capabilities
        name_lower = model_name.lower()
        is_instruct = any(kw in name_lower for kw in ("instruct", "chat"))
        is_coder = "code" in name_lower
        is_reasoning = self._is_reasoning_model(name_lower, None)

        tier = self._assign_tier(size_billions, quantization, is_reasoning)

        return ModelInfo(
            name=f"{model_name}:{tag}",
            family=model_name.split("-")[0].lower() if "-" in model_name else model_name.lower(),
            path=ollama_dir / "manifests" / "registry.ollama.ai" / "library" / model_name / tag,
            size_billions=size_billions,
            quantization=quantization,
            tier=tier,
            is_instruct=is_instruct,
            is_coder=is_coder,
            is_reasoning=is_reasoning,
            source="ollama",
            file_size_gb=0.0,  # Can't easily determine for Ollama
        )

    def _is_reasoning_model(self, filename_lower: str, variant: str | None) -> bool:
        """Check if model is a reasoning/thinking model."""
        # Check filename
        if any(kw in filename_lower for kw in self.REASONING_KEYWORDS):
            return True

        # Check variant
        if variant and any(kw in variant.lower() for kw in self.REASONING_KEYWORDS):
            return True

        return False

    def _assign_tier(
        self,
        size_billions: float,
        quantization: str,
        is_reasoning: bool,
    ) -> ModelTier:
        """Assign performance tier based on model characteristics.

        Rules:
        1. Reasoning models → POWERFUL (always)
        2. Size >= powerful_threshold → POWERFUL
        3. Size < fast_threshold AND low quantization → FAST
        4. Everything else → BALANCED
        """
        # Reasoning models always go to POWERFUL
        if is_reasoning:
            return ModelTier.POWERFUL

        # Large models go to POWERFUL
        if size_billions >= self.powerful_threshold:
            return ModelTier.POWERFUL

        # Small models with efficient quantization go to FAST
        low_quants = {"q2_k", "q3_k", "q3_k_m", "q4_0", "q4_k", "q4_k_m", "q4_k_s"}
        if size_billions < self.fast_threshold and quantization in low_quants:
            return ModelTier.FAST

        return ModelTier.BALANCED

    def _is_ollama_running(self) -> bool:
        """Check if Ollama server is running."""
        # Check if ollama binary exists
        if not shutil.which("ollama"):
            return False

        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                timeout=5,
                check=False,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False

    def _is_llamacpp_running(self) -> bool:
        """Check if llama.cpp server is running (common ports)."""
        import socket

        common_ports = [8080, 8081, 8082]

        for port in common_ports:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.5)
                    result = s.connect_ex(("127.0.0.1", port))
                    if result == 0:
                        return True
            except OSError:
                continue

        return False


def discover_local_models(
    custom_paths: list[Path] | None = None,
) -> DiscoveryResult:
    """Convenience function to discover local models.

    Args:
        custom_paths: Additional paths to scan for models.

    Returns:
        DiscoveryResult with all found models.
    """
    service = ModelDiscoveryService(custom_paths=custom_paths)
    return service.discover()
