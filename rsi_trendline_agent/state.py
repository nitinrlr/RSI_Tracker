from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class AlertState:
    data: dict[str, Any]

    @classmethod
    def load(cls, path: str | Path) -> "AlertState":
        state_path = Path(path)
        if not state_path.exists():
            return cls(data={})
        return cls(data=json.loads(state_path.read_text(encoding="utf-8")))

    def already_alerted(self, key: str, event_index: int) -> bool:
        record = self.data.get(key)
        return bool(record and record.get("event_index") == event_index)

    def mark_alerted(self, key: str, event_index: int, payload: dict[str, Any]) -> None:
        self.data[key] = {"event_index": event_index, **payload}

    def save(self, path: str | Path) -> None:
        state_path = Path(path)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(self.data, indent=2, sort_keys=True), encoding="utf-8")
