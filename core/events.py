from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import Lock


@dataclass(frozen=True)
class CraneEvent:
    name: str
    created_at: datetime
    detail: str = ""


def make_event(name, detail=""):
    return CraneEvent(name=name, detail=detail, created_at=datetime.now(timezone.utc))


class EventLog:
    def __init__(self, maxlen=100):
        self._events = deque(maxlen=maxlen)
        self._lock = Lock()

    def emit(self, name, detail=""):
        event = make_event(name, detail)
        with self._lock:
            self._events.append(event)
        return event

    def recent(self, limit=20):
        with self._lock:
            events = list(self._events)[-limit:]
        return [
            {
                **asdict(event),
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ]
