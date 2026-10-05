# R316 — сохранять пробелы в ответе Codex

**Статус:** готово локально · без commit/push
**Начат:** 2026-10-05

## Цель

Возвращать из Codex Bridge текст ответа без изменения пробелов и пустых строк
по краям.

## Проблема

`run_codex()` вызывал `.strip()` после чтения файла ответа. Это удаляло
значимые начальные отступы и пустые строки; кодовый ответ мог стать другим.
При этом проверка пустого ответа должна остаться.

## Сделано

- `run_codex()` возвращает прочитанный текст без обрезки пробелов по краям.
- Пустота ответа проверяется отдельно через `strip()`, поэтому одни пробелы
  или переводы строк по-прежнему дают контролируемую ошибку.
- Добавлены тесты на сохранение форматирования и отказ для пробельного ответа.

## Проверка

- До исправления: `PYTHONPATH=tests python3 -B -m unittest
  test_bridge.CodexOutputWhitespaceTests` — 2 теста, 1 FAIL: ответ был
  обрезан; проверка ответа из пробелов прошла.
- После исправления: `PYTHONPATH=tests python3 -B -m unittest
  test_bridge.CodexOutputWhitespaceTests test_bridge.CodexOutputIsolationTests`
  — 3 теста, OK.
- Офлайн-набор `test_bridge` без `PostHandlerTests` и `HealthTests` (они
  открывают loopback-сокет, запрещённый sandbox) — 94 теста, OK.
- `PYTHONPATH=tests python3 -B -m unittest test_round_queue
  test_install_scripts` — 5 тестов, OK; три проверки `test_env_port.py` — OK.
- Синтаксис двух изменённых Python-файлов — OK; `git diff --check` — код 0.
- Commit и push не выполнялись.
