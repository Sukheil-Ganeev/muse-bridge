# R356 — запускать Codex `.cmd/.bat` через Windows command processor

**Статус:** готово локально · без commit/push
**Начат:** 2026-10-05

## Цель

Запускать Codex CLI из `.cmd` или `.bat` на Windows так же, как Muse CLI:
через `cmd /c`, не меняя вызовы для обычных исполняемых файлов.

## Проблема

`find_codex()` может найти `codex.cmd` в Windows, но `run_codex()` передаёт его
непосредственно в `subprocess.run`. Windows не запускает batch-файл таким
способом; при этом Muse-мост уже оборачивает `.cmd/.bat` через `cmd /c`.

## Сделано

Добавлен сборщик команды по образцу Muse: `.cmd/.bat` на Windows запускаются
через `cmd /c`, остальные исполняемые файлы остаются прямым вызовом. Тест
проверяет и batch-файл с расширением в верхнем регистре, и обычный `.exe`.

## Проверка

- До исправления: адресный тест завершился `AttributeError`, поскольку у Codex
  не было сборщика команды.
- После исправления: 2 адресных теста, `OK`.
- Общий офлайн-набор без `PostHandlerTests` и `HealthTests` — 107 тестов, `OK`.
- `python3 -m py_compile muse_bridge.py codex_bridge.py tests/test_bridge.py`
  и `git diff --check` — успешно.
