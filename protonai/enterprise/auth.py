"""Enterprise RBAC + Multi-tenant + API key management.
Designed & developed by: Ali Hussein Thajil"""
from __future__ import annotations
import hashlib, hmac, secrets, time, json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, List

ROLES = {"viewer", "physician", "physicist", "admin", "researcher"}
PERMISSIONS = {
    "viewer": ["read.cases", "read.reports"],
    "physician": ["read.*", "write.approvals", "sign.reports"],
    "physicist": ["read.*", "write.plans", "run.pipeline"],
    "admin": ["*"],
    "researcher": ["read.anonymized", "export.cohort"],
}


@dataclass
class Tenant:
    id: str
    name: str
    plan: str = "clinical"
    max_cases_per_day: int = 1000
    created_at: float = 0.0


@dataclass
class User:
    id: str
    email: str
    role: str
    tenant_id: str
    api_key_hash: str = ""
    name: str = ""
    active: bool = True
    created_at: float = 0.0

    def has(self, perm: str) -> bool:
        allowed = PERMISSIONS.get(self.role, [])
        if "*" in allowed:
            return True
        if perm in allowed:
            return True
        ns = perm.split(".")[0] + ".*"
        return ns in allowed


class TenantStore:
    def __init__(self, path: str = "data/tenants.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self):
        if self.path.exists():
            return json.loads(self.path.read_text())
        return {"tenants": {}, "users": {}}

    def _save(self):
        self.path.write_text(json.dumps(self.data, indent=2))

    def create_tenant(self, tenant: Tenant) -> Tenant:
        tenant.created_at = time.time()
        self.data["tenants"][tenant.id] = asdict(tenant)
        self._save()
        return tenant

    def create_user(self, user: User) -> tuple[User, str]:
        raw_key = "pai_" + secrets.token_urlsafe(32)
        user.api_key_hash = self.hash_key(raw_key)
        user.created_at = time.time()
        self.data["users"][user.id] = asdict(user)
        self._save()
        return user, raw_key

    def authenticate(self, raw_key: str) -> Optional[User]:
        h = self.hash_key(raw_key)
        for ud in self.data["users"].values():
            if hmac.compare_digest(ud["api_key_hash"], h) and ud["active"]:
                return User(**ud)
        return None

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        t = self.data["tenants"].get(tenant_id)
        return Tenant(**t) if t else None

    @staticmethod
    def hash_key(raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()

    def list_users(self, tenant_id: Optional[str] = None) -> List[User]:
        out = []
        for ud in self.data["users"].values():
            if tenant_id and ud["tenant_id"] != tenant_id:
                continue
            out.append(User(**ud))
        return out
