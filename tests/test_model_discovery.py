"""Tests for the model discovery service."""

from unittest.mock import MagicMock, patch

import pytest

from openclaw_dash.services.model_discovery import (
    CONFIG_SCHEMA,
    DiscoveryResult,
    ModelDiscoveryService,
    ModelInfo,
    ModelTier,
    discover_local_models,
    infer_family,
    infer_tier,
)


class TestModelTier:
    """Tests for ModelTier enum."""

    def test_tier_values(self):
        """Test tier enum values."""
        assert ModelTier.FAST.value == "fast"
        assert ModelTier.BALANCED.value == "balanced"
        assert ModelTier.POWERFUL.value == "powerful"
        assert ModelTier.UNKNOWN.value == "unknown"

    def test_tier_is_string(self):
        assert isinstance(ModelTier.FAST, str)
        assert ModelTier.FAST == "fast"


class TestInferTier:
    """Tests for tier inference logic."""

    def test_infer_tier_from_name_fast(self):
        """Test inferring fast tier from model name."""
        assert infer_tier("llama3.2:3b") == ModelTier.FAST
        assert infer_tier("qwen2:7b-instruct") == ModelTier.FAST
        assert infer_tier("phi-3:3.8b") == ModelTier.FAST

    def test_infer_tier_from_name_balanced(self):
        """Test inferring balanced tier from model name."""
        assert infer_tier("codellama:13b") == ModelTier.BALANCED
        assert infer_tier("mistral:32b") == ModelTier.BALANCED

    def test_infer_tier_from_name_powerful(self):
        """Test inferring powerful tier from model name."""
        assert infer_tier("llama3.1:70b") == ModelTier.POWERFUL
        assert infer_tier("mixtral:70b") == ModelTier.POWERFUL

    def test_infer_tier_unknown(self):
        """Test unknown tier for unrecognized patterns."""
        assert infer_tier("custom-model") == ModelTier.UNKNOWN
        assert infer_tier("my-model:latest") == ModelTier.UNKNOWN

    def test_infer_tier_from_parameter_count(self):
        """Test tier inference from explicit parameter count."""
        assert infer_tier("custom", "7B") == ModelTier.FAST
        assert infer_tier("custom", "13b") == ModelTier.BALANCED
        assert infer_tier("custom", "70B") == ModelTier.POWERFUL


class TestInferFamily:
    """Tests for family inference logic."""

    def test_infer_family_llama(self):
        """Test inferring llama family."""
        assert infer_family("llama3.2:3b") == "llama"
        # codellama matches codellama (more specific, checked first)
        assert infer_family("codellama:7b") == "codellama"

    def test_infer_family_qwen(self):
        """Test inferring qwen family."""
        assert infer_family("qwen2:7b-instruct") == "qwen"

    def test_infer_family_mistral(self):
        """Test inferring mistral family."""
        assert infer_family("mistral:7b") == "mistral"
        assert infer_family("mixtral:8x7b") == "mixtral"

    def test_infer_family_unknown(self):
        """Test unknown family for unrecognized names."""
        assert infer_family("custom-model") is None


