# R336 — итог раунда

**Состояние:** готово локально; без commit/push, изменения оставлены для переноса.

## Файлы

- `codex_bridge.py`: HTTP 400 на `stream: true`, поскольку SSE в этом мосте не поддерживается.
- `tests/test_bridge.py`: регрессионный тест на ответ 400 и отсутствие запуска CLI.
- `docs/rounds/R336-codex-stream-unsupported.md`, `docs/rounds/QUEUE.md`: описание и статус раунда.

## Проверки

- До исправления: новый тест упал, фактический ответ был HTTP 200 вместо 400.
- После исправления: `CodexPostValidationTests` — 7 тестов, `OK`.
- Офлайн-набор: `Ran 104 tests in 0.529s` / `OK`.
- `py_compile codex_bridge.py tests/test_bridge.py`: код 0.
- `git diff --check`: код 0.
- Проверки, которым нужен реальный loopback-сокет, не запускались.

## Осталось

- Нужен только перенос diff родительским агентом; commit и push не выполнялись.
