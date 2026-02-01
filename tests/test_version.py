"""Tests for version module."""

from unittest.mock import patch

from openclaw_dash.version import VERSION, VersionInfo, get_version_info


class TestVersionInfo:
    """Tests for VersionInfo dataclass."""

    def test_short_commit_with_hash(self):
        """Test short_commit returns first 7 chars."""
        info = VersionInfo(
            version="1.0.0",
            git_commit="abc1234567890",
            git_branch="main",
            build_date="2024-01-01",
        )
        assert info.short_commit == "abc1234"

    def test_short_commit_without_hash(self):
        """Test short_commit returns 'unknown' when no commit."""
        info = VersionInfo(
            version="1.0.0",
            git_commit=None,
            git_branch=None,
            build_date=None,
        )
        assert info.short_commit == "unknown"

    def test_format_short(self):
        """Test short format for footer display."""
        info = VersionInfo(
            version="1.0.0",
            git_commit="abc1234567890",
            git_branch="main",
            build_date=None,
        )
        assert info.format_short() == "v1.0.0 abc1234"

    def test_format_short_no_commit(self):
        """Test short format without git info."""
        info = VersionInfo(
            version="1.0.0",
            git_commit=None,
            git_branch=None,
            build_date=None,
        )
        assert info.format_short() == "v1.0.0"

    def test_format_full_main_branch(self):
        """Test full format on main branch."""
        info = VersionInfo(
            version="1.0.0",
            git_commit="abc1234567890",
            git_branch="main",
            build_date=None,
        )
        assert info.format_full() == "openclaw-dash v1.0.0 (abc1234)"

    def test_format_full_feature_branch(self):
        """Test full format shows branch name when not main."""
        info = VersionInfo(
            version="1.0.0",
            git_commit="abc1234567890",
            git_branch="feature/test",
            build_date=None,
        )
        assert info.format_full() == "openclaw-dash v1.0.0 (abc1234) [feature/test]"

    def test_format_full_no_git(self):
        """Test full format without git info."""
        info = VersionInfo(
            version="1.0.0",
            git_commit=None,
            git_branch=None,
            build_date=None,
        )
        assert info.format_full() == "openclaw-dash v1.0.0"


class TestGetVersionInfo:
    """Tests for get_version_info function."""

    def test_returns_version_info(self):
        """Test that get_version_info returns a VersionInfo object."""
        info = get_version_info()
        assert isinstance(info, VersionInfo)
        assert info.version == VERSION

    def test_version_matches_constant(self):
        """Test version matches the VERSION constant."""
        info = get_version_info()
        assert info.version == "0.1.0"

    @patch("openclaw_dash.version._run_git")
    def test_handles_git_failure(self, mock_run_git):
        """Test graceful handling of git command failures."""
        mock_run_git.return_value = None

        # Clear the cache to test with mocked git
        get_version_info.cache_clear()

        info = get_version_info()
        assert info.version == VERSION
        assert info.git_commit is None
        assert info.git_branch is None

        # Restore cache
        get_version_info.cache_clear()


class TestVersionConstant:
    """Tests for VERSION constant."""

    def test_version_format(self):
        """Test VERSION follows semantic versioning format."""
        import re

        pattern = r"^\d+\.\d+\.\d+(-\w+)?$"
        assert re.match(pattern, VERSION), f"VERSION '{VERSION}' doesn't match semver"

    def test_version_matches_init(self):
        """Test VERSION matches __init__.__version__."""
        import openclaw_dash

        assert openclaw_dash.__version__ == VERSION
