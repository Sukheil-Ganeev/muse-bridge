# R216 — очистка ресурсов при сбое запуска stream watchdog

**Статус:** готово локально · без commit/push
**Начат:** 2026-10-04

## Цель

Не оставлять запущенный Muse CLI и временные файлы, если не удалось запустить любой из служебных потоков потокового запроса.

## Проблема

`stream_muse` запускает CLI, затем запускает таймер и keepalive-поток до блока `try/finally`. Если запуск любого из них завершается ошибкой, очистка не выполняется: дочерний процесс остаётся работать, а prompt- и stderr-файлы остаются открытыми/на диске.

## Сделано

- Добавлены регрессионные тесты для отказа `Timer.start()` и запуска
  keepalive-потока. До исправления тест на таймер падал на `proc.killed == False`.
- Запуски таймера и keepalive-потока перенесены внутрь защищённого блока
  `try/finally`, поэтому отказ запускает штатную очистку.

## Проверка

- До исправления: точечный unittest — 1 тест, FAIL (`proc.killed` оставался
  `False`).
- После исправления: `python3 -B -m unittest test_bridge.StreamAbortTests test_bridge.PromptTempCreationFailureTests test_bridge.TerminalFailureTests` — 16 тестов, `OK`.
- `python3 -B -m unittest discover -s tests -p test_round_queue.py` — 1 тест, `OK`.
- `PYTHONPYCACHEPREFIX=/tmp/muse-bridge-pycache python3 -m py_compile muse_bridge.py tests/test_bridge.py tests/test_round_queue.py` — код 0.
- `git diff --check` — код 0.
- Полный HTTP-набор с loopback-сокетами не запускался.
