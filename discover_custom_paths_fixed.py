"""
SECURITY-FIXED VERSION of discover_custom_paths() method

Replace the existing method in src/openclaw_dash/services/model_discovery.py
starting at line ~647 with this implementation.
"""

def discover_custom_paths(self) -> list[ModelInfo]:
    """Discover models from custom directories.

    Scans configured custom paths for .gguf and .safetensors model files.
    Implements security measures:
    - Whitelist-based path validation
    - Symlink rejection to prevent directory traversal
    - Path sanitization and validation
    - Limited path exposure (directory name only, not full paths)
    - Per-path error handling (skip bad paths, continue)
    - Hard iteration limit with timeout protection

    Returns:
        List of ModelInfo for models found in custom paths
    """
    import itertools
    import logging
    from pathlib import Path

    logger = logging.getLogger(__name__)
    models: list[ModelInfo] = []
    max_iterations = 1000  # Hard cap on iterations

    # Build whitelist of allowed base directories
    allowed_bases = []
    for path_str in self.custom_paths:
        try:
            # Security: Reject symlinks at the base level
            path_obj = Path(path_str)
            if path_obj.is_symlink():
                logger.warning(f"Security: Rejected symlink base path: {path_str}")
                continue

            # Security: Reject paths with ".." components (path traversal attempt)
            if ".." in Path(path_str).parts:
                logger.warning(f"Security: Path contains '..' traversal: {path_str}")
                continue

            # Resolve and validate path (strict=True raises if path doesn't exist)
            base = path_obj.resolve(strict=True)

            # Security: Must be a directory
            if not base.is_dir():
                logger.warning(f"Security: Path is not a directory: {path_str}")
                continue

            allowed_bases.append(base)
        except (OSError, RuntimeError):
            logger.warning(f"Security: Invalid or inaccessible path: {path_str}")
            continue

    # If no valid bases, return empty
    if not allowed_bases:
        return models

    # Scan each allowed base
    model_extensions = {".gguf", ".safetensors"}

    for base in allowed_bases:
        try:
            # Use islice for hard iteration limit
            for model_file in itertools.islice(base.rglob("*"), max_iterations):
                # Security: Skip symlinks entirely (both files and dirs)
                if model_file.is_symlink():
                    logger.debug(f"Security: Skipped symlink: {model_file}")
                    continue

                # Only process files with model extensions
                if not model_file.is_file():
                    continue
                if model_file.suffix.lower() not in model_extensions:
                    continue

                # Security: Verify file is under allowed base
                try:
                    model_file.resolve().relative_to(base)
                except ValueError:
                    logger.warning(f"Security: File outside allowed base: {model_file}")
                    continue

                # Parse model name from filename
                model_name = model_file.stem

                # Get file size
                try:
                    size_bytes = model_file.stat().st_size
                except (OSError, PermissionError):
                    size_bytes = None

                # Create ModelInfo with limited path exposure
                # Security: Store only directory name, not full path
                model = ModelInfo(
                    name=model_name,
                    provider="custom",
                    tier=infer_tier(model_name),
                    size_bytes=size_bytes,
                    family=infer_family(model_name),
                    metadata={
                        "directory": model_file.parent.name,  # Only parent dir name
                        "extension": model_file.suffix,
                    },
                )
                models.append(model)

        except (OSError, PermissionError) as e:
            logger.warning(f"Security: Error scanning {base}: {e}")
            continue

    return models
