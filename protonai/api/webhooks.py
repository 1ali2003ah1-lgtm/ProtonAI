"""Webhook notifications for clinical events.
Designed & developed by: Ali Hussein Thajil

Notifies external systems (EHR, OIS, research DB) of events:
- case.completed
- case.approved
- drift.detected
- risk.alert
"""
from __future__ import annotations
import hashlib, hmac, json, time, uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional

import httpx


@dataclass
class WebhookSubscription:
    id: str
    url: str
    events: List[str]
    secret: str
    active: bool = True
    tenant_id: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class WebhookEvent:
    id: str
    event_type: str
    payload: Dict
    timestamp: float = field(default_factory=time.time)
    tenant_id: str = ""


class WebhookManager:
    def __init__(self, state_path: str = "data/webhooks.json",
                 timeout: float = 5.0, max_retries: int = 3):
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.subscriptions: List[WebhookSubscription] = []
        self.deliveries: List[Dict] = []
        self.timeout = timeout
        self.max_retries = max_retries
        self._load()

    def subscribe(self, url: str, events: List[str],
                  tenant_id: str = "") -> WebhookSubscription:
        secret = "whsec_" + uuid.uuid4().hex
        sub = WebhookSubscription(
            id=uuid.uuid4().hex, url=url, events=events, secret=secret,
            tenant_id=tenant_id)
        self.subscriptions.append(sub)
        self._save()
        return sub

    def unsubscribe(self, sub_id: str) -> bool:
        before = len(self.subscriptions)
        self.subscriptions = [s for s in self.subscriptions if s.id != sub_id]
        if len(self.subscriptions) != before:
            self._save(); return True
        return False

    def _sign(self, secret: str, body: bytes) -> str:
        return "sha256=" + hmac.new(secret.encode(), body,
                                     hashlib.sha256).hexdigest()

    def emit(self, event_type: str, payload: Dict, tenant_id: str = ""):
        evt = WebhookEvent(id=uuid.uuid4().hex, event_type=event_type,
                            payload=payload, tenant_id=tenant_id)
        for sub in self.subscriptions:
            if not sub.active:
                continue
            if sub.tenant_id and sub.tenant_id != tenant_id:
                continue
            if "*" not in sub.events and event_type not in sub.events:
                continue
            self._deliver(sub, evt)

    def _deliver(self, sub: WebhookSubscription, evt: WebhookEvent):
        body = json.dumps(asdict(evt), default=str).encode()
        sig = self._sign(sub.secret, body)
        headers = {"Content-Type": "application/json",
                   "X-Webhook-Signature": sig,
                   "X-Webhook-Id": evt.id,
                   "X-Webhook-Event": evt.event_type,
                   "User-Agent": "ProtonAI-Webhooks/1.0"}
        for attempt in range(self.max_retries):
            try:
                r = httpx.post(sub.url, content=body, headers=headers,
                               timeout=self.timeout)
                self.deliveries.append({
                    "subscription_id": sub.id, "event_id": evt.id,
                    "status_code": r.status_code, "attempt": attempt + 1,
                    "timestamp": time.time(), "success": 200 <= r.status_code < 300,
                })
                if 200 <= r.status_code < 300:
                    break
            except Exception as e:
                self.deliveries.append({
                    "subscription_id": sub.id, "event_id": evt.id,
                    "error": str(e), "attempt": attempt + 1,
                    "timestamp": time.time(), "success": False,
                })
                if attempt == self.max_retries - 1:
                    break
                time.sleep(min(2 ** attempt, 10))
        self._save()

    def list_deliveries(self, limit: int = 100) -> List[Dict]:
        return self.deliveries[-limit:]

    def _load(self):
        if self.state_path.exists():
            try:
                d = json.loads(self.state_path.read_text())
                self.subscriptions = [WebhookSubscription(**s)
                                       for s in d.get("subs", [])]
                self.deliveries = d.get("deliveries", [])
            except Exception:
                pass

    def _save(self):
        self.state_path.write_text(json.dumps({
            "subs": [asdict(s) for s in self.subscriptions],
            "deliveries": self.deliveries[-1000:],
        }))
