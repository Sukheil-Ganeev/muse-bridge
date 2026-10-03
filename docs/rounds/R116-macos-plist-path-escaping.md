# R116 — экранировать путь моста в macOS plist

**Статус:** готово локально · без commit/push  
**Дата:** 2026-10-03

## Цель

Генерировать пригодный LaunchAgent plist, даже если путь к копии проекта
содержит символы, специальные для XML.

## Проблема

`install/macos-install.sh` вставляет путь к `muse_bridge.py` напрямую в XML
элемент `<string>`. Например, допустимый символ `&` делает созданный plist
невалидным, и launchd не может загрузить автозапуск.

## Сделано

- Перед записью plist путь теперь XML-экранирует `&`, `<` и `>`.
- Добавлен офлайн-регрессионный тест: он запускает копию установщика в пути с
  `&`, `<` и `>`, загружает plist через `plistlib` и проверяет точное значение
  аргумента.

## Проверка

- До исправления: новый тест падал — `plistlib` сообщал о невалидном XML
  (`ExpatError`, строка 10, столбец 38).
- После исправления: `python3 -m unittest discover -s tests -p test_install_scripts.py`
  — 1 тест, `OK`; `python3 -m unittest discover -s tests -p test_round_queue.py`
  — 1 тест, `OK`.
- `bash -n install/macos-install.sh`, `python3 -m py_compile tests/test_install_scripts.py`
  и `git diff --check` — успешно.
- macOS `launchctl` в этой Linux-среде не запускался; в тесте он заменён
  безопасной заглушкой, а формат plist проверен стандартным парсером.
