"""
app_compose.py — Dependency injection container for the Boras application.

Centralizes the wiring of all components (state_machine, camera, ptz, brain,
runtime, operator) with shared events/metrics/trace. This replaces the
ad-hoc global initialization that lived in app.py and was the original source
of the "events not wired into all components" bug (Phase 1 critical finding).

Usage:
    from app_compose import compose_app
    components = compose_app()
    runtime = components['runtime']
    app = create_fastapi_app(components)

Or via the convenience function:
    from app_compose import build_app
    app = build_app()  # returns FastAPI app with everything wired
"""
import logging
from typing import Dict, Any

from config import API_TOKEN, CAMERA_IP, CAMERA_PASS, CAMERA_USER, settings
from core.events import EventLog
from core.event_store import EventStore
from core.metrics import RuntimeMetrics
from core.state_machine import CraneStateMachine
from core.tracking_trace import TrackingTrace
from services.camera_service import CameraStream
from services.notification_service import NotificationService
from services.operator_service import OperatorService
from services.ptz_service import CranePTZ
from services.vision_service import SecurityBrain, VisionRuntime

logger = logging.getLogger("crane.app")


def compose_app(
    camera_ip: str = None,
    camera_user: str = None,
    camera_pass: str = None,
    api_token: str = None,
    settings_override=None,
) -> Dict[str, Any]:
    """Build all application components with shared events/metrics/trace.

    All four critical components (state_machine, camera, ptz, brain) receive
    the SAME events/metrics/trace instances — this is the regression fix for
    the Phase 1 bug where they were only passed to VisionRuntime.

    Note: lights functionality was removed — the camera has its own light
    sensors and manages IR/White light automatically.

    Args:
        camera_ip / camera_user / camera_pass / api_token:
            Optional overrides. Defaults come from config module.
        settings_override:
            Optional Settings instance for testing (overrides the singleton).

    Returns:
        Dict with keys: events, metrics, trace, event_store, state_machine,
        camera, ptz, brain, runtime, operator, notifications.
    """
    cfg = settings_override or settings
    ip = camera_ip or CAMERA_IP
    user = camera_user or CAMERA_USER
    password = camera_pass or CAMERA_PASS
    token = api_token or API_TOKEN  # noqa: F841 — kept for completeness

    # Shared singletons — ALL components get the SAME instance.
    # This is the key fix: previously app.py only passed these to VisionRuntime.
    events = EventLog()
    metrics = RuntimeMetrics()
    trace = TrackingTrace()

    # SQLite-backed event store — persists events across server restarts.
    # Every emit() will now also write to SQLite via this listener.
    event_store = EventStore(db_path="events.db")
    events.add_listener(lambda ev: event_store.save(ev.name, ev.detail, ev.created_at))

    state_machine = CraneStateMachine(events=events)
    camera = CameraStream(
        ip=ip, username=user, password=password,
        events=events, metrics=metrics,
    )
    ptz = CranePTZ(
        ip=ip, username=user, password=password,
        events=events, metrics=metrics, trace=trace,
    )
    brain = SecurityBrain(
        ptz, state_machine=state_machine, events=events,
        metrics=metrics, trace=trace,
    )
    runtime = VisionRuntime(
        camera=camera,
        brain=brain,
        ptz=ptz,
        state_machine=state_machine,
        events=events,
        metrics=metrics,
        trace=trace,
    )
    operator = OperatorService(runtime, ptz, logger)

    # NotificationService — watches events for target_detected/target_lost/error
    # and sends Telegram alerts (or any other configured provider).
    # Snapshot provider captures the current JPEG frame for photo alerts.
    notifications = NotificationService(
        events=events,
        snapshot_provider=runtime.get_snapshot,
    )

    return {
        "events": events,
        "metrics": metrics,
        "trace": trace,
        "event_store": event_store,
        "state_machine": state_machine,
        "camera": camera,
        "ptz": ptz,
        "brain": brain,
        "runtime": runtime,
        "operator": operator,
        "notifications": notifications,
    }
