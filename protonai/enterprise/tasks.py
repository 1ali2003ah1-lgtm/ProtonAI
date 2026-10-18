"""Background task queue with persistence and progress tracking.
Designed & developed by: Ali Hussein Thajil"""
from __future__ import annotations
import json, threading, time, traceback, uuid
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    payload: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None


class TaskQueue:
    """In-process task queue. Production: swap with Celery + Redis."""

    def __init__(self, state_path: str = "data/tasks.json", max_workers: int = 4):
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._tasks: Dict[str, Task] = {}
        self._handlers: Dict[str, Callable] = {}
        self._queue: List[str] = []
        self._lock = threading.Lock()
        self._semaphore = threading.Semaphore(max_workers)
        self._load()

    def register(self, name: str):
        def decorator(fn):
            self._handlers[name] = fn
            return fn
        return decorator

    def submit(self, name: str, payload: Dict[str, Any],
               tenant_id: Optional[str] = None,
               user_id: Optional[str] = None) -> Task:
        if name not in self._handlers:
            raise ValueError(f"Unknown task: {name}")
        task = Task(name=name, payload=payload, tenant_id=tenant_id,
                    user_id=user_id)
        with self._lock:
            self._tasks[task.id] = task
            self._queue.append(task.id)
            self._save()
        threading.Thread(target=self._run_task, args=(task.id,),
                         daemon=True).start()
        return task

    def _run_task(self, task_id: str):
        self._semaphore.acquire()
        try:
            with self._lock:
                task = self._tasks[task_id]
                task.status = TaskStatus.RUNNING
                task.started_at = time.time()
                self._save()
            fn = self._handlers[task.name]
            result = fn(task)
            with self._lock:
                task.status = TaskStatus.SUCCESS
                task.result = result
                task.progress = 1.0
                task.completed_at = time.time()
                self._save()
        except Exception as e:
            with self._lock:
                task.status = TaskStatus.FAILED
                task.error = traceback.format_exc()
                task.completed_at = time.time()
                self._save()
        finally:
            self._semaphore.release()

    def get(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def list(self, tenant_id: Optional[str] = None,
             status: Optional[TaskStatus] = None,
             limit: int = 50) -> List[Task]:
        out = []
        for t in self._tasks.values():
            if tenant_id and t.tenant_id != tenant_id:
                continue
            if status and t.status != status:
                continue
            out.append(t)
        out.sort(key=lambda t: t.created_at, reverse=True)
        return out[:limit]

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            t = self._tasks.get(task_id)
            if t and t.status == TaskStatus.PENDING:
                t.status = TaskStatus.CANCELLED
                t.completed_at = time.time()
                self._save()
                return True
        return False

    def update_progress(self, task_id: str, progress: float,
                        meta: Optional[Dict] = None):
        with self._lock:
            t = self._tasks.get(task_id)
            if t:
                t.progress = progress
                if meta and t.result is None:
                    t.result = {}
                if meta and isinstance(t.result, dict):
                    t.result.update(meta)
                self._save()

    def _load(self):
        if self.state_path.exists():
            try:
                data = json.loads(self.state_path.read_text())
                for td in data.values():
                    td["status"] = TaskStatus(td["status"])
                    self._tasks[td["id"]] = Task(**td)
            except Exception:
                pass

    def _save(self):
        data = {tid: asdict(t) for tid, t in self._tasks.items()}
        for td in data.values():
            td["status"] = td["status"].value
        self.state_path.write_text(json.dumps(data, indent=2))
