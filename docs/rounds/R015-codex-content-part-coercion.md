# R015 — Codex Bridge: преобразовывать нестроковый текст части content

**Статус:** done · без commit/push
**Начат:** 2026-10-03

## Цель

Числовое значение `text` внутри content-part не должно обрывать запрос Codex
Bridge до запуска Codex.

## Проблема

`build_prompt` напрямую передавал `p.get("text", "")` в `" ".join(...)`.
Для валидного JSON вроде `{"type":"text","text":123}` возникал `TypeError`;
вызов `build_prompt` расположен до обработки ошибок запуска в `do_POST`.
Muse Bridge уже преобразует нестроковые части в текст, но Codex Bridge этого
не делал.

## Сделано

Непустое значение `text` явно преобразуется в строку; отсутствующее или `null`
значение остаётся пустым.

## Проверка

- До исправления `python3 -m unittest discover -s tests -p test_bridge.py -k CodexBuildPromptTests`: ошибка `TypeError` (`int` в `str.join`).
- После исправления та же команда: 1 тест, `OK`.
- Регрессия R023: `python3 -m unittest discover -s tests -p test_bridge.py -k CodexOutputIsolationTests` — 1 тест, `OK`.
- `python3 -m py_compile codex_bridge.py tests/test_bridge.py`: успешно.
