"""Blast-radius classification for agent tool calls.

Pure and deterministic: no I/O, no clock, no network. Every decision is a
function of the policy and the call, which is what makes it testable and
what makes an audit trail meaningful.

The design rule that matters: an unrecognised tool classifies as STOP. A
guard that fails open is not a guard.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum


class Tier(StrEnum):
    """How much damage a call could do."""

    ALLOW = "allow"  # routine, reversible — run it, log it
    FLAG = "flag"  # outward-facing or costly — run it, surface it loudly
    STOP = "stop"  # irreversible, financial, destructive — refuse, ask first


@dataclass(frozen=True)
class Decision:
    """The outcome of classifying one call."""

    tier: Tier
    reason: str
    matched: str | None = None

    @property
    def blocked(self) -> bool:
        return self.tier is Tier.STOP


@dataclass(frozen=True)
class Policy:
    """Which tools land in which tier, plus argument-level escalation.

    Attributes:
        allow: Tool names that may run freely.
        flag: Tool names that run but must be surfaced.
        stop: Tool names that must never run without approval.
        escalate_markers: Substrings that, found anywhere in the arguments,
            push an otherwise-ALLOW call up to FLAG. Use for things like a
            production hostname or a partner's name.
        spend_limit: Optional currency ceiling. Any call carrying an amount
            above this is forced to STOP regardless of its tool tier.
        amount_keys: Argument keys inspected for a spend amount.
    """

    allow: frozenset[str] = field(default_factory=frozenset)
    flag: frozenset[str] = field(default_factory=frozenset)
    stop: frozenset[str] = field(default_factory=frozenset)
    escalate_markers: tuple[str, ...] = ()
    spend_limit: float | None = None
    amount_keys: tuple[str, ...] = ("amount", "total", "price", "cost", "value")


def _args_text(args: dict | None) -> str:
    if not args:
        return ""
    try:
        return json.dumps(args, default=str).lower()
    except (TypeError, ValueError):
        return str(args).lower()


def _extract_amount(args: dict | None, keys: tuple[str, ...]) -> float | None:
    """Pull a numeric spend amount out of arguments, if one is present."""
    if not args:
        return None
    for key, value in args.items():
        if key.lower() not in keys:
            continue
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.strip().lstrip("$").replace(",", "")
            try:
                return float(cleaned)
            except ValueError:
                continue
    return None


def classify(tool: str, args: dict | None = None, *, policy: Policy) -> Decision:
    """Classify a single tool call.

    Order matters. A spend over the limit outranks the tool's own tier, because
    a "routine" call that moves money is not routine.

    Args:
        tool: Name of the tool being invoked.
        args: Arguments the agent wants to pass.
        policy: The policy to classify against.

    Returns:
        A Decision. Unknown tools return STOP.
    """
    amount = _extract_amount(args, policy.amount_keys)
    if policy.spend_limit is not None and amount is not None and amount > policy.spend_limit:
        return Decision(
            Tier.STOP,
            f"amount {amount:g} exceeds the {policy.spend_limit:g} limit",
            matched=f"spend_limit:{policy.spend_limit:g}",
        )

    if tool in policy.stop:
        return Decision(Tier.STOP, f"'{tool}' is irreversible or financial", matched=tool)

    if tool in policy.flag:
        return Decision(Tier.FLAG, f"'{tool}' is outward-facing or sensitive", matched=tool)

    if tool in policy.allow:
        text = _args_text(args)
        for marker in policy.escalate_markers:
            if marker.lower() in text:
                return Decision(
                    Tier.FLAG,
                    f"'{tool}' is routine but its arguments mention '{marker}'",
                    matched=marker,
                )
        return Decision(Tier.ALLOW, f"'{tool}' is routine and reversible", matched=tool)

    return Decision(
        Tier.STOP,
        f"'{tool}' is not in the policy — refusing rather than guessing",
    )
