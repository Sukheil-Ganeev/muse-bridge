# R007 — stream: только булево true включает SSE

**Статус:** done

## Проблема

`payload.get("stream")` проверялось на истинность: клиент, шлющий
`"stream": "false"`/`"0"`/любую строку, получал SSE-ответ вместо
ожидаемого JSON `chat.completion`.

## Сделано

`if payload.get("stream") is True:` — строгое сравнение с булевым
true, любые небулевы значения трактуются как «не стримить».

## Проверка

- `tests/test_bridge.py`: +1 тест — `stream:"false"` → JSON-ответ,
  `_stream_chat` не вызывается. RED подтверждён.
- `pytest tests/` — 26 passed.
