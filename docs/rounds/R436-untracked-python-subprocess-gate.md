# R436 — учитывать новые Python-файлы в AST-гейте subprocess-timeout

**Статус:** done
**PR:** #56
**Начат:** 2026-10-07

## Цель

Проверка бесконечных ожиданий дочерних процессов должна видеть новый
неигнорируемый `.py`-файл ещё до `git add`.

## Проблема

Гейт R426 перечислял Python-файлы через `git ls-files`, который по умолчанию
возвращает только файлы, уже известные Git. Поэтому новый файл в рабочей папке
мог добавить `subprocess.run()` без `timeout=` и не попасть в локальную проверку.

## Сделано

`_live_py_files()` теперь перечисляет как уже известные Git Python-файлы, так
и новые неигнорируемые `.py` через `git ls-files --cached --others
--exclude-standard -z`. Имена по-прежнему передаются и разбираются с NUL-разделителем.

## Проверка

- До исправления: новый тест с временным неотслеживаемым `.py` завершился
  одним провалом — файл отсутствовал в `_live_py_files()`.
- После исправления: `PYTHONPATH=tests PYTHONDONTWRITEBYTECODE=1 python3 -B -m
  unittest test_no_unbounded_subprocess test_round_queue` — 3 теста, `OK`.
- Полный `unittest discover`: 130 тестов, 13 ошибок открытия loopback-сокета
  (`PermissionError: Operation not permitted` от sandbox); остальные 117 тестов
  прошли. Это ограничение среды, а не результат проверки HTTP-поведения.
- `python3 -m pytest --version` подтвердил, что `pytest` не установлен; пакеты
  не устанавливались.
- `python3 -m py_compile tests/test_no_unbounded_subprocess.py` и
  `git diff --check` — успешно. Созданный `.pyc` удалён; новых побочных файлов
  не осталось.
- Commit и push не выполнялись.
