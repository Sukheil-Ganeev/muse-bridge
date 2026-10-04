# R206: json.load — дубли ключей отклоняются в restore-скрипте

## Задача

Хвост семьи dup-keys: `json.load(f)` в `restore/restore_muse_provider.py` читал seed-файлы (provider_row.json, models_rows.json) без хука — повторяющийся ключ молча сворачивался.

## Что сделано

- `restore/restore_muse_provider.py` — `_no_duplicate_object` + hook в общем `load()`: оба вызова покрыты. Дубль = ValueError с именем ключа до записи в sqlite.

## Проверки

- `py_compile` по правленому файлу.
