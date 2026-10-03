# R006 — extract_effort принимает reasoning-строку

## Проблема

`reasoning.get("effort")` предполагал словарь. Клиент со `"reasoning": "low"`
получал AttributeError в `do_POST` — необработанное исключение обрывало
соединение без ответа.

## Сделано

`reasoning` словарь → читается `effort`; строка/число — само значение
усилия; иное — fallback на `effort`/дефолт.

## Проверка

- `tests/test_bridge.py`: +1 тест — `{"reasoning": "low"}` → "low"
  (до фикса — AttributeError). RED подтверждён.
- `pytest tests/` — 25 passed.
