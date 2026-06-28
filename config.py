"""
config.py — Centralized configuration for Boras Crane Vision.

All tuning parameters live here as dataclass defaults. Credentials continue
to load from environment variables or config_local.py (gitignored).

Module-level CAMERA_IP / CAMERA_USER / CAMERA_PASS / API_TOKEN are preserved
for backward compatibility with existing imports like:
    from config import CAMERA_IP, CAMERA_USER, CAMERA_PASS, API_TOKEN

To override tuning parameters without code changes, set environment variables:
    CRANE_YOLO_MODEL=yolov8s.pt
    CRANE_FRAME_SKIP_RATE=5
    CRANE_AUTH_USERNAME=operator
    CRANE_PTZ_PROFILE=PROFILE_001
    CRANE_MIN_COMMAND_INTERVAL=0.2
    CRANE_PAN_SPEED_GAIN=0.6
    CRANE_MIN_PAN_SPEED=0.1
"""
import os
from dataclasses import dataclass, field
from typing import List


# ─── Credentials (env vars or config_local.py) ─────────────────────────────

CAMERA_IP = os.environ.get("CRANE_CAMERA_IP", "")
CAMERA_USER = os.environ.get("CRANE_CAMERA_USER", "")
CAMERA_PASS = os.environ.get("CRANE_CAMERA_PASS", "")
API_TOKEN = os.environ.get("CRANE_API_TOKEN", "")

# Local-dev override file (not committed) lets you skip exporting env vars.
try:
    from config_local import *  # noqa: F401,F403
except ImportError:
    pass

if not CAMERA_IP or not CAMERA_PASS:
    raise RuntimeError(
        "Camera credentials are not configured.\n"
        "Set CRANE_CAMERA_IP / CRANE_CAMERA_USER / CRANE_CAMERA_PASS as "
        "environment variables, or copy config_local.example.py to "
        "config_local.py and fill in real values (that file is gitignored)."
    )

if not API_TOKEN:
    raise RuntimeError(
        "CRANE_API_TOKEN is not set. Choose a long random string and set "
        "it via env var or config_local.py — it's the password for the "
        "web control panel."
    )


# ─── Tuning parameters (dataclass defaults, env-overridable) ───────────────

@dataclass
class CameraConfig:
    """RTSP connection parameters.

    rtsp_paths is a list of path templates tried in order during connection.
    The first one that opens and returns a frame becomes the working URL.
    Add your camera's specific path here if none of the defaults work.
    """
    rtsp_paths: List[str] = field(default_factory=lambda: [
        "/live/0/MAIN",                                # primary stream (most cameras)
        "/live/0/SUB",                                 # substream fallback
        "/h264/ch1/main/av_stream",                    # Hikvision-style
        "/cam/realmonitor?channel=1&subtype=0",        # Dahua-style
    ])
    rtsp_port: int = 554
    http_port: int = 80
    reconnect_delay: float = 3.0  # seconds between reconnect attempts


@dataclass
class PTZConfig:
    """ONVIF PTZ service parameters."""
    profile: str = "PROFILE_000"             # ONVIF media profile token
    video_source: str = "000"                # ONVIF video source token
    min_command_interval: float = 0.15       # seconds between same-key commands (throttle)
    http_timeout: float = 2.0                # seconds for ONVIF SOAP requests
    # Many cameras don't support ONVIF Imaging service focus control and
    # return HTTP 400. Set to False to skip focus commands entirely
    # (zoom will still work, focus will drift but not break the pipeline).
    enable_focus_control: bool = True


@dataclass
class VisionConfig:
    """YOLO detection and frame processing parameters."""
    yolo_model: str = "yolov8n.pt"           # weights file (yolov8n/s/m/l/x)
    detect_classes: List[int] = field(default_factory=lambda: [0])  # COCO class 0 = person
    frame_skip_rate: int = 3                 # process every Nth frame (1 = every frame)
    jpeg_quality: int = 80                   # MJPEG stream quality (0-100)


@dataclass
class TrackingConfig:
    """AutoTracker aiming parameters.

    All values are in normalized camera-speed units (-1.0 to 1.0) unless noted.
    """
    pan_speed_gain: float = 0.5        # multiplier for offset-to-speed conversion
    min_pan_speed: float = 0.08        # minimum |speed| to overcome deadzone jitter
    deadzone_frac_x: float = 0.15      # fraction of frame width (centered) where no pan happens
    deadzone_frac_y: float = 0.15      # fraction of frame height (centered) where no tilt happens
    height_target_low: float = 0.40    # below this height ratio → zoom in
    height_target_high: float = 0.75   # above this height ratio → zoom out
    zoom_speed: float = 0.15           # continuous zoom speed when adjusting
    focus_speed: float = 0.1           # continuous focus speed when adjusting zoom


