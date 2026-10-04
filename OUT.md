# R296 — итог раунда

**Состояние:** готово локально, без commit/push. Изменения оставлены в dirty tree для переноса родительским агентом.

## Что изменено

- `muse_bridge.py`: неверный явно заданный `MUSE_BRIDGE_EXE` теперь вызывает
  `FileNotFoundError`; мост больше не выбирает другой `muse` из `PATH`.
- `tests/test_bridge.py`: добавлен регрессионный тест с проверкой, что поиск
  по `PATH` не подменяет отсутствующий заданный путь.
- `docs/rounds/R296-invalid-muse-exe-override.md`: описаны цель, причина,
  исправление и результаты проверки.
- `docs/rounds/QUEUE.md`: R296 добавлен в начало очереди со статусом локальной
  проверки.
- `OUT.md` создан как требуемый отчёт раунда; до начала этой работы он был
  удалён в рабочем дереве.

## Проверки

- До исправления: `PYTHONPATH=tests python3 -B -m unittest
  test_bridge.FindMuseTests` — 1 FAIL: `FileNotFoundError not raised`.
- После исправления: та же команда — `Ran 1 test`, `OK`.
- Офлайн-набор `test_bridge` без сетевых классов, а также env-port,
  установщики и очередь — `Ran 96 tests`, `OK`.
- После добавления R296 в очередь отдельный повтор `test_round_queue` —
  `Ran 1 test`, `OK`.
- `py_compile` для `muse_bridge.py` и `tests/test_bridge.py` — 2 файла,
  код возврата 0.
- `git diff --check` — код возврата 0, вывода нет.
- `PostHandlerTests` и `HealthTests`: `Ran 13 tests`, `FAILED (errors=13)`;
  все ошибки вызваны запретом sandbox на `socket()` при привязке к
  `127.0.0.1:0` (`PermissionError: [Errno 1] Operation not permitted`).

## Осталось открытым

- Интеграционные HTTP-проверки, которым нужен локальный порт, здесь недоступны.
- Второй отдельный незакрытый дефект после аудита не подтверждён.
- Commit и push не выполнялись.
