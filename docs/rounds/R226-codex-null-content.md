# R226 — codex bridge: content:null не должен давать текст «None»

**Статус:** готово локально · без commit/push
**Начат:** 2026-10-04

## Цель

Паритет с muse bridge (R010): сообщение с `"content": null` не должно
превращаться в буквальное слово «None» внутри промпта.

## Проблема

`build_prompt` в `codex_bridge.py` не имел гарда на `content is None`:
`f"[{role}]\n{content}"` выводил буквальное «None» — ассистент-ответ
с null-содержимым (типичный ответ API при tool_calls) становился
мусорной строкой в промпте. Muse-мост починён в R010, codex-мост
остался с дрейфом.

## Сделано

- Регрессионный тест: `content: null` → пустая строка, не «None».
  До исправления тест падал (`'[assistant]\nNone'`).
- Добавлен `if content is None: content = ""` после нормализации
  списка частей — симметрично muse_bridge.

## Проверка

- `python3 -m unittest discover -s tests` — 72 теста, OK.