@dataclass
class PatrolConfig:
    """SmartPatrol scanning parameters (all times in seconds)."""
    zoom_out_speed: float = -0.5       # zoom speed during initial zoom-out phase
    zoom_out_focus: float = -0.1       # focus speed during initial zoom-out phase
    pan_speed: float = 0.12            # slow pan speed during patrol
    zoom_out_duration: float = 3.0     # seconds to zoom out before starting pan cycle
    cycle_duration: float = 4.0        # seconds per pan-pause cycle
    pan_duration: float = 2.0          # seconds of panning within each cycle (rest is pause)


@dataclass
class WebConfig:
    """Web server / auth parameters."""
    auth_username: str = "admin"       # HTTP Basic Auth username (password = API_TOKEN)
    stream_sleep: float = 0.05         # MJPEG generator sleep between frames (seconds)
    loop_sleep: float = 0.03           # processing loop sleep between frames (seconds)
    no_frame_sleep: float = 0.05       # sleep when camera has no frame yet (seconds)


@dataclass
class OperatorConfig:
    """Operator / manual control parameters (B3 soft manual override)."""
    # After a manual command, auto-guard stays disabled for this many seconds.
    # If no further manual command arrives, auto-guard re-enables automatically.
    # Set to 0.0 to disable soft override (legacy behavior: manual kills guard
    # until operator re-toggles).
    manual_override_timeout: float = 10.0


@dataclass
class NotificationConfig:
    """Notifications via external providers (Telegram, etc.).
    Set enabled=False to disable all notifications.
    Telegram requires both token and chat_id to be set.
    """
    enabled: bool = False                  # master switch
    # Telegram bot token from @BotFather (e.g. "123456:ABC-DEF...")
    telegram_token: str = ""
    # Telegram chat ID to send messages to (e.g. "123456789" for private chat)
    telegram_chat_id: str = ""
    # Minimum seconds between notifications (rate limit, prevents spam)
    rate_limit_seconds: float = 30.0
    # How often NotificationService polls EventLog for new events (seconds)
    poll_interval: float = 2.0
    # Which event names trigger a notification
    notify_on: tuple = (
        "target_detected",   # PATROL → TRACKING transition
        "target_lost",       # TRACKING → PATROL transition
        "error",             # any system error
        "disconnected",      # RTSP stream lost
    )


@dataclass
class Settings:
    """Top-level settings container. Access sections via settings.camera,
    settings.ptz, settings.vision, settings.tracking, settings.patrol, settings.web,
    settings.operator, settings.notifications.
    """
    camera: CameraConfig = field(default_factory=CameraConfig)
    ptz: PTZConfig = field(default_factory=PTZConfig)
    vision: VisionConfig = field(default_factory=VisionConfig)
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    patrol: PatrolConfig = field(default_factory=PatrolConfig)
    web: WebConfig = field(default_factory=WebConfig)
    operator: OperatorConfig = field(default_factory=OperatorConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)


# Singleton instance — import this everywhere as `from config import settings`
settings = Settings()


# ─── Env overrides for key tuning parameters ───────────────────────────────
# Allows changing tuning without code edits. Credentials are handled above
# (they MUST come from env/config_local for security).

def _env_str(name, default):
    val = os.environ.get(name)
    return val if val is not None else default

def _env_int(name, default):
    val = os.environ.get(name)
    return int(val) if val is not None else default

def _env_float(name, default):
    val = os.environ.get(name)
    return float(val) if val is not None else default


# Apply env overrides to singleton settings instance
settings.vision.yolo_model = _env_str("CRANE_YOLO_MODEL", settings.vision.yolo_model)
settings.vision.frame_skip_rate = _env_int("CRANE_FRAME_SKIP_RATE", settings.vision.frame_skip_rate)
settings.web.auth_username = _env_str("CRANE_AUTH_USERNAME", settings.web.auth_username)
settings.ptz.profile = _env_str("CRANE_PTZ_PROFILE", settings.ptz.profile)
settings.ptz.min_command_interval = _env_float("CRANE_MIN_COMMAND_INTERVAL", settings.ptz.min_command_interval)
settings.tracking.pan_speed_gain = _env_float("CRANE_PAN_SPEED_GAIN", settings.tracking.pan_speed_gain)
settings.tracking.min_pan_speed = _env_float("CRANE_MIN_PAN_SPEED", settings.tracking.min_pan_speed)
settings.operator.manual_override_timeout = _env_float("CRANE_MANUAL_OVERRIDE_TIMEOUT", settings.operator.manual_override_timeout)

# Notifications — Telegram alerts
_tg_token = os.environ.get("CRANE_TELEGRAM_TOKEN", "")
_tg_chat_id = os.environ.get("CRANE_TELEGRAM_CHAT_ID", "")
if _tg_token:
    settings.notifications.telegram_token = _tg_token
if _tg_chat_id:
    settings.notifications.telegram_chat_id = _tg_chat_id
# Auto-enable notifications if both token and chat_id are set via env
if _tg_token and _tg_chat_id:
    settings.notifications.enabled = True
# Allow explicit enable/disable override
_tg_enabled = os.environ.get("CRANE_NOTIFICATIONS_ENABLED")
if _tg_enabled is not None:
    settings.notifications.enabled = _tg_enabled.lower() in ("1", "true", "yes", "on")
