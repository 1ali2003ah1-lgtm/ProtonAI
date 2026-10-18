"""Persistent, tamper-evident audit log (SQLite + SHA256 chain).
Designed & developed by: Ali Hussein Thajil"""
from __future__ import annotations
import hashlib, json, sqlite3, time, uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


class AuditLog:
    def __init__(self, db_path: str = "data/audit.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _init(self):
        with sqlite3.connect(self.db_path) as con:
            con.execute("""CREATE TABLE IF NOT EXISTS audit (
                id TEXT PRIMARY KEY,
                timestamp REAL NOT NULL,
                tenant_id TEXT,
                user_id TEXT,
                action TEXT NOT NULL,
                resource_type TEXT,
                resource_id TEXT,
                payload TEXT,
                ip TEXT,
                user_agent TEXT,
                prev_hash TEXT,
                hash TEXT NOT NULL,
                outcome TEXT
            )""")
            con.execute("""CREATE INDEX IF NOT EXISTS idx_tenant
                           ON audit(tenant_id, timestamp)""")
            con.execute("""CREATE INDEX IF NOT EXISTS idx_action
                           ON audit(action, timestamp)""")

    def record(self, action: str, resource_type: str = "",
               resource_id: str = "", payload: Dict[str, Any] = None,
               tenant_id: str = "", user_id: str = "",
               ip: str = "", user_agent: str = "",
               outcome: str = "success") -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT hash FROM audit ORDER BY timestamp DESC LIMIT 1")
            row = cur.fetchone()
            prev_hash = row[0] if row else "GENESIS"
            entry_id = str(uuid.uuid4())
            ts = time.time()
            payload_json = json.dumps(payload or {}, sort_keys=True,
                                       default=str)
            data = f"{entry_id}:{ts}:{action}:{resource_type}:{resource_id}:{payload_json}:{prev_hash}"
            h = hashlib.sha256(data.encode()).hexdigest()
            cur.execute("""INSERT INTO audit VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (entry_id, ts, tenant_id, user_id, action,
                         resource_type, resource_id, payload_json, ip,
                         user_agent, prev_hash, h, outcome))
            return {"id": entry_id, "hash": h, "prev_hash": prev_hash,
                    "timestamp": ts}

    def verify_integrity(self) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT id, timestamp, action, resource_type, "
                        "resource_id, payload, prev_hash, hash "
                        "FROM audit ORDER BY timestamp ASC")
            rows = cur.fetchall()
        prev = "GENESIS"
        for i, row in enumerate(rows):
            entry_id, ts, action, rt, rid, payload, prev_hash, h = row
            if prev_hash != prev:
                return {"valid": False, "broken_at": i, "id": entry_id,
                        "reason": "prev_hash mismatch"}
            data = f"{entry_id}:{ts}:{action}:{rt}:{rid}:{payload}:{prev_hash}"
            expected = hashlib.sha256(data.encode()).hexdigest()
            if expected != h:
                return {"valid": False, "broken_at": i, "id": entry_id,
                        "reason": "hash mismatch"}
            prev = h
        return {"valid": True, "count": len(rows), "last_hash": prev}

    def query(self, tenant_id: Optional[str] = None,
              action: Optional[str] = None,
              since: Optional[float] = None,
              limit: int = 100) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as con:
            con.row_factory = sqlite3.Row
            sql = "SELECT * FROM audit WHERE 1=1"
            args = []
            if tenant_id:
                sql += " AND tenant_id = ?"; args.append(tenant_id)
            if action:
                sql += " AND action = ?"; args.append(action)
            if since:
                sql += " AND timestamp >= ?"; args.append(since)
            sql += " ORDER BY timestamp DESC LIMIT ?"; args.append(limit)
            rows = con.execute(sql, args).fetchall()
            return [dict(r) for r in rows]
