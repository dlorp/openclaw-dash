"""Tests for PR workflow state machine."""

from __future__ import annotations

import json

import pytest

from openclaw_dash.pr_workflow import PRWorkflow, StaticAnalysisResult


def create_workflow(tmp_path):
    """Create a workflow backed by a temporary state file."""
    return PRWorkflow(tmp_path / ".pr-workflow-state.json")


def create_pr(workflow: PRWorkflow, pr_key: str = "openclaw-dash#123"):
    """Create a standard test PR entry."""
    return workflow.create_pr(
        pr_key,
        pr_url="https://github.com/dlorp/openclaw-dash/pull/123",
        pr_number=123,
        repo="dlorp/openclaw-dash",
        repo_short="openclaw-dash",
        base_branch="main",
        head_branch="deps/update-requests",
        local_branch="deps/update-requests",
        title="deps: update requests",
        description="Bump requests",
        created=1_717_171_717,
        created_commit="abc123",
        latest_commit="def456",
    )


def test_initializes_workflow_state_file(tmp_path):
    """Workflow should create the separate .pr-workflow-state.json schema."""
    state_file = tmp_path / ".pr-workflow-state.json"
    workflow = PRWorkflow(state_file)

    data = json.loads(state_file.read_text())

    assert workflow.load() == data
    assert data["$schema"] == "pr-workflow-state-v1"
    assert data["active_prs"] == {}
    assert data["completed_prs"] == {}


def test_create_pr_populates_default_validations(tmp_path):
    """New PR entries should include the standard validation blocks."""
    workflow = create_workflow(tmp_path)

    pr_state = create_pr(workflow)

    assert pr_state.state == "CREATED"
    assert set(pr_state.validations) == {"security_review", "code_review", "ci"}
    assert pr_state.validations["security_review"].status == "not_started"


def test_transition_requires_completed_security_review(tmp_path):
    """SECURITY_REVIEW -> CODE_REVIEW should remain gated until review output exists."""
    workflow = create_workflow(tmp_path)
    create_pr(workflow)
    workflow.transition("openclaw-dash#123", "SECURITY_REVIEW")

    allowed, reason = workflow.can_transition(
        "openclaw-dash#123", "SECURITY_REVIEW", "CODE_REVIEW"
    )

    assert allowed is False
    assert reason == "Security review not complete"


def test_transition_advances_after_required_validations(tmp_path):
    """Workflow should reach READY once all required validations complete."""
    workflow = create_workflow(tmp_path)
    create_pr(workflow)

    workflow.transition("openclaw-dash#123", "SECURITY_REVIEW", at=10)
    workflow.update_validation(
        "openclaw-dash#123",
        "security_review",
        status="completed",
        file="reviews/PR-123-security.md",
        file_exists=True,
        static_analysis=StaticAnalysisResult(passed=True, critical_issues=0),
    )
    workflow.transition("openclaw-dash#123", "CODE_REVIEW", at=20)
    workflow.update_validation(
        "openclaw-dash#123",
        "code_review",
        status="completed",
        file="reviews/PR-123-code.md",
        file_exists=True,
    )
    workflow.transition("openclaw-dash#123", "FIXES_APPLIED", at=30)
    workflow.transition("openclaw-dash#123", "CI_RUNNING", at=40)
    workflow.update_validation("openclaw-dash#123", "ci", status="completed")
    ready_state = workflow.transition("openclaw-dash#123", "READY", at=50)

    assert ready_state.state == "READY"
    assert len(ready_state.transitions) == 5
    assert workflow.is_ready_for_merge("openclaw-dash#123") == (True, "")


def test_transition_rejects_wrong_current_state(tmp_path):
    """Transition checks should validate the PR's current state."""
    workflow = create_workflow(tmp_path)
    create_pr(workflow)

    allowed, reason = workflow.can_transition("openclaw-dash#123", "SECURITY_REVIEW", "CODE_REVIEW")

    assert allowed is False
    assert reason == "PR is at CREATED, not SECURITY_REVIEW"


def test_is_ready_for_merge_rejects_missing_pr(tmp_path):
    """Missing workflow entries should not pass merge readiness."""
    workflow = create_workflow(tmp_path)

    ready, reason = workflow.is_ready_for_merge("openclaw-dash#999")

    assert ready is False
    assert reason == "PR not in workflow"


def test_transition_raises_for_blocked_move(tmp_path):
    """transition should raise when the validation gate is not satisfied."""
    workflow = create_workflow(tmp_path)
    create_pr(workflow)
    workflow.transition("openclaw-dash#123", "SECURITY_REVIEW")

    with pytest.raises(ValueError, match="Security review not complete"):
        workflow.transition("openclaw-dash#123", "CODE_REVIEW")
