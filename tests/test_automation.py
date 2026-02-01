"""Tests for automation module."""

import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from openclaw_dash.automation.pr_auto import (
    PRAutomation, MergeConfig, CleanupConfig,
    PRInfo, BranchInfo,
    format_merge_results, format_cleanup_results,
)
from openclaw_dash.automation.deps_auto import (
    DepsAutomation, DepsConfig, UpdateResult,
    format_deps_results,
)
from openclaw_dash.automation.backup import (
    BackupVerifier, BackupConfig, FileCheck, SyncCheck, BackupReport,
    format_backup_report, format_backup_summary,
)


class TestPRAutomation:
    """Tests for PR automation."""

    def test_merge_config_defaults(self):
        """Test MergeConfig has sensible defaults."""
        config = MergeConfig()
        assert "deps/" in config.safelist
        assert config.require_ci_pass is True
        assert config.require_approval is True
        assert config.min_approvals == 1
        assert config.delete_branch_after_merge is True
        assert config.dry_run is False

    def test_cleanup_config_defaults(self):
        """Test CleanupConfig has sensible defaults."""
        config = CleanupConfig()
        assert config.max_age_days == 30
        assert "main" in config.protect_patterns
        assert config.only_merged is True
        assert config.dry_run is False

    def test_is_safe_to_merge_branch_not_in_safelist(self):
        """Test PR not in safelist is rejected."""
        pr = PRInfo(
            number=1,
            title="Test PR",
            branch="feature/test",
            state="OPEN",
            mergeable=True,
            ci_status="success",
            approvals=1,
            labels=[],
            author="test",
            created_at="2024-01-01T00:00:00Z",
            url="https://github.com/test/test/pull/1",
        )
        config = MergeConfig(safelist=["deps/"])
        
        automation = PRAutomation(Path("/tmp/test"))
        safe, reason = automation.is_safe_to_merge(pr, config)
        
        assert safe is False
        assert "not in safelist" in reason

    def test_is_safe_to_merge_deps_branch(self):
        """Test PR with deps/ prefix is safe to merge when conditions met."""
        pr = PRInfo(
            number=1,
            title="Update package",
            branch="deps/update-pkg-1.0",
            state="OPEN",
            mergeable=True,
            ci_status="success",
            approvals=1,
            labels=[],
            author="test",
            created_at="2024-01-01T00:00:00Z",
            url="https://github.com/test/test/pull/1",
        )
        config = MergeConfig()
        
        automation = PRAutomation(Path("/tmp/test"))
        safe, reason = automation.is_safe_to_merge(pr, config)
        
        assert safe is True
        assert "Ready" in reason

    def test_is_safe_to_merge_ci_pending(self):
        """Test PR with pending CI is not merged."""
        pr = PRInfo(
            number=1,
            title="Update package",
            branch="deps/update-pkg-1.0",
            state="OPEN",
            mergeable=True,
            ci_status="pending",
            approvals=1,
            labels=[],
            author="test",
            created_at="2024-01-01T00:00:00Z",
            url="https://github.com/test/test/pull/1",
        )
        config = MergeConfig()
        
        automation = PRAutomation(Path("/tmp/test"))
        safe, reason = automation.is_safe_to_merge(pr, config)
        
        assert safe is False
        assert "CI status" in reason

    def test_is_safe_to_merge_no_approval(self):
        """Test PR without approval is not merged."""
        pr = PRInfo(
            number=1,
            title="Update package",
            branch="deps/update-pkg-1.0",
            state="OPEN",
            mergeable=True,
            ci_status="success",
            approvals=0,
            labels=[],
            author="test",
            created_at="2024-01-01T00:00:00Z",
            url="https://github.com/test/test/pull/1",
        )
        config = MergeConfig()
        
        automation = PRAutomation(Path("/tmp/test"))
        safe, reason = automation.is_safe_to_merge(pr, config)
        
        assert safe is False
        assert "approvals" in reason

    def test_is_branch_protected(self):
        """Test branch protection pattern matching."""
        automation = PRAutomation(Path("/tmp/test"))
        
        patterns = ["main", "master", "release/*"]
        
        assert automation.is_branch_protected("main", patterns) is True
        assert automation.is_branch_protected("master", patterns) is True
        assert automation.is_branch_protected("release/1.0", patterns) is True
        assert automation.is_branch_protected("feature/test", patterns) is False
        assert automation.is_branch_protected("deps/update", patterns) is False

    def test_format_merge_results(self):
        """Test merge results formatting."""
        results = [
            {"pr": 1, "title": "Update A", "branch": "deps/a", "status": "merged", "reason": "Ready"},
            {"pr": 2, "title": "Update B", "branch": "deps/b", "status": "skipped", "reason": "CI pending"},
        ]
        
        output = format_merge_results(results, "test-repo")
        
        assert "test-repo" in output
        assert "Merged" in output
        assert "Skipped" in output
        assert "Update A" in output
        assert "1 merged" in output

    def test_format_cleanup_results(self):
        """Test cleanup results formatting."""
        results = [
            {"branch": "deps/old", "status": "deleted", "reason": "Stale", "author": "bot"},
            {"branch": "main", "status": "protected", "reason": "Protected"},
        ]
        
        output = format_cleanup_results(results, "test-repo")
        
        assert "test-repo" in output
        assert "Deleted" in output
        assert "deps/old" in output


