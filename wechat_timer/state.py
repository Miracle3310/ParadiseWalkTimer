from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class RunState:
    path: Path
    last_success_date: str | None = None
    pending_locked_date: str | None = None
    last_status: str | None = None
    last_message: str | None = None
    last_screenshot: str | None = None
    updated_at: str | None = None

    @classmethod
    def load(cls, path: Path) -> "RunState":
        if not path.exists():
            return cls(path=path)
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(path=path, **{key: raw.get(key) for key in cls._persisted_keys()})

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(self)
        data.pop("path", None)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def mark_pending_locked(self, today: str) -> None:
        self.pending_locked_date = today
        self.record_result("pending_locked", "Workstation is locked; retry will run after unlock.")

    def record_success(self, today: str, status: str, message: str) -> None:
        self.last_success_date = today
        self.pending_locked_date = None
        self.last_screenshot = None
        self.record_result(status, message)

    def record_failure(self, message: str, screenshot: str | None = None) -> None:
        self.last_screenshot = screenshot
        self.record_result("failed_action_required", message)

    def record_result(self, status: str, message: str) -> None:
        self.last_status = status
        self.last_message = message
        if status != "failed_action_required":
            self.last_screenshot = None
        self.updated_at = datetime.now().isoformat(timespec="seconds")

    @staticmethod
    def _persisted_keys() -> tuple[str, ...]:
        return (
            "last_success_date",
            "pending_locked_date",
            "last_status",
            "last_message",
            "last_screenshot",
            "updated_at",
        )