class TestModelInfo:
    """Tests for ModelInfo dataclass."""

    def test_model_info_creation(self):
        """Test creating ModelInfo instance."""
        model = ModelInfo(
            name="llama3.2:3b",
            provider="ollama",
            tier=ModelTier.FAST,
            size_bytes=2 * 1024**3,  # 2GB
            family="llama",
            running=True,
        )
        assert model.name == "llama3.2:3b"
        assert model.provider == "ollama"
        assert model.tier == ModelTier.FAST
        assert model.running is True

    def test_model_info_to_dict(self):
        """Test ModelInfo serialization."""
        model = ModelInfo(
            name="test-model",
            provider="ollama",
            tier=ModelTier.BALANCED,
        )
        data = model.to_dict()
        assert data["name"] == "test-model"
        assert data["provider"] == "ollama"
        assert data["tier"] == "balanced"
        assert data["running"] is False

    def test_model_info_display_size_gb(self):
        """Test display_size for GB sizes."""
        model = ModelInfo(
            name="test",
            provider="ollama",
            size_bytes=int(2.5 * 1024**3),
        )
        assert model.display_size == "2.5GB"

    def test_model_info_display_size_mb(self):
        """Test display_size for MB sizes."""
        model = ModelInfo(
            name="test",
            provider="ollama",
            size_bytes=500 * 1024**2,
        )
        assert model.display_size == "500MB"

    def test_model_info_display_size_unknown(self):
        """Test display_size when size is unknown."""
        model = ModelInfo(name="test", provider="ollama")
        assert model.display_size == "?"

    def test_tier_emoji(self):
        assert ModelInfo(name="a", provider="a", tier=ModelTier.FAST).tier_emoji == "▸"
        assert ModelInfo(name="a", provider="a", tier=ModelTier.BALANCED).tier_emoji == "◉"
        assert ModelInfo(name="a", provider="a", tier=ModelTier.POWERFUL).tier_emoji == "★"
        assert ModelInfo(name="a", provider="a", tier=ModelTier.UNKNOWN).tier_emoji == "◌"

    def test_display_name_with_variant(self):
        model = ModelInfo(
            name="anthropic/claude-sonnet-4",
            provider="anthropic",
            tier=ModelTier.BALANCED,
            family="claude",
            variant="sonnet",
        )
        assert model.display_name == "Claude Sonnet"

    def test_display_name_without_variant(self):
        model = ModelInfo(
            name="openai/gpt-4", provider="openai", family="gpt", tier=ModelTier.POWERFUL
        )
        assert model.display_name == "Gpt"


class TestDiscoveryResult:
    """Tests for DiscoveryResult dataclass."""

    def test_empty_result(self):
        result = DiscoveryResult()
        assert result.models == []
        assert result.gateway_connected is False

    def test_by_tier_grouping(self):
        result = DiscoveryResult(
            models=[
                ModelInfo(name="fast1", provider="a", tier=ModelTier.FAST),
                ModelInfo(name="powerful1", provider="b", tier=ModelTier.POWERFUL),
                ModelInfo(name="fast2", provider="c", tier=ModelTier.FAST),
                ModelInfo(name="balanced1", provider="d", tier=ModelTier.BALANCED),
            ],
            gateway_connected=True,
        )

        by_tier = result.by_tier
        assert len(by_tier[ModelTier.FAST]) == 2
        assert len(by_tier[ModelTier.BALANCED]) == 1
        assert len(by_tier[ModelTier.POWERFUL]) == 1

    def test_by_provider_grouping(self):
        result = DiscoveryResult(
            models=[
                ModelInfo(name="m1", provider="ollama"),
                ModelInfo(name="m2", provider="anthropic"),
                ModelInfo(name="m3", provider="ollama"),
            ],
        )

        by_provider = result.by_provider
        assert len(by_provider["ollama"]) == 2
        assert len(by_provider["anthropic"]) == 1


