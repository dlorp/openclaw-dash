"""Automation features for openclaw-dash."""

from .pr_auto import PRAutomation
from .deps_auto import DepsAutomation
from .backup import BackupVerifier

__all__ = ["PRAutomation", "DepsAutomation", "BackupVerifier"]