class TestDepsAutomation:
    """Tests for dependency automation."""

    def test_deps_config_defaults(self):
        """Test DepsConfig has sensible defaults."""
        config = DepsConfig()
        assert len(config.repos) > 0
        assert config.max_prs_per_run == 5
        assert config.security_only is False
        assert config.dry_run is False

    def test_should_run_weekly_first_run(self):
        """Test should_run_weekly returns True on first run."""
        with patch.object(DepsAutomation, '_load_state', return_value={"last_run": None}):
            automation = DepsAutomation()
            should_run, reason = automation.should_run_weekly()
            
            assert should_run is True
            assert "First run" in reason

    def test_should_run_weekly_recent_run(self):
        """Test should_run_weekly returns False if run recently."""
        recent_run = (datetime.now() - timedelta(days=2)).isoformat()
        
        with patch.object(DepsAutomation, '_load_state', return_value={"last_run": recent_run}):
            automation = DepsAutomation()
            should_run, reason = automation.should_run_weekly()
            
            assert should_run is False
            assert "next run in" in reason

    def test_should_run_weekly_old_run(self):
        """Test should_run_weekly returns True if run > 7 days ago."""
        old_run = (datetime.now() - timedelta(days=10)).isoformat()
        
        with patch.object(DepsAutomation, '_load_state', return_value={"last_run": old_run}):
            automation = DepsAutomation()
            should_run, reason = automation.should_run_weekly()
            
            assert should_run is True
            assert "days ago" in reason

    def test_format_deps_results(self):
        """Test dependency results formatting."""
        results = [
            UpdateResult(
                repo="test-repo",
                package="requests",
                from_version="2.28.0",
                to_version="2.31.0",
                dep_type="pip",
                is_security=True,
                status="created",
                message="PR created",
                pr_url="https://github.com/test/test/pull/1",
            ),
            UpdateResult(
                repo="test-repo",
                package="flask",
                from_version="2.0.0",
                to_version="2.3.0",
                dep_type="pip",
                is_security=False,
                status="dry-run",
                message="Would create PR",
            ),
        ]
        
        output = format_deps_results(results)
        
        assert "requests" in output
        assert "2.28.0" in output
        assert "2.31.0" in output
        assert "🔒" in output  # Security icon
        assert "PRs Created" in output


