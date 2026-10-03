# R012 — PORT env: мусорное значение = warn + дефолт, не crash

**Статус:** done · PR: TBD
**Начат:** 2026-10-03

## Цель

`PORT = int(os.environ.get(...))` падал с `ValueError` при мусорном/
пробельном `MUSE_BRIDGE_PORT` / `CODEX_BRIDGE_PORT` — опечатка в env
ломала запуск моста на импорте.

## Сделано

- `_env_int()` в обоих мостах: unset/blank → дефолт молча; нечисловое →
  warning в stderr + дефолт (11471/11472).
- `tests/test_env_port.py` — 3 кейса через subprocess-импорт: garbage →
  дефолт (оба моста), blank → дефолт. Предупреждение идёт в stderr —
  stdout мостов остаётся чистым.

## Проверка

- `pytest tests/test_env_port.py` — 3 passed; весь набор tests/ зелёный.
