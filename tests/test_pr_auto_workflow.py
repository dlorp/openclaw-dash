"""Tests for PR auto-merge workflow gating."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

from openclaw_dash.pr_workflow import PRWorkflow


def load_pr_auto_module():
    """Load pr_auto.py directly to avoid importing the full automation package."""
    module_name = "tests._pr_auto_under_test"
    if module_name in sys.modules:
        return sys.modules[module_name]

    module_path = Path(__file__).resolve().parents[1] / "src" / "openclaw_dash" / "automation" / "pr_auto.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def make_pr(module):
    """Create a standard PRInfo object for merge-gate tests."""
    return module.PRInfo(
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


def test_is_safe_to_merge_with_workflow_gate_blocks_not_ready(tmp_path):
    """Workflow state should block merge until the PR is READY."""
    module = load_pr_auto_module()
    pr = make_pr(module)
    config = module.MergeConfig()
    workflow = PRWorkflow(tmp_path / ".pr-workflow-state.json")
    workflow.create_pr(
        "test#1",
        pr_url=pr.url,
        pr_number=pr.number,
        repo="test/test",
        repo_short="test",
        base_branch="main",
        head_branch=pr.branch,
        local_branch=pr.branch,
        title=pr.title,
        description="",
        created=1_700_000_000,
        created_commit="abc123",
    )

    automation = module.PRAutomation(Path("/tmp/test"))
    safe, reason = automation.is_safe_to_merge(pr, config, workflow=workflow)

    assert safe is False
    assert reason == "PR is at CREATED, not READY"


def test_is_safe_to_merge_with_workflow_gate_allows_ready():
    """Workflow-ready PRs should continue through normal merge checks."""
    module = load_pr_auto_module()
    pr = make_pr(module)
    config = module.MergeConfig()
    workflow = MagicMock()
    workflow.is_ready_for_merge.return_value = (True, "")

    automation = module.PRAutomation(Path("/tmp/test"))
    safe, reason = automation.is_safe_to_merge(pr, config, workflow=workflow)

    assert safe is True
    assert reason == "Ready to merge"
    workflow.is_ready_for_merge.assert_called_once_with("test#1")
