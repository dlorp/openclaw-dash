"""PR workflow state machine with LLM agent integration."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

State = Literal["CREATED", "SECURITY_REVIEW", "CODE_REVIEW", "FIXES_APPLIED", "CI_RUNNING", "READY"]
ValidationStatus = Literal["not_started", "running", "completed", "validated"]

SCHEMA_NAME = "pr-workflow-state-v1"
SCHEMA_VERSION = "1.1.0"


@dataclass
class StaticAnalysisResult:
    """Results from the static audit stage."""

    tool: str = "openclaw-dash audit"
    run_at: int | None = None
    critical_issues: int = 0
    high_issues: int = 0
    medium_issues: int = 0
    low_issues: int = 0
    passed: bool = False
    report_file: str | None = None


@dataclass
class Validation:
    """Validation state for one workflow gate."""

    status: ValidationStatus = "not_started"
    static_analysis: StaticAnalysisResult | None = None
    agent_spawned: bool = False
    agent_session: str | None = None
    spawned_at: int | None = None
    completed_at: int | None = None
    file: str | None = None
    file_exists: bool = False
    result: Literal["pass", "fail"] | None = None
    issues_found: int = 0


@dataclass
class PRWorkflowState:
    """Complete workflow state for a PR."""

    state: State
    pr_url: str
    pr_number: int
    repo: str
    repo_short: str
    base_branch: str
    head_branch: str
    local_branch: str
    title: str
    description: str
    created: int
    created_commit: str
    latest_commit: str
    transitions: list[dict[str, Any]]
    validations: dict[str, Validation]


class PRWorkflow:
    """Workflow state machine and persistence for PR review automation."""

    TRANSITIONS: dict[State, list[State]] = {
        "CREATED": ["SECURITY_REVIEW"],
        "SECURITY_REVIEW": ["CODE_REVIEW", "FIXES_APPLIED"],
        "CODE_REVIEW": ["FIXES_APPLIED"],
        "FIXES_APPLIED": ["CI_RUNNING"],
        "CI_RUNNING": ["READY", "FIXES_APPLIED"],
        "READY": [],
    }

    DEFAULT_VALIDATIONS = ("security_review", "code_review", "ci")

    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.state_file.exists():
            self._init_state_file()

    @classmethod
    def empty_state(cls) -> dict[str, Any]:
        """Return the default workflow state document."""
        return {
            "$schema": SCHEMA_NAME,
            "version": SCHEMA_VERSION,
            "description": "PR workflow state machine - OpenClaw LLM agent integration",
            "active_prs": {},
            "completed_prs": {},
        }

    def _init_state_file(self) -> None:
        """Initialize an empty workflow state file."""
        self.state_file.write_text(json.dumps(self.empty_state(), indent=2))

    def load(self) -> dict[str, Any]:
        """Load workflow state from disk."""
        if not self.state_file.exists():
            self._init_state_file()
        return json.loads(self.state_file.read_text())

    def save(self, data: dict[str, Any]) -> None:
        """Save workflow state to disk."""
        self.state_file.write_text(json.dumps(data, indent=2))

    def get_pr_state(self, pr_key: str) -> PRWorkflowState | None:
        """Get workflow state for a specific PR."""
        pr_data = self.load().get("active_prs", {}).get(pr_key)
        if not pr_data:
            return None
        return self._deserialize_pr_state(pr_data)

    def create_pr(self, pr_key: str, **metadata: Any) -> PRWorkflowState:
        """Create a new workflow entry for a PR."""
        data = self.load()
        if pr_key in data["active_prs"]:
            return self._deserialize_pr_state(data["active_prs"][pr_key])

        validations = {name: asdict(Validation()) for name in self.DEFAULT_VALIDATIONS}
        pr_data = {
            "state": "CREATED",
            "pr_url": metadata["pr_url"],
            "pr_number": metadata["pr_number"],
            "repo": metadata["repo"],
            "repo_short": metadata.get("repo_short", metadata["repo"]),
            "base_branch": metadata["base_branch"],
            "head_branch": metadata["head_branch"],
            "local_branch": metadata.get("local_branch", metadata["head_branch"]),
            "title": metadata["title"],
            "description": metadata.get("description", ""),
            "created": metadata["created"],
            "created_commit": metadata["created_commit"],
            "latest_commit": metadata.get("latest_commit", metadata["created_commit"]),
            "transitions": [],
            "validations": validations,
        }
        data["active_prs"][pr_key] = pr_data
        self.save(data)
        return self._deserialize_pr_state(pr_data)

    def update_validation(self, pr_key: str, validation_name: str, **changes: Any) -> Validation:
        """Update one validation block for a PR."""
        data = self.load()
        pr_data = data.get("active_prs", {}).get(pr_key)
        if not pr_data:
            raise KeyError(f"PR not found in workflow: {pr_key}")

        validations = pr_data.setdefault("validations", {})
        current = validations.setdefault(validation_name, asdict(Validation()))

        if "static_analysis" in changes and isinstance(changes["static_analysis"], StaticAnalysisResult):
            changes["static_analysis"] = asdict(changes["static_analysis"])

        current.update(changes)
        self.save(data)
        return self._deserialize_validation(current)

    def transition(
        self,
        pr_key: str,
        to_state: State,
        *,
        at: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PRWorkflowState:
        """Move a PR to the next state if the transition is valid."""
        data = self.load()
        pr_data = data.get("active_prs", {}).get(pr_key)
        if not pr_data:
            raise KeyError(f"PR not found in workflow: {pr_key}")

        from_state = pr_data["state"]
        allowed, reason = self.can_transition(pr_key, from_state, to_state)
        if not allowed:
            raise ValueError(reason)

        pr_data["state"] = to_state
        pr_data.setdefault("transitions", []).append(
            {
                "from": from_state,
                "to": to_state,
                "at": at,
                "metadata": metadata or {},
            }
        )
        self.save(data)
        return self._deserialize_pr_state(pr_data)

    def can_transition(self, pr_key: str, from_state: State, to_state: State) -> tuple[bool, str]:
        """Check whether a state transition is currently allowed."""
        if to_state not in self.TRANSITIONS.get(from_state, []):
            return False, f"Invalid transition: {from_state} → {to_state}"

        pr_state = self.get_pr_state(pr_key)
        if not pr_state:
            return False, "PR not found in workflow"

        if pr_state.state != from_state:
            return False, f"PR is at {pr_state.state}, not {from_state}"

        if from_state == "SECURITY_REVIEW" and to_state == "CODE_REVIEW":
            security = pr_state.validations.get("security_review")
            if not security or security.status != "completed" or not security.file_exists:
                return False, "Security review not complete"

        if from_state == "CODE_REVIEW" and to_state == "FIXES_APPLIED":
            code_review = pr_state.validations.get("code_review")
            if not code_review or code_review.status != "completed" or not code_review.file_exists:
                return False, "Code review not complete"

        if from_state == "CI_RUNNING" and to_state == "READY":
            ci = pr_state.validations.get("ci")
            if not ci or ci.status != "completed":
                return False, "CI not passing"

        return True, ""

    def is_ready_for_merge(self, pr_key: str) -> tuple[bool, str]:
        """Check whether the PR has reached the READY workflow state."""
        pr_state = self.get_pr_state(pr_key)
        if not pr_state:
            return False, "PR not in workflow"
        if pr_state.state != "READY":
            return False, f"PR is at {pr_state.state}, not READY"
        return True, ""

    @staticmethod
    def _deserialize_validation(data: dict[str, Any]) -> Validation:
        """Build a Validation object from persisted JSON data."""
        static = data.get("static_analysis")
        return Validation(
            status=data.get("status", "not_started"),
            static_analysis=StaticAnalysisResult(**static) if static else None,
            agent_spawned=data.get("agent_spawned", False),
            agent_session=data.get("agent_session"),
            spawned_at=data.get("spawned_at"),
            completed_at=data.get("completed_at"),
            file=data.get("file"),
            file_exists=data.get("file_exists", False),
            result=data.get("result"),
            issues_found=data.get("issues_found", 0),
        )

    def _deserialize_pr_state(self, pr_data: dict[str, Any]) -> PRWorkflowState:
        """Build a PRWorkflowState object from persisted JSON data."""
        validations = {
            name: self._deserialize_validation(payload)
            for name, payload in pr_data.get("validations", {}).items()
        }
        return PRWorkflowState(
            state=pr_data["state"],
            pr_url=pr_data["pr_url"],
            pr_number=pr_data["pr_number"],
            repo=pr_data["repo"],
            repo_short=pr_data["repo_short"],
            base_branch=pr_data["base_branch"],
            head_branch=pr_data["head_branch"],
            local_branch=pr_data["local_branch"],
            title=pr_data["title"],
            description=pr_data.get("description", ""),
            created=pr_data["created"],
            created_commit=pr_data["created_commit"],
            latest_commit=pr_data["latest_commit"],
            transitions=pr_data.get("transitions", []),
            validations=validations,
        )
