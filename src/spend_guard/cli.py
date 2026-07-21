"""Command line interface.

The point of `check` is that you can interrogate your policy without running
an agent -- ask "what would happen if it tried this?" and get an answer.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from spend_guard.config import PolicyError, discover, load
from spend_guard.policy import Policy, Tier

EXIT_BY_TIER = {Tier.ALLOW: 0, Tier.FLAG: 0, Tier.STOP: 2}


def _resolve(path: str | None) -> Policy:
    target = Path(path) if path else discover()
    if target is None:
        raise PolicyError("no spend-guard.toml found in this directory or any parent")
    return load(target)


def _cmd_check(args: argparse.Namespace) -> int:
    policy = _resolve(args.policy)
    tool_args = json.loads(args.args) if args.args else {}
    from spend_guard.policy import classify

    d = classify(args.tool, tool_args, policy=policy)
    if args.json:
        print(json.dumps({"tool": args.tool, "tier": str(d.tier), "reason": d.reason,
                          "matched": d.matched, "blocked": d.blocked}))
    else:
        symbol = {Tier.ALLOW: "ALLOW", Tier.FLAG: "FLAG ", Tier.STOP: "STOP "}[d.tier]
        print(f"{symbol}  {args.tool}\n        {d.reason}")
    return EXIT_BY_TIER[d.tier]


def _cmd_explain(args: argparse.Namespace) -> int:
    policy = _resolve(args.policy)
    print(f"allow ({len(policy.allow)}): {', '.join(sorted(policy.allow)) or '-'}")
    print(f"flag  ({len(policy.flag)}): {', '.join(sorted(policy.flag)) or '-'}")
    print(f"stop  ({len(policy.stop)}): {', '.join(sorted(policy.stop)) or '-'}")
    print(f"escalate markers: {', '.join(policy.escalate_markers) or '-'}")
    print(f"spend limit: {policy.spend_limit if policy.spend_limit is not None else '-'}")
    print("\nAnything not listed above is refused.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="spend-guard", description=__doc__)
    parser.add_argument("--policy", help="path to a policy TOML file")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="classify a hypothetical tool call")
    check.add_argument("tool")
    check.add_argument("args", nargs="?", help="JSON object of tool arguments")
    check.add_argument("--json", action="store_true")
    check.set_defaults(func=_cmd_check)

    explain = sub.add_parser("explain", help="show the active policy")
    explain.set_defaults(func=_cmd_explain)

    ns = parser.parse_args(argv)
    try:
        return ns.func(ns)
    except PolicyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"error: arguments are not valid JSON: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
