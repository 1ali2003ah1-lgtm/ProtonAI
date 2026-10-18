"""Modern API layer tests."""
import os, sys, json
sys.path.insert(0, os.getcwd())

from protonai.api.webhooks import WebhookManager


def test_webhook_subscribe_and_list():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        m = WebhookManager(state_path=os.path.join(td, "w.json"))
        s = m.subscribe("https://example.com/hook", ["case.completed"])
        assert s.id and s.secret.startswith("whsec_")
        assert len(m.subscriptions) == 1


def test_webhook_unsubscribe():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        m = WebhookManager(state_path=os.path.join(td, "w.json"))
        s = m.subscribe("https://x.com", ["*"])
        assert m.unsubscribe(s.id)
        assert len(m.subscriptions) == 0


def test_webhook_emit_no_crash_when_no_subs():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        m = WebhookManager(state_path=os.path.join(td, "w.json"))
        m.emit("case.completed", {"case_id": "c1"})  # should not raise
        assert True
