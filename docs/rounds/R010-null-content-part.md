# R010: build_prompt — явный `content: null` не превращается в текст «None»

**Статус:** done

## Проблема
Сообщение вида `{"role":"assistant","content":null}` (штатная форма OpenAI при
tool_calls) проходит валидацию `messages is list of objects`, и `build_prompt`
пишет в промт буквальный `[assistant]\nNone` — мусорное слово «None» в тексте
запроса модели.

## Изменение
В `build_prompt` `content=None` → пустая строка; части списка с `text: null`
также дают пустую строку, не «None».

## Гейт
unittest `tests/test_bridge.py` — новые: null-content → пустое тело части;
null-text внутри list-part не даёт «None».
