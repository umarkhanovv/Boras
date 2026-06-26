 🎯 Boras — AI Security System

 Intelligent PTZ camera security system powered by YOLOv8. Automatically detects people, tracks their movement via ONVIF PTZ control, and patrols the perimeter when no targets are present.

 ![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
 ![Tests](https://img.shields.io/badge/tests-223%20passing-brightgreen.svg)
 ![License](https://img.shields.io/badge/license-MIT-green.svg)

 ## ✨ Features

 - **Real-time Detection** — YOLOv8 person tracking with configurable frame skip rate
 - **Auto-Guard Mode** — Smooth pan/tilt/zoom aiming with deadzone suppression
 - **Smart Patrol** — Automatic perimeter scanning (zoom-out → pan → pause cycle) when no targets
 - **Soft Manual Override** — Manual commands pause auto-guard for 10s, then auto-resume
 - **Multi-URL RTSP Fallback** — Tries 4 RTSP path templates (MAIN/SUB/Hikvision/Dahua)
 - **PTZ Throttle Bypass** — Instant response on direction change (no 150ms lag)
 - **Connection Health** — Separate RTSP and PTZ HTTP status in `/api/status`
 - **Tracking Trace** — 5-stage debug recorder (YOLO → target → auto_aim → ptz_command → ptz_http)
 - **Rolling FPS** — Last-N-frames window instead of useless lifetime average
 - **Configurable** — All tuning parameters in `Settings` dataclass, env-overridable
 - **223 Tests** — Full pytest suite running in ~3s without camera/network/YOLO weights

 ## 🚀 Quick Start

 ### Prerequisites

 - Python 3.12+
 - PTZ camera with ONVIF support
 - RTSP stream access

 ### Installation

 ```bash
 # Clone the repository
 git clone https://github.com/umarkhanovv/Boras.git
 cd Boras

 # Create virtual environment
 python -m venv ai_env
 source ai_env/bin/activate    # Linux/macOS
 # ai_env\Scripts\activate     # Windows

 # Install dependencies
 pip install -r requirements.txt
 pip install pytest
 ```

 ### Configuration

 Copy the credentials template and fill in your camera details:

 ```bash
 cp config_local.example.py config_local.py
 ```

 Edit `config_local.py`:

 ```python
 CAMERA_IP = "10.0.0.1"                    # your camera IP
 CAMERA_USER = "admin"                     # camera ONVIF username
 CAMERA_PASS = "your-camera-password"      # camera password

 # Web panel password (NOT the camera password)
 # Username defaults to "admin" (configurable via CRANE_AUTH_USERNAME)
 API_TOKEN = "your-long-random-string"
 ```

 > **Note:** `config_local.py` is gitignored — your credentials never get committed.

 ### Run

 ```bash
 uvicorn app:app --reload
 ```

 Open http://127.0.0.1:8000/ in your browser. Login with `admin` / your `API_TOKEN`.

 ## ⚙️ Configuration

 All tuning parameters live in `config.py` as a `Settings` dataclass with 7 sections:

 | Section | Purpose |
 |---|---|
 | `camera` | RTSP paths, ports, reconnect delay |
 | `ptz` | ONVIF profile, throttle interval, HTTP timeout, focus control toggle |
 | `vision` | YOLO model, detect classes, frame skip rate, JPEG quality |
 | `tracking` | Pan/tilt/zoom speeds, deadzone, height ratio targets |
 | `patrol` | Patrol scan timings, pan speed |
 | `web` | Auth username, MJPEG/loop sleep intervals |
 | `operator` | Soft manual override timeout |

 Override via environment variables (no code changes needed):

 ```bash
 export CRANE_YOLO_MODEL=yolov8s.pt              # heavier but more accurate
 export CRANE_FRAME_SKIP_RATE=5                  # process every 5th frame
 export CRANE_AUTH_USERNAME=operator             # web panel username
 export CRANE_PTZ_PROFILE=PROFILE_001            # ONVIF profile token
 export CRANE_MIN_COMMAND_INTERVAL=0.2           # PTZ throttle interval
 export CRANE_PAN_SPEED_GAIN=0.6                 # faster panning
 export CRANE_MANUAL_OVERRIDE_TIMEOUT=30         # soft override timeout
 export CRANE_DISABLE_FOCUS=1                    # disable focus (unsupported cameras)
 ```

 ## 🧪 Testing

 ```bash
 # Run all 223 tests
 python -m pytest tests/

 # Full CI check (compile + tests + e2e smoke test)
 bash scripts/ci.sh

 # End-to-end smoke test (no camera needed)
 python scripts/e2e_trace_check.py
 ```

 Tests run in ~3 seconds without requiring a camera, network, or YOLO weights. Stubs for `ultralytics` and `cv2` are auto-loaded in `tests/conftest.py`.

 ## 🔍 API Reference

 ### `GET /`
 Serves the operator console UI (`index.html`). Requires HTTP Basic Auth.

 ### `GET /stream`
 MJPEG video stream with YOLO annotations. Use in `<img>` tag.

 ### `GET /api/status`
 Returns full system state as JSON:

 ```json
 {
   "camera_status": "live",
   "auto_guard": true,
   "mode": "TRACKING",
   "metrics": {
     "fps": 20.5,
     "fps_lifetime_avg": 21.2,
     "frames_seen": 4199,
     "frames_processed": 285,
     "detections_count": 189,
     "ptz_commands": 12,
     "errors": 0
   },
   "events": [...],
   "tracking_trace": {
     "yolo": {"boxes": 1},
     "target": {"cx": 1124.6, "cy": 829.0, "height": 477},
     "auto_aim": {"decision": "tilt", "speed_y": 0.268},
     "ptz_command": {"kind": "move", "pan": 0.0, "tilt": -0.268},
     "ptz_http": {"sent": true, "http": 200, "ok": true}
   },
   "connection_health": {
     "rtsp": {"rtsp_healthy": true, "last_frame_age_s": 0.09},
     "ptz": {"ptz_reachable": true, "last_http_status": 200}
   }
 }
 ```

 ### `GET /api/move?direction=left|right|up|down|stop`
 Manual PTZ control. Triggers soft manual override.

 ### `GET /api/zoom?direction=in|out|stop`
 Manual zoom control.

 ### `GET /api/focus?direction=near|far|stop`
 Manual focus control (disabled if `CRANE_DISABLE_FOCUS=1`).

 ### `POST /api/toggle_guard`
 Toggle auto-guard on/off.

 ## 🩺 Troubleshooting

 Use `/api/status` to diagnose issues:

 | Symptom | Cause | Fix |
 |---|---|---|
 | `camera_status: "failed"` | RTSP unreachable | Check IP/credentials/firewall |
 | `connection_health.ptz.ptz_reachable: false` | ONVIF HTTP unreachable | Verify port 80 open on camera |
 | `connection_health.ptz.last_http_status: 401` | Wrong ONVIF credentials | Check `CAMERA_USER`/`CAMERA_PASS` |
 | `tracking_trace.yolo.boxes: 0` | YOLO finds no person | Check lighting, try `yolov8s.pt` |
 | `tracking_trace.ptz_http.ok: false` | Camera rejected SOAP | Check `CRANE_PTZ_PROFILE` |
 | `metrics.errors` growing | Recurring errors | Check `events` array for error details |

 ## 📂 Project Structure

 ```
 Boras/
 ├── app.py                       # FastAPI entry, HTTP Basic Auth
 ├── app_compose.py               # DI container (compose_app)
 ├── config.py                    # Settings dataclass (7 sections)
 ├── config_local.example.py      # Credentials template
 ├── conftest.py                  # Pytest root config
 ├── pytest.ini
 ├── requirements.txt
 ├── index.html                   # Operator Console UI
 ├── camera_stream.py             # Backward compat wrapper
 ├── control.py                   # Backward compat wrapper
 ├── security_brain.py            # Backward compat wrapper
 ├── core/
 │   ├── events.py                # EventLog (ring buffer)
 │   ├── metrics.py               # RuntimeMetrics (rolling FPS)
 │   ├── state_machine.py         # CraneStateMachine (IDLE/PATROL/TRACKING/MANUAL)
 │   └── tracking_trace.py        # 5-stage debug recorder
 ├── behavior/
 │   ├── tracking.py              # AutoTracker (pan/tilt/zoom aim)
 │   └── patrol.py                # SmartPatrol (scan cycle)
 ├── services/
 │   ├── camera_service.py        # RTSP stream + 4 URL fallbacks + health()
 │   ├── ptz_service.py           # ONVIF PTZ (SOAP, throttle bypass, health())
 │   ├── vision_service.py        # SecurityBrain + VisionRuntime
 │   ├── target_manager.py        # Group target from YOLO boxes
 │   └── operator_service.py      # Manual commands
 ├── tests/                       # 223 tests
 │   ├── conftest.py              # Fixtures + stubs
 │   ├── test_target_manager.py
 │   ├── test_auto_tracker.py
 │   ├── test_state_machine.py
 │   ├── test_smart_patrol.py
 │   ├── test_tracking_trace.py
 │   ├── test_metrics.py          # Rolling FPS tests
 │   ├── test_app_wiring.py       # Wiring regression suite
 │   ├── test_config.py           # Settings + env overrides
 │   ├── test_ptz_service.py      # Throttle bypass + health
 │   ├── test_app_compose.py      # compose_app DI tests
 │   └── test_soft_override.py    # B3 soft manual override
 └── scripts/
     ├── ci.sh                    # CI: compileall → pytest → e2e
     └── e2e_trace_check.py       # Smoke test (no camera)
 ```

 ## 🏗 Architecture

 ```
                     ┌──────────────────────────────────────────┐
                     │              compose_app()               │
                     │         (DI container in app.py)         │
                     └──────────────────────────────────────────┘
                                       │
         ┌─────────────────┬───────────┼───────────┬─────────────────┐
         ▼                 ▼           ▼           ▼                 ▼
   ┌──────────┐     ┌──────────┐ ┌──────────┐ ┌──────────┐      ┌──────────┐
   │  Camera  │     │   PTZ    │ │  Brain   │ │  State   │      │ Operator │
   │  Stream  │     │  Service │ │  (YOLO)  │ │  Machine │      │ Service  │
   └────┬─────┘     └────┬─────┘ └────┬─────┘ └────┬─────┘      └────┬─────┘
        │                │            │            │                 │
        │   shared       │   shared   │   shared   │      shared     │
        │   events,      │   events,  │   events,  │                 │
        │   metrics,     │   metrics, │   metrics, │                 │
        │   trace ◄──────┴────────────┴────────────┘                 │
        │                                                            │
        ▼                                                            ▼
   RTSP stream                                                  /api/move
   /api/status                                                  /api/zoom
   /stream                                                      /api/focus
                                                                /api/toggle_guard
 ```

 All components share the same `EventLog`, `RuntimeMetrics`, and `TrackingTrace` instances — this was the critical bug fix from Phase 1 (previously only `VisionRuntime` received them).

 ## 🔄 State Machine

 ```
                 ┌──────┐
                 │ IDLE │ ◄─────────────────────────┐
                 └──┬───┘                           │
                    │ enable_auto_guard             │ disable_auto_guard
                    ▼                               │
                 ┌──────┐                           │
        ┌──────► │PATROL│ ◄─────────────┐           │
        │        └──┬───┘               │           │
        │           │ target_detected   │ target_   │
        │           ▼                   │ lost      │
        │        ┌──────┐               │           │
        │        │TRACK │ ──────────────┘           │
        │        │ ING  │                           │
        │        └──────┘                           │
        │                                           │
        │   manual command (10s timeout)            │
        │   ┌──────┐                                │
        └───┤MANUAL│ ───────────────────────────────┘
            └──────┘
              │
              │ timeout expired (auto-return)
              └────────────────────────────────────► PATROL
 ```

 ## 📦 Dependencies

 - `fastapi` 0.138 — Web framework
 - `uvicorn` 0.49 — ASGI server
 - `opencv-python` 4.13 — RTSP capture + frame encoding
 - `ultralytics` 8.4 — YOLOv8 inference
 - `torch` 2.12 + `torchvision` 0.27 — PyTorch backend
 - `requests` 2.34 — ONVIF SOAP HTTP client

 See `requirements.txt` for pinned versions.

 ## 🤝 Contributing

 1. Fork the repository
 2. Create a feature branch: `git checkout -b feature/amazing-feature`
 3. Run tests: `bash scripts/ci.sh`
 4. Commit changes: `git commit -m 'Add amazing feature'`
 5. Push to branch: `git push origin feature/amazing-feature`
 6. Open a Pull Request

 ## 📝 License

 Distributed under the MIT License. See `LICENSE` for more information.

 ## 👤 Author

 **Umarkhanov Askhat**

 ## 🙏 Acknowledgments

 - [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) — Real-time object detection
 - [ONVIF](https://www.onvif.org/) — Open network video interface standard
 - [FastAPI](https://fastapi.tiangolo.com/) — Modern Python web framework
