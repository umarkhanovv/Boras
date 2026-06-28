# Boras-Lab: AI Security System

Интеллектуальная система безопасности на базе YOLOv8 и PTZ-камер. Система автоматически обнаруживает людей, отслеживает их перемещение через PTZ-наведение и управляет режимом патрулирования при отсутствии целей.

## 🚀 Быстрый старт

### 1. Подготовка окружения (Python 3.12+)

```bash
python -m venv ai_env
source ai_env/bin/activate  # Linux/macOS
# ai_env\Scripts\activate   # Windows
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
pip install pytest  # для запуска тестов
```

### 3. Конфигурация

Учётные данные камеры хранятся в `config_local.py` (gitignored). Скопируй шаблон:

```bash
cp config_local.example.py config_local.py
```

Затем впиши свои значения `CAMERA_IP` / `CAMERA_USER` / `CAMERA_PASS` / `API_TOKEN` в `config_local.py`.

Альтернативно — переменные окружения:

```bash
export CRANE_CAMERA_IP="10.60.98.215"
export CRANE_CAMERA_USER="admin"
export CRANE_CAMERA_PASS="your-password"
export CRANE_API_TOKEN="long-random-string"
```

`API_TOKEN` — пароль для веб-панели управления (HTTP Basic Auth, логин: `admin` по умолчанию). Без него приложение не запустится.

### 4. Запуск системы

```bash
uvicorn app:app --reload
```

После запуска открой в браузере: http://127.0.0.1:8000/ (потребуется логин: `admin` / твой `API_TOKEN`)

## 📂 Структура проекта

```
Boras/
├── app.py                      # FastAPI entry point, веб-аутентификация
├── app_compose.py              # DI-контейнер: compose_app() — вся проводка компонентов
├── config.py                   # Settings dataclass (7 секций, env-overridable)
├── config_local.example.py     # Шаблон кредов (скопируй в config_local.py)
├── conftest.py                 # Pytest root config (sys.path, env vars)
├── pytest.ini
├── requirements.txt
├── index.html                  # Operator Console UI
├── camera_stream.py            # Root wrapper (backward compat)
├── control.py                  # Root wrapper (backward compat)
├── security_brain.py           # Root wrapper (backward compat)
├── core/
│   ├── events.py               # EventLog — кольцевой буфер событий
│   ├── metrics.py              # RuntimeMetrics — rolling FPS + счётчики
│   ├── state_machine.py        # CraneStateMachine (IDLE/PATROL/TRACKING/MANUAL)
│   └── tracking_trace.py       # 5-stage recorder для /api/status
├── behavior/
│   ├── tracking.py             # AutoTracker — pan/tilt/zoom наведение
│   └── patrol.py               # SmartPatrol — zoom-out → pan → pause цикл
├── services/
│   ├── camera_service.py       # RTSP stream (4 URL fallback) + health()
│   ├── ptz_service.py          # ONVIF PTZ (SOAP, throttle bypass, health())
│   ├── vision_service.py       # SecurityBrain (YOLO) + VisionRuntime
│   ├── target_manager.py       # Group target из YOLO boxes
│   └── operator_service.py     # Ручные команды move/zoom/focus
├── tests/                      # 223 теста (pytest)
│   ├── conftest.py             # Фикстуры + stubs (ultralytics, cv2)
│   ├── test_target_manager.py
│   ├── test_auto_tracker.py
│   ├── test_state_machine.py
│   ├── test_smart_patrol.py
│   ├── test_tracking_trace.py
│   ├── test_metrics.py         # Rolling FPS тесты
│   ├── test_app_wiring.py      # Регрессионный сет проводки
│   ├── test_config.py          # Settings + env overrides
│   ├── test_ptz_service.py     # Throttle bypass + health
│   ├── test_app_compose.py     # compose_app DI тесты
│   └── test_soft_override.py   # B3 soft manual override
└── scripts/
    ├── ci.sh                   # CI: compileall → pytest → e2e
    └── e2e_trace_check.py      # Smoke test (без камеры)
```

## 🛠 Возможности

- **Auto-Guard**: Плавное наведение на объект с подавлением дребезга и throttle bypass при смене направления
- **Smart Patrol**: Автоматическое сканирование периметра при отсутствии целей (zoom-out → pan → pause цикл)
- **Soft Manual Override**: Ручные команды временно приостанавливают auto-guard (10 сек), затем автоматически возвращается PATROL
- **Connection Health**: Раздельные статусы для RTSP стрима и PTZ HTTP в `/api/status`
- **Tracking Trace**: 5-стадийный рекордер (YOLO → target → auto_aim → ptz_command → ptz_http) для отладки
- **Rolling FPS**: Last-N-frames rolling window вместо lifetime average
- **Web-UI**: Потоковая передача с метаданными ИИ в реальном времени, защищена логином
- **RTSP Fallback**: 4 разных RTSP path template (MAIN/SUB/Hikvision/Dahua) для совместимости с разными камерами
- **Configurable**: Все tuning-параметры в `config.py` (Settings dataclass), env-overridable

## ⚙️ Настройка параметров (env vars)

Все параметры можно переопределить без правки кода:

```bash
export CRANE_YOLO_MODEL=yolov8s.pt              # heavier but more accurate model
export CRANE_FRAME_SKIP_RATE=5                  # process every 5th frame (less CPU)
export CRANE_AUTH_USERNAME=operator             # web panel username
export CRANE_PTZ_PROFILE=PROFILE_001            # ONVIF profile token
export CRANE_MIN_COMMAND_INTERVAL=0.2           # PTZ throttle interval
export CRANE_PAN_SPEED_GAIN=0.6                 # faster panning
export CRANE_MIN_PAN_SPEED=0.1                  # higher minimum pan speed
export CRANE_MANUAL_OVERRIDE_TIMEOUT=30         # soft override timeout (seconds)
export CRANE_DISABLE_FOCUS=1                    # disable focus control (camera doesn't support)
```

## 🧪 Тестирование

```bash
# Запустить все тесты
python3 -m pytest tests/

# Полная CI-проверка
bash scripts/ci.sh

# Smoke test без камеры
python3 scripts/e2e_trace_check.py
```

Ожидаемый результат: `223 passed in ~3s`

## 🔍 Отладка

### `/api/status`

Возвращает полный снимок состояния системы:

```json
{
  "camera_status": "live",
  "auto_guard": true,
  "mode": "TRACKING",
  "metrics": {
    "fps": 20.5,
    "fps_lifetime_avg": 21.2,
    "frames_seen": 4199,
    "detections_count": 189,
    "ptz_commands": 12,
    "errors": 0
  },
  "events": [...],
  "tracking_trace": {
    "yolo": {"boxes": 1},
    "target": {"cx": 1124.6, "cy": 829.0},
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

### Диагностика по `tracking_trace`

| Симптом | Диагноз |
|---|---|
| `yolo.boxes = 0` | YOLO не находит человека |
| `auto_aim.decision = "hold"` | Таргет в центре, камера правильно стоит |
| `ptz_http.throttled = true` | Команда отброшена throttle (нормально) |
| `ptz_http.ok = false` | HTTP ошибка — смотри `last_http_status` |
| `ptz.ptz_reachable = false` | Камера недоступна по HTTP |

## ⚠️ Требования

- Python 3.12+
- Камера с поддержкой ONVIF PTZ
- Доступ к RTSP стриму камеры
