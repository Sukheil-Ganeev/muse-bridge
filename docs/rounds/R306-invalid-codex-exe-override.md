# R306 — не подменять неверный CODEX_BRIDGE_EXE найденной командой

**Статус:** готово локально · без commit/push  
**Начат:** 2026-10-04

## Цель

Если владелец явно указал `CODEX_BRIDGE_EXE`, не запускать вместо него другой
Codex CLI при неверном пути.

## Проблема

`find_codex()` проверяет существование явно заданного пути, но при его
отсутствии продолжает поиск в `PATH`. Ошибочная настройка незаметно выбирает
другую команду.

## Сделано

- Если `CODEX_BRIDGE_EXE` задан, `find_codex()` возвращает этот путь только
  когда он существует; иначе поднимает понятный `FileNotFoundError`.
- Добавлен регрессионный тест: неверный явный путь не должен переключать мост
  на команду, найденную в `PATH`.

## Проверка

- До исправления: `PYTHONPATH=tests python3 -B -m unittest
  test_bridge.FindCodexTests` — 1 FAIL: `FileNotFoundError not raised`.
- После исправления: `PYTHONPATH=tests python3 -B -m unittest
  test_bridge.FindCodexTests test_bridge.FindMuseTests` — 2 теста, `OK`.
- Офлайн-контракты моста, кроме `PostHandlerTests` и `HealthTests`: 92 теста,
  `OK`. Очередь раундов и установщики: 5 тестов, `OK`.
- `pytest` недоступен (`No module named pytest`); три проверки `test_env_port.py`
  запущены напрямую и прошли: `3 environment-port checks: OK`.
- `py_compile` для двух затронутых Python-файлов и `git diff --check` — код 0,
  вывода нет.
- `PostHandlerTests` и `HealthTests` не запускались: sandbox запрещает
  loopback-bind.
