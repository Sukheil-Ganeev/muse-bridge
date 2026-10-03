# R016 — codex_bridge: строгий Content-Length + лимит тела

**Статус:** готово

## Цель

Перенести на codex_bridge защиту входящего POST, которую muse_bridge получил в R005+R009.

## Проблема

`do_POST` в codex_bridge.py парсил `Content-Length` через голый `int(...)`:

- заголовок `not-a-number` / `10x` / юникодные цифры → непойманный `ValueError` → обрыв соединения без ответа;
- лимита на размер тела не было вообще — заявленный `Content-Length: 999999999` читался в память.

## Сделано

- `_parse_content_length(value)`: None → 0; непустое значение обязано быть ASCII-цифрами (`isascii()+isdecimal`), иначе `ValueError` → ответ `400 bad content-length` (как в muse_bridge).
- `MAX_BODY_BYTES = 4 MiB`: заявленная длина сверх лимита → `413 payload too large` до чтения тела.
- Тесты `CodexContentLengthTests`: мусорный заголовок → 400 (раньше — необработанное исключение), лимит+1 → 413.

## Проверка

- `python3 -m pytest tests -q` → 44 passed (42 + 2 новых).
