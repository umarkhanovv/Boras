# Boras-Lab: AI Security System

Интеллектуальная система безопасности на базе YOLOv8 и PTZ-камер. Система автоматически обнаруживает людей, отслеживает их перемещение через PTZ-наведение и управляет освещением камеры для улучшения качества распознавания.

## 🚀 Быстрый старт

### 1. Подготовка окружения (Python 3.12)
Убедись, что у тебя установлен Python 3.12. Создай и активируй виртуальное окружение:
```bash
python -m venv ai_env
ai_env\Scripts\activate
2. Установка зависимостей
Bash
pip install fastapi uvicorn opencv-python ultralytics requests torch torchvision
3. Конфигурация
Учётные данные камеры больше не хранятся в коде. Выбери один из вариантов:

Вариант A — config_local.py (для локальной разработки, в .gitignore):
```bash
cp config_local.example.py config_local.py
```
Затем впиши свои значения CAMERA_IP / CAMERA_USER / CAMERA_PASS / API_TOKEN в config_local.py.

Вариант B — переменные окружения:
```bash
export CRANE_CAMERA_IP="192.168.1.100"
export CRANE_CAMERA_USER="admin"
export CRANE_CAMERA_PASS="your-password"
export CRANE_API_TOKEN="long-random-string"
```

API_TOKEN — это пароль для веб-панели управления (HTTP Basic Auth, логин: operator). Без него приложение не запустится.

4. Запуск системы
Bash
uvicorn app:app --reload
После запуска открой в браузере: http://127.0.0.1:8000/ (потребуется логин: operator / твой API_TOKEN)

📂 Структура проекта
app.py: Точка входа, FastAPI сервер, веб-аутентификация.

security_brain.py: Алгоритм ИИ (YOLOv8) и логика наведения (Auto-Guard v3.1).

control.py: Драйвер ONVIF для управления PTZ.

lights.py: Интеграция управления яркостью ИК/Белого света.

camera_stream.py: Асинхронный поток видео.

config.py: Загрузка настроек из переменных окружения / config_local.py.

🛠 Возможности
Auto-Guard v3.1: Плавное наведение на объект с подавлением дребезга.

Smart Patrol: Автоматическое сканирование периметра при отсутствии целей.

Dynamic Lighting: Интеллектуальное переключение между ИК-режимом и мощным белым светом.

Web-UI: Потоковая передача с метаданными ИИ в реальном времени, защищена логином.

⚠️ Требования
Python 3.12+

Установленные Microsoft Visual C++ Redistributable (для работы PyTorch DLL).

Камера с поддержкой ONVIF и доступом к эндпоинту /Images/1/IrCutFilter.


***

### Что еще стоит сделать:
Если ты хочешь, чтобы другие (или ты сам на другом ПК) легко установили всё одной командой, создай рядом файл `requirements.txt` и вставь туда этот список:
```text
fastapi
uvicorn
opencv-python
ultralytics
requests
torch
torchvision
Теперь установка будет выглядеть так: pip install -r requirements.txt. Это профессиональный подход.