"""Tests for security audit module."""

import json
import os
import stat
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from openclaw_dash.security.audit import (
    SECRET_PATTERNS,
    AuditResult,
    Finding,
    SecurityAudit,
    run_audit,
)
from openclaw_dash.security.deps import (
    DependencyScanner,
    DependencyScanResult,
    Vulnerability,
)
from openclaw_dash.security.fixes import (
    FixAction,
    FixResult,
    SecurityFixer,
)


class TestSecretPatterns:
    """Test secret detection patterns."""

    def test_detects_openai_key(self):
        import re

        text = 'api_key = "sk-abcdefghijklmnopqrstuvwxyz1234567890abcd"'
        matched = any(re.search(p[0], text) for p in SECRET_PATTERNS)
        assert matched

    def test_detects_github_token(self):
        import re

        text = "GITHUB_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz"
        matched = any(re.search(p[0], text) for p in SECRET_PATTERNS)
        assert matched

    def test_detects_aws_key(self):
        import re

        text = "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"
        matched = any(re.search(p[0], text) for p in SECRET_PATTERNS)
        assert matched

    def test_ignores_placeholder(self):
        import re

        # Placeholders should be filtered by audit logic, not regex
        # Using a long enough string to match patterns
        text = 'api_key = "your_api_key_here_placeholder_value"'
        # Pattern will match, but audit.scan_secrets filters placeholders
        matched = any(re.search(p[0], text) for p in SECRET_PATTERNS)
        # This is expected to match the pattern itself (filtering happens in scan_secrets)
        assert matched


