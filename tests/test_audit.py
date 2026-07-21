"""Redaction and the audit trail. A log that leaks credentials is a liability."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from spend_guard.audit import REDACTED, Guard, redact
from spend_guard.policy import Policy, Tier

POLICY = Policy(
    allow=frozenset({"read_file"}),
    flag=frozenset({"send_email"}),
    stop=frozenset({"make_payment"}),
)
FIXED = datetime(2026, 1, 1, tzinfo=UTC)


def _lines(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def test_redacts_credential_shaped_keys():
    out = redact({"api_key": "sk-live-123", "path": "README.md"})
    assert out["api_key"] == REDACTED
    assert out["path"] == "README.md"


def test_redacts_nested_dicts():
    out = redact({"config": {"password": "hunter2", "host": "db"}})
    assert out["config"]["password"] == REDACTED
    assert out["config"]["host"] == "db"


def test_redacts_inside_lists():
    out = redact({"items": [{"token": "abc"}, {"name": "ok"}]})
    assert out["items"][0]["token"] == REDACTED
    assert out["items"][1]["name"] == "ok"


def test_redaction_is_key_based_not_value_based():
    """A harmless-looking value under a credential key is still redacted."""
    assert redact({"secret": "1"})["secret"] == REDACTED


def test_check_writes_intent_record(tmp_path):
    log = tmp_path / "audit.jsonl"
    Guard(POLICY, log, now=lambda: FIXED).check("read_file", {"path": "a.txt"})
    (rec,) = _lines(log)
    assert rec["phase"] == "intent"
    assert rec["tier"] == "allow"
    assert rec["ts"] == FIXED.isoformat()


def test_blocked_call_is_still_logged(tmp_path):
    """You most need the record of the thing that was refused."""
    log = tmp_path / "audit.jsonl"
    d = Guard(POLICY, log, now=lambda: FIXED).check("make_payment", {"amount": 900})
    assert d.blocked
    (rec,) = _lines(log)
    assert rec["tier"] == "stop"


def test_credentials_never_reach_the_log(tmp_path):
    log = tmp_path / "audit.jsonl"
    Guard(POLICY, log, now=lambda: FIXED).check("read_file", {"api_key": "sk-live-SECRET"})
    assert "sk-live-SECRET" not in log.read_text(encoding="utf-8")


def test_result_record_marks_flagged_calls(tmp_path):
    log = tmp_path / "audit.jsonl"
    g = Guard(POLICY, log, now=lambda: FIXED)
    d = g.check("send_email", {"to": "a@b.com"})
    g.record_result("send_email", d, {"status": "sent"})
    recs = _lines(log)
    assert recs[1]["phase"] == "result"
    assert recs[1]["flagged"] is True


def test_guard_without_log_path_still_classifies(tmp_path):
    assert Guard(POLICY).check("read_file", {}).tier is Tier.ALLOW


def test_log_is_append_only_across_calls(tmp_path):
    log = tmp_path / "nested" / "audit.jsonl"
    g = Guard(POLICY, log, now=lambda: FIXED)
    g.check("read_file", {})
    g.check("read_file", {})
    assert len(_lines(log)) == 2
