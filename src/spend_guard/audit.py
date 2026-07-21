"""Enforcement and the audit trail.

Framework-agnostic on purpose. `Guard.check()` is the whole integration
surface -- call it before a tool runs, honour the result. Adapters for
specific agent frameworks wrap this rather than the other way round.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from spend_guard.policy import Decision, Policy, Tier, classify

REDACT_KEYS: tuple[str, ...] = (
    "token",
    "password",
    "secret",
    "key",
    "authorization",
    "credential",
    "api_key",
    "cookie",
    "session",
)

REDACTED = "***redacted***"


def redact(args: dict[str, Any] | None) -> dict[str, Any]:
    """Strip credential-shaped values, recursing into nested structures.

    Matches on key name rather than value shape: a key called `api_key` is
    redacted whatever it holds, which fails safe when a value looks harmless.
    """
    if not args:
        return {}
    out: dict[str, Any] = {}
    for key, value in args.items():
        if any(marker in key.lower() for marker in REDACT_KEYS):
            out[key] = REDACTED
        elif isinstance(value, dict):
            out[key] = redact(value)
        elif isinstance(value, list):
            out[key] = [redact(v) if isinstance(v, dict) else v for v in value]
        else:
            out[key] = value
    return out


class Guard:
    """Classifies calls, blocks the dangerous ones, records all of them."""

    def __init__(
        self,
        policy: Policy,
        log_path: Path | str | None = None,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        """
        Args:
            policy: Policy to enforce.
            log_path: JSONL audit file. Omit to classify without recording.
            now: Clock override, for tests.
        """
        self.policy = policy
        self.log_path = Path(log_path) if log_path else None
        self._now = now or (lambda: datetime.now(UTC))
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _record(self, payload: dict[str, Any]) -> None:
        if not self.log_path:
            return
        payload["ts"] = self._now().isoformat()
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, default=str) + "\n")

    def check(self, tool: str, args: dict[str, Any] | None = None) -> Decision:
        """Classify a call and write the intent record.

        Returns:
            The Decision. Callers must not run the tool when `decision.blocked`.
        """
        decision = classify(tool, args, policy=self.policy)
        self._record(
            {
                "phase": "intent",
                "tool": tool,
                "tier": str(decision.tier),
                "reason": decision.reason,
                "matched": decision.matched,
                "args": redact(args),
            }
        )
        return decision

    def record_result(self, tool: str, decision: Decision, result: Any = None) -> None:
        """Record what actually happened after an allowed call ran."""
        self._record(
            {
                "phase": "result",
                "tool": tool,
                "tier": str(decision.tier),
                "flagged": decision.tier is Tier.FLAG,
                "result": redact(result) if isinstance(result, dict) else result,
            }
        )
