import time
from threading import Lock


class RuntimeMetrics:
    def __init__(self):
        self._lock = Lock()
        self._started_at = time.monotonic()
        self.frames_seen = 0
        self.frames_processed = 0
        self.frames_encoded = 0
        self.detections_count = 0
        self.ptz_commands = 0
        self.errors = 0

    def seen_frame(self):
        with self._lock:
            self.frames_seen += 1

    def processed_frame(self):
        with self._lock:
            self.frames_processed += 1

    def encoded_frame(self):
        with self._lock:
            self.frames_encoded += 1

    def detected(self):
        with self._lock:
            self.detections_count += 1

    def ptz_command(self):
        with self._lock:
            self.ptz_commands += 1

    def error(self):
        with self._lock:
            self.errors += 1

    def snapshot(self):
        with self._lock:
            elapsed = max(time.monotonic() - self._started_at, 0.001)
            return {
                "fps": round(self.frames_seen / elapsed, 2),
                "frames_seen": self.frames_seen,
                "frames_processed": self.frames_processed,
                "frames_encoded": self.frames_encoded,
                "detections_count": self.detections_count,
                "ptz_commands": self.ptz_commands,
                "errors": self.errors,
            }
