"""Approval gates and an audit trail for agent tool calls."""

from spend_guard.audit import Guard, redact
from spend_guard.config import PolicyError, discover, load, parse
from spend_guard.policy import Decision, Policy, Tier, classify

__version__ = "0.1.0"
__all__ = [
    "Decision",
    "Guard",
    "Policy",
    "PolicyError",
    "Tier",
    "classify",
    "discover",
    "load",
    "parse",
    "redact",
]
