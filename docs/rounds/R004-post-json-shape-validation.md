# R004 — проверка формы JSON-тела в POST

## Цель

POST /v1/chat/completions отвечает 400 на валидный JSON неправильной формы —
соединение не должно умирать без ответа.

## Проблема

Тело `["a","b"]` проходило `json.loads`, но `payload.get(...)` на списке давал
AttributeError — обработчик умирал с traceback, клиент не получал ответ.
`messages: "hello"` итерировался по символам и падал там же; `messages: [42]`
падал в `build_prompt` на `m.get("role")`.

## Сделано

После `json.loads` — две проверки формы: payload обязан быть объектом
(`payload must be a json object`), `messages`, если задан, — списком объектов
(`messages must be a list of objects`). Нарушение → 400 JSON-ошибка.

## Проверка

3 новых теста (payload-список, messages-строка, messages с не-объектом)
до правки давали AttributeError/обрыв соединения, после — 400.
`pytest tests/` — 22 passed.
