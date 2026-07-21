"""Policy loading from TOML.

TOML because `tomllib` is stdlib on 3.11+, so a guard that sits in the
critical path of every tool call adds no dependencies of its own.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from spend_guard.policy import Policy

DEFAULT_CONFIG_NAMES = ("spend-guard.toml", ".spend-guard.toml")


class PolicyError(ValueError):
    """Raised when a policy file is missing or malformed."""


def _as_frozenset(value: object, field: str) -> frozenset[str]:
    if value is None:
        return frozenset()
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise PolicyError(f"'{field}' must be a list of strings")
    return frozenset(value)


def parse(data: dict) -> Policy:
    """Build a Policy from already-parsed TOML data."""
    tools = data.get("tools", {})
    limits = data.get("limits", {})

    allow = _as_frozenset(tools.get("allow"), "tools.allow")
    flag = _as_frozenset(tools.get("flag"), "tools.flag")
    stop = _as_frozenset(tools.get("stop"), "tools.stop")

    for a, b, label in ((allow, flag, "allow/flag"), (allow, stop, "allow/stop"), (flag, stop, "flag/stop")):
        overlap = a & b
        if overlap:
            raise PolicyError(f"tool(s) {sorted(overlap)} appear in both {label}")

    markers = data.get("escalate", {}).get("markers", [])
    if not isinstance(markers, list) or not all(isinstance(m, str) for m in markers):
        raise PolicyError("'escalate.markers' must be a list of strings")

    spend_limit = limits.get("spend")
    if spend_limit is not None and not isinstance(spend_limit, (int, float)):
        raise PolicyError("'limits.spend' must be a number")

    return Policy(
        allow=allow,
        flag=flag,
        stop=stop,
        escalate_markers=tuple(markers),
        spend_limit=float(spend_limit) if spend_limit is not None else None,
    )


def load(path: Path | str) -> Policy:
    """Load a policy from a TOML file."""
    p = Path(path)
    if not p.exists():
        raise PolicyError(f"no policy file at {p}")
    try:
        data = tomllib.loads(p.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise PolicyError(f"{p} is not valid TOML: {exc}") from exc
    return parse(data)


def discover(start: Path | str = ".") -> Path | None:
    """Find a policy file in `start` or any parent directory."""
    current = Path(start).resolve()
    for directory in (current, *current.parents):
        for name in DEFAULT_CONFIG_NAMES:
            candidate = directory / name
            if candidate.exists():
                return candidate
    return None
