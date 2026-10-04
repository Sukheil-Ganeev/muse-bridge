# R186 — отклонять stream terminal.failed без причины

**Статус:** готово локально · без commit/push

**Начат:** 2026-10-04

## Цель

Не выдавать потоковый ответ как успешный, если Muse прислал `run.terminal.failed`, даже когда событие не содержит причины.

## Проблема

`stream_muse` сохраняет ошибку только при непустом `payload.reason`. Поэтому `terminal.failed` без причины после частичного текста игнорируется, и вызывающий код получает этот фрагмент как успешный ответ. Непотоковый путь уже закрывает этот случай текстом `unknown reason`.

## Сделано

- Добавлен регрессионный тест: после частичного текста приходит
  `run.terminal.failed` с пустым `payload`; ожидается `RuntimeError` с
  `unknown reason`.
- Потоковый путь теперь считает любое событие `run.terminal.failed` ошибкой,
  используя `unknown reason`, если причина отсутствует или пуста.
- До исправления новый тест падал: `RuntimeError not raised`.

## Проверка

- `python3 -B -m unittest test_bridge.StreamAbortTests test_bridge.TerminalFailureTests` — 11 тестов, `OK`.
- `python3 -m py_compile muse_bridge.py tests/test_bridge.py tests/test_install_scripts.py` — код 0.
- `git diff --check` — код 0.