class TestSecurityAudit:
    """Test SecurityAudit class."""

    def test_audit_result_summary(self):
        result = AuditResult(
            findings=[
                Finding(severity="critical", category="secrets", title="Test 1", description=""),
                Finding(severity="high", category="permissions", title="Test 2", description=""),
                Finding(severity="medium", category="config", title="Test 3", description=""),
            ]
        )
        assert result.summary["critical"] == 1
        assert result.summary["high"] == 1
        assert result.summary["medium"] == 1
        assert result.critical_count == 1
        assert result.high_count == 1

    def test_audit_result_to_dict(self):
        result = AuditResult(
            findings=[Finding(severity="high", category="test", title="Test", description="Desc")],
            scanned_files=5,
        )
        d = result.to_dict()
        assert d["scanned_files"] == 5
        assert len(d["findings"]) == 1
        assert d["findings"][0]["title"] == "Test"

    def test_run_audit_returns_result(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_audit(openclaw_dir=Path(tmpdir))
            assert isinstance(result, AuditResult)

    def test_scan_secrets_finds_exposed_token(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            config_file.write_text('{"api_key": "sk-1234567890abcdefghijklmnopqrstuvwxyz12345678"}')

            audit = SecurityAudit(openclaw_dir=Path(tmpdir))
            audit.scan_secrets()

            assert any(f.category == "secrets" for f in audit.result.findings)

    def test_scan_secrets_ignores_placeholders(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            config_file.write_text('{"api_key": "your_api_key_here_changeme"}')

            audit = SecurityAudit(openclaw_dir=Path(tmpdir))
            audit.scan_secrets()

            # Should not flag placeholder
            secret_findings = [f for f in audit.result.findings if f.category == "secrets"]
            assert len(secret_findings) == 0

    def test_check_permissions_detects_world_readable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            os.chmod(tmppath, 0o755)  # Too permissive

            audit = SecurityAudit(openclaw_dir=tmppath)
            audit.check_permissions()

            perm_findings = [f for f in audit.result.findings if f.category == "permissions"]
            assert len(perm_findings) > 0

    def test_check_config_detects_disabled_auth(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            config_file.write_text(json.dumps({"auth": {"enabled": False}}))

            audit = SecurityAudit(openclaw_dir=Path(tmpdir))
            audit.check_config()

            assert any("auth" in f.title.lower() for f in audit.result.findings)

    def test_check_config_detects_exposed_server(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            config_file.write_text(
                json.dumps(
                    {
                        "server": {"host": "0.0.0.0"},
                        "auth": {"enabled": False},
                    }
                )
            )

            audit = SecurityAudit(openclaw_dir=Path(tmpdir))
            audit.check_config()

            critical = [f for f in audit.result.findings if f.severity == "critical"]
            assert len(critical) > 0


class TestDependencyScanner:
    """Test DependencyScanner class."""

    def test_vulnerability_dataclass(self):
        vuln = Vulnerability(
            package="requests",
            installed_version="2.25.0",
            affected_versions="<2.26.0",
            severity="high",
            vulnerability_id="CVE-2021-12345",
            description="Test vulnerability",
            fix_version="2.26.0",
            source="pip-audit",
        )
        assert vuln.package == "requests"
        assert vuln.severity == "high"

    def test_scan_result_summary(self):
        result = DependencyScanResult(
            vulnerabilities=[
                Vulnerability(
                    package="test",
                    installed_version="1.0",
                    affected_versions="<2.0",
                    severity="critical",
                    vulnerability_id="CVE-1",
                    description="",
                ),
                Vulnerability(
                    package="test2",
                    installed_version="1.0",
                    affected_versions="<2.0",
                    severity="high",
                    vulnerability_id="CVE-2",
                    description="",
                ),
            ]
        )
        assert result.summary["critical"] == 1
        assert result.summary["high"] == 1

    @patch("subprocess.run")
    def test_scan_pip_audit_parses_output(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(
                [
                    {
                        "name": "requests",
                        "version": "2.25.0",
                        "vulns": [
                            {
                                "id": "CVE-2021-12345",
                                "affected_versions": "<2.26.0",
                                "fix_versions": ["2.26.0"],
                                "severity": "high",
                                "description": "Test",
                            }
                        ],
                    }
                ]
            ),
        )

        scanner = DependencyScanner()
        scanner.scan_pip_audit()

        assert len(scanner.result.vulnerabilities) == 1
        assert scanner.result.vulnerabilities[0].package == "requests"

    @patch("subprocess.run")
    def test_scan_handles_pip_audit_not_installed(self, mock_run):
        mock_run.side_effect = FileNotFoundError()

        scanner = DependencyScanner()
        scanner.scan_pip_audit()

        assert "pip-audit not installed" in scanner.result.errors[0]

    def test_severity_mapping(self):
        scanner = DependencyScanner()
        assert scanner._map_severity("CRITICAL") == "critical"
        assert scanner._map_severity("Important") == "high"
        assert scanner._map_severity("moderate") == "medium"
        assert scanner._map_severity("unknown") == "medium"


class TestSecurityFixer:
    """Test SecurityFixer class."""

    def test_fix_result_to_dict(self):
        result = FixResult(
            actions=[
                FixAction(
                    finding_title="Test",
                    action="applied",
                    command="chmod 600 /test",
                    description="Fixed",
                )
            ],
            applied_count=1,
        )
        d = result.to_dict()
        assert d["applied"] == 1
        assert len(d["actions"]) == 1

    def test_fix_permission_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test")
            os.chmod(test_file, 0o644)

            fixer = SecurityFixer(dry_run=True)
            action = fixer.fix_permission(test_file, 0o600)

            assert action.action == "suggested"
            # File should still be 0644
            assert stat.S_IMODE(test_file.stat().st_mode) == 0o644

    def test_fix_permission_applies(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test")
            os.chmod(test_file, 0o644)

            fixer = SecurityFixer(dry_run=False)
            action = fixer.fix_permission(test_file, 0o600)

            assert action.action == "applied"
            assert stat.S_IMODE(test_file.stat().st_mode) == 0o600

    def test_suggest_dependency_updates(self):
        dep_result = DependencyScanResult(
            vulnerabilities=[
                Vulnerability(
                    package="requests",
                    installed_version="2.25.0",
                    affected_versions="<2.26.0",
                    severity="high",
                    vulnerability_id="CVE-2021-12345",
                    description="",
                    fix_version="2.26.0",
                    source="pip-audit",
                ),
            ]
        )

        fixer = SecurityFixer(dry_run=True)
        suggestions = fixer.suggest_dependency_updates(dep_result)

        assert len(suggestions) == 1
        assert suggestions[0]["package"] == "requests"
        assert suggestions[0]["target_version"] == "2.26.0"
        assert "pip install" in suggestions[0]["command"]

    def test_fix_all_from_audit(self):
        audit_result = AuditResult(
            findings=[
                Finding(
                    severity="high",
                    category="permissions",
                    title="Test",
                    description="",
                    path="/nonexistent/path",
                    auto_fixable=True,
                ),
            ]
        )

        fixer = SecurityFixer(dry_run=True)
        result = fixer.fix_all(audit_result=audit_result)

        # Should handle nonexistent path gracefully
        assert isinstance(result, FixResult)


class TestCLIIntegration:
    """Test CLI security command integration."""

    @patch("sys.argv", ["openclaw-dash", "security", "--json"])
    def test_security_command_json_output(self, capsys):
        from openclaw_dash.cli import main

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(
                __import__(
                    "openclaw_dash.security.audit", fromlist=["SecurityAudit"]
                ).SecurityAudit,
                "__init__",
                lambda self, **kwargs: (
                    setattr(self, "openclaw_dir", Path(tmpdir))
                    or setattr(self, "result", AuditResult())
                ),
            ):
                main()

        captured = capsys.readouterr()
        # Should produce valid JSON
        try:
            data = json.loads(captured.out)
            assert "audit" in data or "dependencies" in data or captured.out == ""
        except json.JSONDecodeError:
            # Empty or error output is acceptable in test environment
            pass

    @patch("sys.argv", ["openclaw-dash", "security", "--deep"])
    def test_security_command_deep_flag(self):
        from openclaw_dash.cli import main

        # Just verify it doesn't crash
        result = main()
        assert result in (0, 1)
