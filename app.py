import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from config import API_TOKEN, settings
from app_compose import compose_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("crane.app")

# A2: All component wiring lives in compose_app() now — no more ad-hoc globals.
# This guarantees events/metrics/trace are shared across all components
# (regression fix for Phase 1 bug where they were only passed to VisionRuntime).
_components = compose_app()
events = _components["events"]
metrics = _components["metrics"]
trace = _components["trace"]
state_machine = _components["state_machine"]
camera = _components["camera"]
ptz = _components["ptz"]
brain = _components["brain"]
runtime = _components["runtime"]
operator = _components["operator"]
notifications = _components["notifications"]
event_store = _components["event_store"]

_security = HTTPBasic()


def require_auth(credentials: HTTPBasicCredentials = Depends(_security)):
    valid_user = secrets.compare_digest(credentials.username, settings.web.auth_username)
    valid_pass = secrets.compare_digest(credentials.password, API_TOKEN)
    if not (valid_user and valid_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    runtime.start()
    notifications.start()
    yield
    notifications.stop()
    runtime.stop()


app = FastAPI(lifespan=lifespan, dependencies=[Depends(require_auth)])


@app.get("/")
def read_root():
    return FileResponse("index.html")


@app.get("/stream")
def stream():
    return StreamingResponse(runtime.mjpeg_generator(), media_type="multipart/x-mixed-replace; boundary=--frame")


@app.get("/api/status")
def get_status():
    return runtime.status()


@app.get("/api/history")
def get_history(limit: int = 100, name: str = None):
    """SQLite-backed event history. Survives server restarts.

    Query params:
        limit: number of events to return (default 100, max 1000)
        name:  filter by event name (e.g. "target_detected")
    """
    limit = max(1, min(limit, 1000))
    events = event_store.get_recent(limit=limit, name_filter=name)
    return {
        "total": event_store.count(name_filter=name),
        "returned": len(events),
        "events": events,
    }


@app.delete("/api/history")
def clear_history():
    """Delete all event history. Use with caution."""
    deleted = event_store.clear()
    return {"deleted": deleted}


@app.get("/history")
def history_page():
    """Web UI for browsing event history."""
    return FileResponse("history.html")


@app.get("/api/move")
def manual_move(direction: str):
    # Delegate to OperatorService for consistent manual command handling
    return operator.move(direction)


@app.get("/api/zoom")
def manual_zoom(direction: str):
    # Delegate to OperatorService for zoom control
    return operator.zoom(direction)


@app.get("/api/focus")
def manual_focus(direction: str):
    # Delegate to OperatorService for focus control
    return operator.focus(direction)




@app.post("/api/toggle_guard")
def toggle_guard():
    return {"status": runtime.toggle_guard()}