class TestBackupVerifier:
    """Tests for backup verification."""

    def test_backup_config_defaults(self):
        """Test BackupConfig has sensible defaults."""
        config = BackupConfig()
        assert config.max_age_hours == 48
        assert "AGENTS.md" in config.required_files
        assert "MEMORY.md" in config.required_files

    def test_check_file_missing(self, tmp_path):
        """Test check_file for missing file."""
        config = BackupConfig(workspace_path=tmp_path)
        verifier = BackupVerifier(config)
        
        result = verifier.check_file(tmp_path / "nonexistent.md")
        
        assert result.exists is False
        assert result.status == "missing"

    def test_check_file_exists(self, tmp_path):
        """Test check_file for existing file."""
        test_file = tmp_path / "test.md"
        test_file.write_text("test content")
        
        config = BackupConfig(workspace_path=tmp_path)
        verifier = BackupVerifier(config)
        
        result = verifier.check_file(test_file)
        
        assert result.exists is True
        assert result.status == "ok"
        assert result.size_bytes == 12

    def test_check_file_empty(self, tmp_path):
        """Test check_file for empty file."""
        test_file = tmp_path / "empty.md"
        test_file.write_text("")
        
        config = BackupConfig(workspace_path=tmp_path)
        verifier = BackupVerifier(config)
        
        result = verifier.check_file(test_file)
        
        assert result.exists is True
        assert result.status == "empty"

    def test_verify_healthy_workspace(self, tmp_path):
        """Test verify returns healthy for complete workspace."""
        # Create required files
        for filename in ["AGENTS.md", "SOUL.md", "USER.md", "MEMORY.md"]:
            (tmp_path / filename).write_text(f"# {filename}\nContent here")
        
        # Create memory directory with today's file
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        today = datetime.now().strftime("%Y-%m-%d")
        (memory_dir / f"{today}.md").write_text("# Today's notes")
        
        config = BackupConfig(workspace_path=tmp_path)
        verifier = BackupVerifier(config)
        
        with patch.object(verifier, 'check_sync_status', return_value=SyncCheck(
            is_git_repo=True,
            has_remote=True,
            branch="main",
            ahead=0,
            behind=0,
            uncommitted=0,
            last_commit_date=datetime.now(),
            status="synced",
        )):
            report = verifier.verify()
        
        assert report.overall_status == "healthy"
        assert len(report.issues) == 0

    def test_verify_missing_files(self, tmp_path):
        """Test verify catches missing required files."""
        config = BackupConfig(workspace_path=tmp_path)
        verifier = BackupVerifier(config)
        
        with patch.object(verifier, 'check_sync_status', return_value=SyncCheck(
            is_git_repo=True,
            has_remote=True,
            branch="main",
            ahead=0,
            behind=0,
            uncommitted=0,
            last_commit_date=datetime.now(),
            status="synced",
        )):
            report = verifier.verify()
        
        assert report.overall_status == "critical"
        assert any("Missing required file" in issue for issue in report.issues)

    def test_format_backup_report(self):
        """Test backup report formatting."""
        report = BackupReport(
            timestamp=datetime.now(),
            workspace_path="/test/workspace",
            file_checks=[
                FileCheck(
                    path="/test/AGENTS.md",
                    exists=True,
                    size_bytes=1000,
                    last_modified=datetime.now(),
                    age_hours=1.0,
                    status="ok",
                ),
            ],
            memory_checks=[],
            sync_check=SyncCheck(
                is_git_repo=True,
                has_remote=True,
                branch="main",
                ahead=0,
                behind=0,
                uncommitted=0,
                last_commit_date=datetime.now(),
                status="synced",
            ),
            overall_status="healthy",
            issues=[],
        )
        
        output = format_backup_report(report)
        
        assert "Backup Verification" in output
        assert "healthy" in output.lower()
        assert "AGENTS.md" in output

    def test_format_backup_summary_healthy(self):
        """Test brief backup summary for healthy status."""
        report = BackupReport(
            timestamp=datetime.now(),
            workspace_path="/test/workspace",
            file_checks=[],
            memory_checks=[],
            sync_check=SyncCheck(
                is_git_repo=True,
                has_remote=True,
                branch="main",
                ahead=0,
                behind=0,
                uncommitted=0,
                last_commit_date=datetime.now(),
                status="synced",
            ),
            overall_status="healthy",
            issues=[],
        )
        
        output = format_backup_summary(report)
        
        assert "✅" in output
        assert "healthy" in output

    def test_format_backup_summary_critical(self):
        """Test brief backup summary for critical status."""
        report = BackupReport(
            timestamp=datetime.now(),
            workspace_path="/test/workspace",
            file_checks=[],
            memory_checks=[],
            sync_check=SyncCheck(
                is_git_repo=False,
                has_remote=False,
                branch="",
                ahead=0,
                behind=0,
                uncommitted=0,
                last_commit_date=None,
                status="not-a-repo",
            ),
            overall_status="critical",
            issues=["Missing required file: AGENTS.md"],
        )
        
        output = format_backup_summary(report)
        
        assert "🚨" in output
        assert "critical" in output
        assert "Missing" in output


class TestCLIIntegration:
    """Integration tests for CLI automation commands."""

    def test_cli_auto_help(self):
        """Test that auto command shows help."""
        from openclaw_dash.cli import main
        import sys
        
        with patch.object(sys, 'argv', ['openclaw-dash', 'auto', '--help']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_cli_auto_merge_dry_run(self, tmp_path):
        """Test auto merge dry-run doesn't fail."""
        from openclaw_dash.cli import cmd_auto_merge
        
        # Create a mock args object
        args = MagicMock()
        args.repos = None
        args.repo_base = str(tmp_path)
        args.safelist = None
        args.no_ci = False
        args.no_approval = False
        args.min_approvals = 1
        args.keep_branch = False
        args.dry_run = True
        args.json = False
        
        # Should not raise, just warn about missing repos
        result = cmd_auto_merge(args)
        assert result == 0

    def test_cli_auto_backup(self, tmp_path):
        """Test auto backup command."""
        from openclaw_dash.cli import cmd_auto_backup
        
        # Create required files
        for filename in ["AGENTS.md", "SOUL.md", "USER.md", "MEMORY.md"]:
            (tmp_path / filename).write_text(f"# {filename}")
        
        args = MagicMock()
        args.workspace = str(tmp_path)
        args.max_age_hours = 48
        args.brief = True
        args.json = False
        
        result = cmd_auto_backup(args)
        # May return 1 (critical) due to no git repo, but shouldn't crash
        assert result in (0, 1)