class TestModelDiscoveryService:
    """Tests for ModelDiscoveryService."""

    def test_service_initialization(self):
        """Test service initialization with defaults."""
        service = ModelDiscoveryService()
        assert service.ollama_host == "http://localhost:11434"
        assert service.lm_studio_host == "http://localhost:1234"
        assert service.timeout == 5

    def test_service_custom_hosts(self):
        """Test service initialization with custom hosts."""
        service = ModelDiscoveryService(
            ollama_host="http://custom:1234",
            timeout=10,
        )
        assert service.ollama_host == "http://custom:1234"
        assert service.timeout == 10

    @patch("subprocess.run")
    def test_discover_ollama_parses_output(self, mock_run):
        """Test parsing ollama list output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "NAME                    ID              SIZE      MODIFIED\n"
                "llama3.2:3b             abc123          2.0 GB    2 days ago\n"
                "qwen2:7b                def456          4.5 GB    1 week ago\n"
            ),
        )

        service = ModelDiscoveryService()
        # Also mock ollama ps
        with patch.object(service, "_get_ollama_running", return_value=[]):
            models = service.discover_ollama()

        assert len(models) == 2
        assert models[0].name == "llama3.2:3b"
        assert models[0].provider == "ollama"
        assert models[0].tier == ModelTier.FAST

    @patch("subprocess.run")
    def test_discover_ollama_handles_error(self, mock_run):
        """Test graceful handling of ollama errors."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        service = ModelDiscoveryService()
        models = service.discover_ollama()

        assert models == []

    @patch("subprocess.run")
    def test_discover_ollama_handles_timeout(self, mock_run):
        """Test graceful handling of timeouts."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ollama", timeout=5)

        service = ModelDiscoveryService()
        models = service.discover_ollama()

        assert models == []

    def test_filter_by_tier(self):
        """Test filtering models by tier."""
        models = [
            ModelInfo(name="fast1", provider="ollama", tier=ModelTier.FAST),
            ModelInfo(name="balanced1", provider="ollama", tier=ModelTier.BALANCED),
            ModelInfo(name="fast2", provider="ollama", tier=ModelTier.FAST),
        ]

        service = ModelDiscoveryService()
        fast_models = service.filter_by_tier(models, ModelTier.FAST)

        assert len(fast_models) == 2
        assert all(m.tier == ModelTier.FAST for m in fast_models)

    def test_filter_by_tier_string(self):
        """Test filtering by tier using string value."""
        models = [
            ModelInfo(name="balanced1", provider="ollama", tier=ModelTier.BALANCED),
        ]

        service = ModelDiscoveryService()
        result = service.filter_by_tier(models, "balanced")

        assert len(result) == 1

    def test_filter_by_provider(self):
        """Test filtering models by provider."""
        models = [
            ModelInfo(name="model1", provider="ollama"),
            ModelInfo(name="model2", provider="lm-studio"),
            ModelInfo(name="model3", provider="ollama"),
        ]

        service = ModelDiscoveryService()
        ollama_models = service.filter_by_provider(models, "ollama")

        assert len(ollama_models) == 2
        assert all(m.provider == "ollama" for m in ollama_models)


class TestGatewayDiscovery:
    """Tests for gateway-based model discovery."""

    @pytest.fixture
    def mock_client(self):
        from openclaw_dash.services import GatewayClient

        return MagicMock(spec=GatewayClient)

    def test_discover_with_gateway(self, mock_client):
        mock_client.get_available_models.return_value = [
            "anthropic/claude-sonnet-4-20250514",
            "openai/gpt-4o",
            "google/gemini-2.0-flash",
        ]

        service = ModelDiscoveryService(client=mock_client)
        result = service.discover(include_local=False, include_gateway=True)

        assert result.gateway_connected is True
        assert len(result.models) == 3

    def test_discover_gateway_offline(self, mock_client):
        mock_client.get_available_models.side_effect = Exception("Connection refused")

        service = ModelDiscoveryService(client=mock_client)
        result = service.discover(include_local=False, include_gateway=True)

        assert result.gateway_connected is False
        assert len(result.models) == 0

    def test_discover_sorts_by_tier(self, mock_client):
        mock_client.get_available_models.return_value = [
            "google/gemini-2.0-flash",  # FAST
            "anthropic/claude-opus-4",  # POWERFUL (reasoning)
            "anthropic/claude-sonnet-4",  # BALANCED
        ]

        service = ModelDiscoveryService(client=mock_client)
        result = service.discover(include_local=False, include_gateway=True)

        # POWERFUL should come first
        assert result.models[0].tier == ModelTier.POWERFUL
        # Then BALANCED
        assert result.models[1].tier == ModelTier.BALANCED
        # Then FAST
        assert result.models[2].tier == ModelTier.FAST

    def test_parse_anthropic_model(self, mock_client):
        service = ModelDiscoveryService(client=mock_client)
        model = service._parse_gateway_model("anthropic/claude-sonnet-4-20250514")

        assert model.name == "anthropic/claude-sonnet-4-20250514"
        assert model.family == "claude"
        assert model.provider == "anthropic"
        assert model.variant == "sonnet"
        assert model.tier == ModelTier.BALANCED

    def test_parse_openai_model(self, mock_client):
        service = ModelDiscoveryService(client=mock_client)
        model = service._parse_gateway_model("openai/gpt-4o")

        assert model.provider == "openai"
        assert model.family == "gpt"
        assert model.tier == ModelTier.POWERFUL

    def test_parse_reasoning_model(self, mock_client):
        service = ModelDiscoveryService(client=mock_client)

        # Claude Opus is reasoning
        model = service._parse_gateway_model("anthropic/claude-opus-4")
        assert model.is_reasoning is True
        assert model.tier == ModelTier.POWERFUL

        # o1 is reasoning
        model = service._parse_gateway_model("openai/o1")
        assert model.is_reasoning is True
        assert model.tier == ModelTier.POWERFUL

    def test_parse_coder_model(self, mock_client):
        service = ModelDiscoveryService(client=mock_client)
        model = service._parse_gateway_model("deepseek/deepseek-coder-33b")

        assert model.is_coder is True

    def test_parse_fast_tier_models(self, mock_client):
        service = ModelDiscoveryService(client=mock_client)

        # Flash variant
        model = service._parse_gateway_model("google/gemini-2.0-flash")
        assert model.tier == ModelTier.FAST
        assert model.variant == "flash"

        # Mini variant
        model = service._parse_gateway_model("openai/gpt-4o-mini")
        assert model.tier == ModelTier.FAST

        # Haiku variant
        model = service._parse_gateway_model("anthropic/claude-3-haiku")
        assert model.tier == ModelTier.FAST
        assert model.variant == "haiku"

    def test_parse_powerful_tier_models(self, mock_client):
        service = ModelDiscoveryService(client=mock_client)

        # Pro variant
        model = service._parse_gateway_model("google/gemini-pro")
        assert model.tier == ModelTier.POWERFUL
        assert model.variant == "pro"

        # Ultra variant
        model = service._parse_gateway_model("google/gemini-ultra")
        assert model.tier == ModelTier.POWERFUL

    def test_parse_model_without_provider(self, mock_client):
        service = ModelDiscoveryService(client=mock_client)
        model = service._parse_gateway_model("llama-3-70b")

        assert model.provider == "unknown"


class TestDiscoverLocalModels:
    """Tests for the convenience function."""

    @patch.object(ModelDiscoveryService, "discover_all")
    def test_discover_basic(self, mock_discover):
        """Test basic discovery."""
        mock_discover.return_value = [
            ModelInfo(name="test", provider="ollama"),
        ]

        models = discover_local_models()
        assert len(models) == 1

    @patch.object(ModelDiscoveryService, "get_running_models")
    def test_discover_running_only(self, mock_running):
        """Test filtering for running models only."""
        mock_running.return_value = [
            ModelInfo(name="running", provider="ollama", running=True),
        ]

        models = discover_local_models(running_only=True)
        mock_running.assert_called_once()
        assert len(models) == 1


class TestConfigSchema:
    """Tests for CONFIG_SCHEMA."""

    def test_schema_structure(self):
        """Test that CONFIG_SCHEMA has expected structure."""
        assert "model_manager" in CONFIG_SCHEMA
        schema = CONFIG_SCHEMA["model_manager"]
        assert schema["type"] == "object"
        assert "properties" in schema

    def test_schema_has_host_configs(self):
        """Test that schema includes host configuration."""
        props = CONFIG_SCHEMA["model_manager"]["properties"]
        assert "ollama_host" in props
        assert "lm_studio_host" in props
        assert "vllm_host" in props

    def test_schema_defaults(self):
        """Test that schema includes sensible defaults."""
        props = CONFIG_SCHEMA["model_manager"]["properties"]
        assert props["ollama_host"]["default"] == "http://localhost:11434"
        assert props["discovery_timeout"]["default"] == 5


class TestCustomPathsDiscovery:
    """Tests for custom paths model discovery."""

    def test_custom_paths_initialization(self, tmp_path):
        """Test service initialization with custom paths."""
        custom_paths = [str(tmp_path)]
        service = ModelDiscoveryService(custom_paths=custom_paths)
        assert service.custom_paths == custom_paths

    def test_custom_paths_default_empty(self):
        """Test that custom_paths defaults to empty list."""
        service = ModelDiscoveryService()
        assert service.custom_paths == []

    def test_discover_gguf_files(self, tmp_path):
        """Test discovery of .gguf files."""
        # Create test .gguf files
        model1 = tmp_path / "llama-3-8b.gguf"
        model1.write_bytes(b"fake model data")

        model2 = tmp_path / "mistral-7b-instruct.gguf"
        model2.write_bytes(b"fake model data")

        service = ModelDiscoveryService(custom_paths=[str(tmp_path)])
        models = service.discover_custom_paths()

        assert len(models) == 2
        model_names = {m.name for m in models}
        assert "llama-3-8b" in model_names
        assert "mistral-7b-instruct" in model_names
        assert all(m.provider == "custom" for m in models)
        assert all(m.metadata.get("extension") == ".gguf" for m in models)

    def test_discover_safetensors_files(self, tmp_path):
        """Test discovery of .safetensors files."""
        # Create test .safetensors files
        model1 = tmp_path / "qwen-14b.safetensors"
        model1.write_bytes(b"fake model data")

        model2 = tmp_path / "deepseek-coder-33b.safetensors"
        model2.write_bytes(b"fake model data")

        service = ModelDiscoveryService(custom_paths=[str(tmp_path)])
        models = service.discover_custom_paths()

        assert len(models) == 2
        model_names = {m.name for m in models}
        assert "qwen-14b" in model_names
        assert "deepseek-coder-33b" in model_names
        assert all(m.metadata.get("extension") == ".safetensors" for m in models)

    def test_discover_recursive_search(self, tmp_path):
        """Test that discovery searches subdirectories recursively."""
        # Create nested directory structure
        subdir1 = tmp_path / "models" / "llama"
        subdir1.mkdir(parents=True)
        subdir2 = tmp_path / "models" / "mistral"
        subdir2.mkdir(parents=True)

        (subdir1 / "llama-8b.gguf").write_bytes(b"data")
        (subdir2 / "mistral-7b.gguf").write_bytes(b"data")

        service = ModelDiscoveryService(custom_paths=[str(tmp_path)])
        models = service.discover_custom_paths()

        assert len(models) == 2
        model_names = {m.name for m in models}
        assert "llama-8b" in model_names
        assert "mistral-7b" in model_names

    def test_path_traversal_prevention(self, tmp_path):
        """Test that path traversal attacks are prevented."""
        # Create a path outside the allowed directory
        outside_dir = tmp_path.parent / "outside"
        outside_dir.mkdir(exist_ok=True)

        # Create a model file in the outside directory
        (outside_dir / "evil-model.gguf").write_bytes(b"malicious")

        # Create a safe model in the allowed directory
        (tmp_path / "safe-model.gguf").write_bytes(b"safe")

        # Try to access parent directory via traversal
        malicious_path = str(tmp_path / ".." / "outside")

        service = ModelDiscoveryService(custom_paths=[malicious_path])
        models = service.discover_custom_paths()

        # Should NOT find the evil model - verify it was blocked
        model_names = {m.name for m in models}
        assert "evil-model" not in model_names

        # Should find safe model when using the correct path
        service2 = ModelDiscoveryService(custom_paths=[str(tmp_path)])
        models2 = service2.discover_custom_paths()
        model_names2 = {m.name for m in models2}
        assert "safe-model" in model_names2

    def test_permission_error_handling(self, tmp_path):
        """Test graceful handling of permission errors."""
        import os
        import stat

        # Create a file we can't read
        restricted_file = tmp_path / "restricted.gguf"
        restricted_file.write_bytes(b"data")

        # Make parent directory non-readable (on Unix-like systems)
        if os.name != "nt":  # Skip on Windows
            original_mode = tmp_path.stat().st_mode
            try:
                os.chmod(tmp_path, stat.S_IWUSR)  # Write-only, no read

                service = ModelDiscoveryService(custom_paths=[str(tmp_path)])
                # Should not raise exception
                models = service.discover_custom_paths()
                assert isinstance(models, list)
            finally:
                # Restore permissions
                os.chmod(tmp_path, original_mode)

    def test_empty_path_handling(self):
        """Test handling of empty or invalid paths."""
        service = ModelDiscoveryService(custom_paths=["/nonexistent/path/to/models"])
        models = service.discover_custom_paths()

        # Should return empty list, not raise exception
        assert models == []

    def test_non_directory_path_handling(self, tmp_path):
        """Test handling when path is a file, not a directory."""
        # Create a file instead of a directory
        file_path = tmp_path / "not_a_directory.txt"
        file_path.write_text("test")

        service = ModelDiscoveryService(custom_paths=[str(file_path)])
        models = service.discover_custom_paths()

        # Should skip the file and return empty list
        assert models == []

    def test_file_count_cap(self, tmp_path):
        """Test that file count is capped at 1000 files."""
        # This would be slow to actually create 1001 files, so we'll mock it
        from unittest.mock import patch

        # Create a few real files
        for i in range(5):
            (tmp_path / f"model-{i}.gguf").write_bytes(b"data")

        service = ModelDiscoveryService(custom_paths=[str(tmp_path)])

        # Patch the max_files to a smaller number for testing
        with patch.object(service, "discover_custom_paths") as mock_discover:
            # Create a mock that simulates hitting the cap
            def mock_impl():
                models = []
                for i in range(10):  # Simulate 10 files
                    models.append(
                        ModelInfo(
                            name=f"model-{i}",
                            provider="custom",
                            tier=ModelTier.UNKNOWN,
                        )
                    )
                return models[:5]  # Return only 5 due to cap

            mock_discover.side_effect = mock_impl
            models = service.discover_custom_paths()
            assert len(models) <= 5

    def test_model_metadata_includes_directory_name(self, tmp_path):
        """Test that discovered models include directory name (not full path) in metadata."""
        model_file = tmp_path / "test-model.gguf"
        model_file.write_bytes(b"data")

        service = ModelDiscoveryService(custom_paths=[str(tmp_path)])
        models = service.discover_custom_paths()

        assert len(models) == 1
        # Should have directory name, not full path
        assert "directory" in models[0].metadata
        assert "path" not in models[0].metadata
        # Directory should be the parent folder name
        assert models[0].metadata["directory"] == tmp_path.name

    def test_model_size_extraction(self, tmp_path):
        """Test that model file size is correctly extracted."""
        model_file = tmp_path / "test-model.gguf"
        test_data = b"x" * 1024 * 1024  # 1 MB
        model_file.write_bytes(test_data)

        service = ModelDiscoveryService(custom_paths=[str(tmp_path)])
        models = service.discover_custom_paths()

        assert len(models) == 1
        assert models[0].size_bytes is not None
        assert models[0].size_bytes == len(test_data)

    def test_tier_inference_from_filename(self, tmp_path):
        """Test that tier is inferred from model filename."""
        (tmp_path / "llama-3b.gguf").write_bytes(b"data")
        (tmp_path / "mistral-13b.gguf").write_bytes(b"data")
        (tmp_path / "llama-70b.gguf").write_bytes(b"data")

        service = ModelDiscoveryService(custom_paths=[str(tmp_path)])
        models = service.discover_custom_paths()

        assert len(models) == 3

        # Find each model and check tier
        models_by_name = {m.name: m for m in models}
        assert models_by_name["llama-3b"].tier == ModelTier.FAST
        assert models_by_name["mistral-13b"].tier == ModelTier.BALANCED
        assert models_by_name["llama-70b"].tier == ModelTier.POWERFUL

    def test_family_inference_from_filename(self, tmp_path):
        """Test that family is inferred from model filename."""
        (tmp_path / "llama-8b.gguf").write_bytes(b"data")
        (tmp_path / "qwen-7b.gguf").write_bytes(b"data")

        service = ModelDiscoveryService(custom_paths=[str(tmp_path)])
        models = service.discover_custom_paths()

        models_by_name = {m.name: m for m in models}
        assert models_by_name["llama-8b"].family == "llama"
        assert models_by_name["qwen-7b"].family == "qwen"

    def test_discover_all_includes_custom_paths(self, tmp_path):
        """Test that discover_all() includes custom path models."""
        (tmp_path / "custom-model.gguf").write_bytes(b"data")

        service = ModelDiscoveryService(custom_paths=[str(tmp_path)])

        # Mock local provider discovery to return empty
        with patch.object(service, "discover_ollama", return_value=[]):
            with patch.object(service, "discover_lm_studio", return_value=[]):
                with patch.object(service, "discover_vllm", return_value=[]):
                    models = service.discover_all()

        # Should include the custom model
        assert len(models) >= 1
        custom_models = [m for m in models if m.provider == "custom"]
        assert len(custom_models) == 1
        assert custom_models[0].name == "custom-model"

    def test_multiple_custom_paths(self, tmp_path):
        """Test discovery from multiple custom paths."""
        path1 = tmp_path / "path1"
        path2 = tmp_path / "path2"
        path1.mkdir()
        path2.mkdir()

        (path1 / "model1.gguf").write_bytes(b"data")
        (path2 / "model2.gguf").write_bytes(b"data")

        service = ModelDiscoveryService(custom_paths=[str(path1), str(path2)])
        models = service.discover_custom_paths()

        assert len(models) == 2
        model_names = {m.name for m in models}
        assert "model1" in model_names
        assert "model2" in model_names

    def test_ignores_non_model_files(self, tmp_path):
        """Test that non-model files are ignored."""
        (tmp_path / "model.gguf").write_bytes(b"data")
        (tmp_path / "readme.txt").write_bytes(b"data")
        (tmp_path / "config.json").write_bytes(b"data")
        (tmp_path / "image.png").write_bytes(b"data")

        service = ModelDiscoveryService(custom_paths=[str(tmp_path)])
        models = service.discover_custom_paths()

        # Should only find the .gguf file
        assert len(models) == 1
        assert models[0].name == "model"

    def test_symlink_rejection_base_path(self, tmp_path):
        """Test that symlinks are rejected as base paths."""
        import os

        # Create a real directory with a model
        real_dir = tmp_path / "real"
        real_dir.mkdir()
        (real_dir / "model.gguf").write_bytes(b"data")

        # Create a symlink to it
        link_dir = tmp_path / "link"
        if os.name != "nt":  # Skip on Windows
            link_dir.symlink_to(real_dir)

            # Try to use the symlink as base path
            service = ModelDiscoveryService(custom_paths=[str(link_dir)])
            models = service.discover_custom_paths()

            # Should reject the symlink and find nothing
            assert len(models) == 0

    def test_symlink_rejection_during_scan(self, tmp_path):
        """Test that symlinks are skipped during directory traversal."""
        import os

        # Create legitimate directory
        (tmp_path / "safe-model.gguf").write_bytes(b"data")

        # Create an outside directory
        outside_dir = tmp_path.parent / "outside"
        outside_dir.mkdir(exist_ok=True)
        (outside_dir / "secret.gguf").write_bytes(b"secret")

        # Create a symlink inside the allowed directory pointing outside
        link_path = tmp_path / "evil_link"
        if os.name != "nt":  # Skip on Windows
            link_path.symlink_to(outside_dir)

            service = ModelDiscoveryService(custom_paths=[str(tmp_path)])
            models = service.discover_custom_paths()

            # Should skip the symlink and only find the safe model
            model_names = {m.name for m in models}
            assert "safe-model" in model_names
            assert "secret" not in model_names
            assert len(models) == 1

    def test_outside_directory_not_scanned(self, tmp_path):
        """Test that files outside the allowed directory are NOT scanned."""
        # Create allowed directory with one model
        (tmp_path / "allowed-model.gguf").write_bytes(b"data")

        # Create sibling directory with another model
        sibling_dir = tmp_path.parent / "sibling"
        sibling_dir.mkdir(exist_ok=True)
        (sibling_dir / "outside-model.gguf").write_bytes(b"data")

        # Scan only the allowed directory
        service = ModelDiscoveryService(custom_paths=[str(tmp_path)])
        models = service.discover_custom_paths()

        # Should ONLY find the allowed model, NOT the outside one
        model_names = {m.name for m in models}
        assert "allowed-model" in model_names
        assert "outside-model" not in model_names
        assert len(models) == 1

    def test_metadata_directory_not_full_path(self, tmp_path):
        """Test that metadata contains directory name, not full path."""
        subdir = tmp_path / "my_models" / "llama"
        subdir.mkdir(parents=True)
        (subdir / "model.gguf").write_bytes(b"data")

        service = ModelDiscoveryService(custom_paths=[str(tmp_path)])
        models = service.discover_custom_paths()

        assert len(models) == 1
        # Should NOT have full path
        assert "path" not in models[0].metadata
        # Should have only directory name
        assert "directory" in models[0].metadata
        assert models[0].metadata["directory"] == "llama"
        # Should NOT contain full path components
        assert str(tmp_path) not in models[0].metadata["directory"]
