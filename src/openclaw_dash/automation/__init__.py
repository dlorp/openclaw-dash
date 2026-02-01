"""Automation features for openclaw-dash."""

from .backup import BackupVerifier
from .deps_auto import DepsAutomation
from .pr_auto import PRAutomation

__all__ = ["PRAutomation", "DepsAutomation", "BackupVerifier"]
