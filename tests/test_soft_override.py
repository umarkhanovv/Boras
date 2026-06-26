"""Тесты для B3 — Soft manual override.

Логика:
  - manual_override() переводит state_machine в MANUAL и запоминает timestamp
  - Любой новый вызов manual_override() продлевает timeout
  - Если _manual_override_timeout секунд не было новых команд —
    processing loop автоматически возвращает PATROL
  - Если timeout == 0 — soft override отключён (legacy behavior)
"""
import time
from unittest.mock import patch

import pytest

from app_compose import compose_app
from core.state_machine import CraneMode


@pytest.fixture
def runtime():
    """Свежий runtime для каждого теста с FakePTZ (без реальных HTTP запросов).

    compose_app() создаёт реальный CranePTZ который при stop() делает HTTP
    запрос к камере — в тестах это недопустимо (таймаут 2s × много тестов).
    Поэтому подменяем ptz на FakePTZ после compose_app.
    """
    from conftest import FakePTZ
    comps = compose_app()
    rt = comps["runtime"]
    fake_ptz = FakePTZ()
    rt.ptz = fake_ptz
    # Также подменяем в brain и operator, чтобы все ссылки были согласованы
    comps["brain"].ptz = fake_ptz
    comps["operator"].ptz = fake_ptz
    return rt


class TestManualOverrideEntersManualMode:
    """B3: manual_override переводит state_machine в MANUAL."""

    def test_manual_override_enters_manual_mode(self, runtime):
        runtime.state_machine.enable_auto_guard()  # PATROL
        runtime.manual_override()
        assert runtime.state_machine.mode == CraneMode.MANUAL
        assert runtime.state_machine.auto_guard_enabled is False

    def test_manual_override_records_timestamp(self, runtime):
        runtime.state_machine.enable_auto_guard()
        assert runtime._last_manual_command_time is None
        runtime.manual_override()
        assert runtime._last_manual_command_time is not None

    def test_manual_override_emits_event(self, runtime):
        runtime.state_machine.enable_auto_guard()
        runtime.manual_override()
        events = runtime.events.recent()
        assert any(e["name"] == "manual_override" and e["detail"] == "soft" for e in events)

    def test_manual_override_stops_ptz(self, runtime):
        """При переходе из auto-guard в MANUAL — ptz.stop() должен вызываться.
        FakePTZ уже подменён в фикстуре runtime."""
        runtime.state_machine.enable_auto_guard()
        runtime.manual_override()
        # runtime.ptz — это FakePTZ, записывает все вызовы в .calls
        assert any(call[0] == "stop" for call in runtime.ptz.calls), \
            "ptz.stop() should be called during manual_override"


class TestManualOverrideExtendsTimeout:
    """B3: новый вызов manual_override продлевает timeout."""

    def test_second_call_updates_timestamp(self, runtime):
        runtime.state_machine.enable_auto_guard()
        runtime.manual_override()
        first_ts = runtime._last_manual_command_time
        # Небольшая пауза чтобы timestamp точно отличался
        time.sleep(0.01)
        runtime.manual_override()
        second_ts = runtime._last_manual_command_time
        assert second_ts > first_ts


class TestSoftOverrideAutoReturn:
    """B3: после timeout — processing loop возвращает PATROL автоматически."""

    def test_check_timeout_returns_to_patrol(self, runtime):
        """Если timeout истёк — _check_manual_override_timeout включает auto_guard."""
        runtime.state_machine.enable_auto_guard()
        runtime.manual_override()
        assert runtime.state_machine.mode == CraneMode.MANUAL

        # Имитируем что прошло больше времени чем timeout
        runtime._last_manual_command_time = time.monotonic() - (runtime._manual_override_timeout + 1)
        runtime._check_manual_override_timeout()

        assert runtime.state_machine.mode == CraneMode.PATROL
        assert runtime.state_machine.auto_guard_enabled is True
        assert runtime._last_manual_command_time is None

    def test_check_timeout_emits_expired_event(self, runtime):
        runtime.state_machine.enable_auto_guard()
        runtime.manual_override()
        runtime._last_manual_command_time = time.monotonic() - (runtime._manual_override_timeout + 1)
        runtime._check_manual_override_timeout()
        events = runtime.events.recent()
        assert any(e["name"] == "manual_override_expired" for e in events)

    def test_check_timeout_no_action_before_expiry(self, runtime):
        """Если timeout ещё не истёк — остаёмся в MANUAL."""
        runtime.state_machine.enable_auto_guard()
        runtime.manual_override()
        # timestamp только что установлен — timeout не истёк
        runtime._check_manual_override_timeout()
        assert runtime.state_machine.mode == CraneMode.MANUAL
        assert runtime._last_manual_command_time is not None

    def test_check_timeout_no_action_when_not_in_manual(self, runtime):
        """Если мы не в MANUAL (например в IDLE) — ничего не делаем."""
        runtime._last_manual_command_time = time.monotonic() - 1000  # очень старое
        # state_machine в IDLE по умолчанию
        runtime._check_manual_override_timeout()
        assert runtime.state_machine.mode == CraneMode.IDLE

    def test_check_timeout_no_action_when_no_manual_command(self, runtime):
        """Если _last_manual_command_time is None — ничего не делаем."""
        runtime.state_machine.enable_auto_guard()  # PATROL
        assert runtime._last_manual_command_time is None
        runtime._check_manual_override_timeout()
        assert runtime.state_machine.mode == CraneMode.PATROL  # не изменилось


class TestSoftOverrideDisabledWhen:
    """B3: если timeout == 0 — soft override отключён (legacy behavior)."""

    def test_timeout_zero_disables_soft_override(self, runtime):
        runtime._manual_override_timeout = 0.0
        runtime.state_machine.enable_auto_guard()
        runtime.manual_override()
        # Даже если время сильно в прошлом — _check не должен возвращать
        runtime._last_manual_command_time = time.monotonic() - 1000
        runtime._check_manual_override_timeout()
        # Остаются в MANUAL — soft override отключён
        assert runtime.state_machine.mode == CraneMode.MANUAL


class TestSoftOverrideConfigIntegration:
    """B3: настройка из config.py."""

    def test_default_timeout_is_10_seconds(self):
        from config import settings
        assert settings.operator.manual_override_timeout == 10.0

    def test_env_override_manual_override_timeout(self, monkeypatch):
        monkeypatch.setenv("CRANE_MANUAL_OVERRIDE_TIMEOUT", "30")
        import importlib
        import config as config_module
        importlib.reload(config_module)
        try:
            assert config_module.settings.operator.manual_override_timeout == 30.0
        finally:
            monkeypatch.delenv("CRANE_MANUAL_OVERRIDE_TIMEOUT")
            importlib.reload(config_module)
