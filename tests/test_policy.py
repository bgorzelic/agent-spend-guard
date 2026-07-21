"""The guard's whole value is that it refuses correctly. Test that hardest."""

from __future__ import annotations

import pytest

from spend_guard.policy import Policy, Tier, classify

POLICY = Policy(
    allow=frozenset({"read_file", "search", "list_messages"}),
    flag=frozenset({"send_email", "deploy"}),
    stop=frozenset({"make_payment", "delete_data"}),
    escalate_markers=("production", "acme corp"),
    spend_limit=50.0,
)


def test_routine_tool_is_allowed():
    d = classify("read_file", {"path": "README.md"}, policy=POLICY)
    assert d.tier is Tier.ALLOW
    assert not d.blocked


def test_outward_facing_tool_is_flagged():
    d = classify("send_email", {"to": "a@b.com"}, policy=POLICY)
    assert d.tier is Tier.FLAG
    assert not d.blocked


def test_irreversible_tool_is_stopped():
    d = classify("make_payment", {"amount": 5}, policy=POLICY)
    assert d.tier is Tier.STOP
    assert d.blocked


def test_unknown_tool_fails_safe_to_stop():
    """The property that makes this a guard rather than a suggestion."""
    d = classify("wire_transfer_everything", {}, policy=POLICY)
    assert d.tier is Tier.STOP
    assert "not in the policy" in d.reason


def test_marker_in_args_escalates_allow_to_flag():
    d = classify("read_file", {"path": "/srv/production/secrets"}, policy=POLICY)
    assert d.tier is Tier.FLAG
    assert d.matched == "production"


def test_marker_matching_is_case_insensitive():
    d = classify("search", {"q": "ACME CORP revenue"}, policy=POLICY)
    assert d.tier is Tier.FLAG


def test_spend_over_limit_overrides_allow_tier():
    """A 'routine' call that moves real money is not routine."""
    d = classify("read_file", {"amount": 500}, policy=POLICY)
    assert d.tier is Tier.STOP
    assert "exceeds" in d.reason


def test_spend_under_limit_does_not_escalate():
    d = classify("read_file", {"amount": 10}, policy=POLICY)
    assert d.tier is Tier.ALLOW


@pytest.mark.parametrize("raw", ["$500", "500", "1,200.50", 500, 500.0])
def test_amount_parsed_from_common_formats(raw):
    d = classify("read_file", {"amount": raw}, policy=POLICY)
    assert d.tier is Tier.STOP


@pytest.mark.parametrize("raw", ["not-a-number", "", None, {"nested": 1}])
def test_unparseable_amount_does_not_crash(raw):
    d = classify("read_file", {"amount": raw}, policy=POLICY)
    assert d.tier is Tier.ALLOW


def test_no_spend_limit_means_no_amount_check():
    p = Policy(allow=frozenset({"buy"}), spend_limit=None)
    assert classify("buy", {"amount": 10_000}, policy=p).tier is Tier.ALLOW


def test_empty_policy_stops_everything():
    assert classify("anything", {}, policy=Policy()).tier is Tier.STOP


def test_stop_tier_wins_over_marker_escalation():
    d = classify("delete_data", {"target": "production"}, policy=POLICY)
    assert d.tier is Tier.STOP


def test_none_args_are_safe():
    assert classify("read_file", None, policy=POLICY).tier is Tier.ALLOW
