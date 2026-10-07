# R426 — timeout на subprocess-вызовах в тестах + AST-гейт

**PR:** #54

**Статус:** готово локально · без commit/push  
**Начат:** 2026-10-07

## Цель

Ни один `subprocess`-вызов в проекте не должен ждать дочерний процесс
бесконечно: восьми вызовам `subprocess.run` в тестах не хватало `timeout=`.

## Сделано

- `timeout=60` на 8 точках `subprocess.run` в `tests/test_env_port.py`
  и `tests/test_install_scripts.py`.
- Новый AST-гейт `tests/test_no_unbounded_subprocess.py`: `subprocess`
  `run/call/check_call/check_output` без `timeout=`, `wait()`/`communicate()`
  без `timeout=` на Popen-переменной и Popen без ожидания и без
  `# timeout:` пометки = FAIL во всех tracked .py вне `.agents/`, `docs/`
  и служебных папок.

## Проверка

`python3 -m pytest tests -q` — 131 зелёный, включая новый гейт.
