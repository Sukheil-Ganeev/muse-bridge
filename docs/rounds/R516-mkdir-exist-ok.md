# R516: mkdir/makedirs — exist_ok обязателен во всех tracked .py + AST-гейт

**Статус:** done
**PR:** #68
**Семья:** mkdir-exist-ok

## Дефект

`Path.mkdir()`/`os.makedirs()` без `exist_ok` падают
`FileExistsError` на повторном запуске — 12 сайтов в
tests/test_install_scripts.py.

## Исправление

Добавлен `exist_ok=True` во все 12 точек. `os.mkdir` исключён —
у него нет параметра `exist_ok`.

## Гейт

`tests/test_no_unbounded_mkdir.py` — AST-разбор всех tracked .py:
любой вызов `mkdir`/`makedirs` без ключевого `exist_ok` = красный.
