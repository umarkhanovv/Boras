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
lights = _components["lights"]
brain = _components["brain"]
runtime = _components["runtime"]
operator = _components["operator"]

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
    yield
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




@app.post("/api/lights")
def set_lights(mode: str, brightness: int = 100):
    # Delegate to OperatorService for consistent lighting control
    return operator.set_lights(mode, brightness)


@app.post("/api/toggle_guard")
def toggle_guard():
    return {"status": runtime.toggle_guard()}
